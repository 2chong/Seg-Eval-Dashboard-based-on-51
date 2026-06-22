"""
tools/precompute_panel_stats.py
────────────────────────────────
1회성 사전 집계 스크립트: 등록된 모든 experiment 의 마스크를 평가해
패널(plugins/seg_dashboard/)이 읽을 data/panel_stats.json 을 생성한다.

패널은 런타임에 마스크·픽셀 연산을 하지 않으며 이 파일만 읽는다.

panel_stats.json v2 스키마:
  {
    "meta": {
      "dataset": str,
      "num_samples": int,
      "classes": [str],
      "generated_at": str,
      "experiments": [exp_name, ...],
      "default_experiment": str,
      "experiment_labels": {exp_name: label, ...}
    },
    "columns": {                        ← PANEL_COLUMN_META 에서 채움 (generate/compute 키 제외)
      "<col>": {"kind","type","description",...}
    },
    "experiments": {
      "<exp>": {
        "confusion_matrix":   {"classes":[str], "matrix":[[int]]},
        "per_class":          {"<cls>": {"recall":f, "f1":f, "precision":f}},
        "per_class_by_value": {          ← categorical 속성별 픽셀-레벨 per-class 메트릭
          "<field>": {
            "<value>": {"per_class": {"<cls>": {"recall":f,"f1":f,"precision":f}}}
          }
        },
        "records": [
          {"image_path":str, <attr_keys>:…, <metric_keys>:…}
        ],
        "correlation": {
          "fields":[], "metrics":[], "matrix":[[]], "n_samples":int
        }
      }
    }
  }

메트릭 자동 동기화:
  메트릭 정의는 config.PANEL_COLUMN_META (kind="metric", compute 키)만 편집하면 됨.
  compute.source 전략:
    "fiftyone_eval" — {field}_{exp} 샘플 필드에서 읽기
                       (evaluation.py 가 FO 생성 {exp}_{field} → {field}_{exp} 로 rename)
    "derived"       — 다른 메트릭 값에서 파생 (fn 으로 함수 이름 지정)
    "mask"          — 마스크 파일에서 직접 계산 (fn 으로 함수 이름 지정)
  새 메트릭 추가 시 기존 source 재사용이면 config 한 항목만; 새 source이면 +계산 함수 1개.

Run:
    python tools/precompute_panel_stats.py [--dataset <name>]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import config

_p = argparse.ArgumentParser(add_help=False)
_p.add_argument("--dataset", default=None)
config.activate_dataset(_p.parse_known_args()[0].dataset)

import seg_utils
from pipeline import dataset_builder, evaluation

try:
    import fiftyone as fo
    from fiftyone import ViewField as F
except ImportError as exc:
    sys.exit(f"FiftyOne not installed.\nError: {exc}")

_SUB_EVAL_KEY = "panel_sub"

# panel_stats.json 에 포함할 컬럼 메타 키 (generate/compute 는 내부 전용)
_DISPLAY_KEYS = {"kind", "type", "description", "values", "range", "unit"}


# ── 메트릭 레지스트리 ─────────────────────────────────────────────────────────

def _metric_specs() -> dict[str, dict]:
    """config.PANEL_COLUMN_META 에서 kind=="metric" + compute 키가 있는 항목을 반환한다."""
    return {
        name: meta
        for name, meta in config.PANEL_COLUMN_META.items()
        if meta.get("kind") == "metric" and "compute" in meta
    }


# ── 파생(derived) 메트릭 계산 함수 ──────────────────────────────────────────

def _f1_from_pr(p: float | None, r: float | None) -> float | None:
    if p is None or r is None:
        return None
    return float(2 * p * r / (p + r)) if (p + r) > 0 else 0.0


def _f2_from_pr(p: float | None, r: float | None) -> float | None:
    # F_beta (beta=2): (1+4)*P*R / (4*P + R)
    if p is None or r is None:
        return None
    denom = 4 * p + r
    return float(5 * p * r / denom) if denom > 0 else 0.0


def _iou_from_pr(p: float | None, r: float | None) -> float | None:
    """건물 픽셀 IoU — Jaccard 지수 (PR / (P+R−PR)).

    precision × recall / (precision + recall − precision × recall)
    와 동등하며, binary segmentation 에서 mIoU 의 단일 클래스 버전.
    """
    if p is None or r is None:
        return None
    denom = p + r - p * r
    return float(p * r / denom) if denom > 0 else 0.0


_DERIVED_FNS: dict[str, callable] = {
    "f1": _f1_from_pr,
    "f2": _f2_from_pr,
    "iou": _iou_from_pr,
}


# mask fn 레지스트리: fn 이름 → (manifest, exp_name, params) → {image_path: float|None}
# 이진 세그멘테이션(건물/배경 2클래스)에서 mask source 메트릭은 불필요하므로 비워둔다.
# iou 는 derived 방식(precision/recall 기반)으로 config 에 등록돼 있다.
_MASK_FNS: dict[str, callable] = {}


# ── 헬퍼 ──────────────────────────────────────────────────────────────────────

def _is_attr_field(name: str, ftype) -> bool:
    exp_suffixes = tuple(f"_{exp}" for exp in config.EXPERIMENTS)
    if name in config.PANEL_EXCLUDE_FIELDS or name.endswith(exp_suffixes):
        return False
    col_meta = config.PANEL_COLUMN_META.get(name, {})
    if col_meta.get("kind") == "metric":
        return False
    return isinstance(ftype, (fo.StringField, fo.FloatField, fo.IntField))


def _get_scalar(sample, field_name: str) -> float | None:
    try:
        val = sample.get_field(field_name)
    except AttributeError:
        return None
    if val is None:
        return None
    if isinstance(val, dict):
        vals = [v for v in val.values() if v is not None]
        return float(sum(vals) / len(vals)) if vals else None
    return float(val)


# ── records 단일 소스 빌드 ────────────────────────────────────────────────────

def _build_records(
    dataset: fo.Dataset,
    attr_fields: list[str],
    exp_name: str,
    metric_specs: dict,
    precomputed: dict[str, dict[str, float | None]],
) -> list[dict]:
    """per-sample 통합 테이블 (records) 생성 — 메트릭 레지스트리 기반.

    records 는 속성 + 모든 메트릭을 하나의 행에 담는 단일 소스다.
    분포·상관 등 모든 파생 통계는 이 records 에서 계산한다.

    Args:
        dataset:      FiftyOne 데이터셋
        attr_fields:  attribute 필드 이름 목록
        exp_name:     현재 experiment 이름
        metric_specs: _metric_specs() 반환값
        precomputed:  {"mask_fn_name": {image_path: value}} — mask source 사전 계산 결과
    """
    records: list[dict] = []

    # compute 순서: fiftyone_eval → mask → derived (derived는 앞 두 값에 의존)
    fo_eval_metrics = {
        name: spec for name, spec in metric_specs.items()
        if spec["compute"]["source"] == "fiftyone_eval"
    }
    mask_metrics = {
        name: spec for name, spec in metric_specs.items()
        if spec["compute"]["source"] == "mask"
    }
    derived_metrics = {
        name: spec for name, spec in metric_specs.items()
        if spec["compute"]["source"] == "derived"
    }

    for sample in dataset.iter_samples():
        record: dict = {"image_path": sample.filepath}

        # 속성 필드
        for f in attr_fields:
            record[f] = sample.get_field(f)

        computed: dict[str, float | None] = {}

        # 1. fiftyone_eval: {field}_{exp} 샘플 필드에서 읽기 (메트릭명_모델명 순)
        for mname, spec in fo_eval_metrics.items():
            fo_field = f"{spec['compute']['field']}_{exp_name}"
            computed[mname] = _get_scalar(sample, fo_field)

        # 2. mask: 사전 계산된 dict 에서 조회
        for mname, spec in mask_metrics.items():
            fn_name = spec["compute"]["fn"]
            by_path = precomputed.get(fn_name, {})
            computed[mname] = by_path.get(sample.filepath)

        # 3. derived: 다른 계산된 값들에서 파생
        # compute.deps 에 선언된 순서대로 이미 계산된 값을 인수로 전달한다.
        for mname, spec in derived_metrics.items():
            fn_name = spec["compute"]["fn"]
            fn = _DERIVED_FNS.get(fn_name)
            if fn is None:
                computed[mname] = None
                continue
            deps = spec["compute"].get("deps", [])
            args = [computed.get(dep) for dep in deps]
            computed[mname] = fn(*args)

        for mname, val in computed.items():
            if val is not None:
                record[mname] = round(float(val), 6)

        records.append(record)
    return records


# ── 픽셀 레벨 전용 집계 ───────────────────────────────────────────────────────

def _per_class_overall(results) -> dict[str, dict]:
    """SegmentationResults.report() 에서 overall per-class 지표 추출.

    NOTE: report() 는 recall/precision/f1-score 만 반환한다.
    config 에 등록된 다른 메트릭은 per-class 로 제공되지 않는다 (구조적 한계).
    """
    try:
        report = results.report()
    except Exception:
        return {}
    per_class: dict[str, dict] = {}
    for cls, row in report.items():
        if cls in ("accuracy", "macro avg", "weighted avg"):
            continue
        per_class[cls] = {
            "recall":    float(row["recall"])    if row.get("recall")    is not None else None,
            "precision": float(row["precision"]) if row.get("precision") is not None else None,
            "f1":        float(row.get("f1-score") or 0.0),
        }
    return per_class


def _per_class_by_value(
    dataset: fo.Dataset,
    attr_field_names: list[str],
    classes: list[str],
    schema: dict,
    pred_field: str = "predictions",
) -> dict[str, dict]:
    """categorical 속성별 픽셀-레벨 per-class 메트릭 (records 로 대체 불가한 유일한 픽셀 집계).

    records 에는 per-sample 스칼라 메트릭만 있어 class-level breakdown 불가.
    이 블록이 그 유일한 예외다.

    Returns:
        {"<field>": {"<value>": {"per_class": {"<cls>": {"recall":f,"f1":f,"precision":f}}}}}
    """
    result: dict[str, dict] = {}

    for fname in attr_field_names:
        ftype = schema[fname]
        if not isinstance(ftype, fo.StringField):
            continue

        distribution: dict[str, int] = dict(dataset.count_values(fname))
        by_value: dict[str, dict] = {}

        for value in distribution:
            view = dataset.match(F(fname) == value)
            if len(view) == 0:
                continue
            print(f"      [{fname}={value}] {len(view)} samples …")

            try:
                sub = view.evaluate_segmentations(
                    pred_field,
                    gt_field="ground_truth",
                    eval_key=_SUB_EVAL_KEY,
                    mask_targets=config.MASK_TARGETS,
                )
                try:
                    report = sub.report()
                except Exception as exc:
                    print(f"        Warning: report() failed ({exc}). Skipping.")
                    report = {}

                per_class: dict[str, dict] = {}
                for cls in classes:
                    row = report.get(cls, {})
                    r, p, f = row.get("recall"), row.get("precision"), row.get("f1-score")
                    per_class[cls] = {
                        "recall":    float(r) if r is not None else None,
                        "precision": float(p) if p is not None else None,
                        "f1":        float(f) if f is not None else None,
                    }
                by_value[str(value)] = {"per_class": per_class}
            finally:
                # 스크래치 eval + 임시 필드(panel_sub_*)를 즉시 삭제.
                # 루프 안에서 정리해야 다음 이터레이션이 같은 key 로 충돌하지 않고,
                # report() 중 예외가 발생해도 MongoDB 에 잔재가 남지 않는다.
                if _SUB_EVAL_KEY in dataset.list_evaluations():
                    dataset.delete_evaluation(_SUB_EVAL_KEY)

        if by_value:
            result[fname] = by_value

    return result


# ── 상관계수 (records 에서 파생) ──────────────────────────────────────────────

def _correlation_stats(records: list[dict], attr_fields: list[str], schema: dict) -> dict:
    """수치형 속성 × 메트릭 Pearson 상관계수 — records 단일 소스 사용.

    메트릭 목록은 records 의 실제 키에서 동적 산출 (하드코딩 없음).
    """
    if not records:
        return {}

    numerical_attrs = [
        f for f in attr_fields
        if isinstance(schema.get(f), (fo.FloatField, fo.IntField))
    ]
    if not numerical_attrs:
        return {}

    # records 에 실제로 있는 메트릭 키 (image_path, 속성 키 제외)
    all_keys = set(records[0].keys())
    metric_keys = [
        k for k in all_keys
        if k not in ("image_path", *attr_fields)
    ]
    if not metric_keys:
        return {}

    matrix: list[list[float]] = []
    for fname in numerical_attrs:
        row: list[float] = []
        for mkey in metric_keys:
            pairs = [
                (float(r[fname]), float(r[mkey]))
                for r in records
                if r.get(fname) is not None and r.get(mkey) is not None
            ]
            if len(pairs) < 2:
                row.append(0.0)
                continue
            v = np.array([p[0] for p in pairs])
            m = np.array([p[1] for p in pairs])
            if v.std() == 0 or m.std() == 0:
                row.append(0.0)
            else:
                row.append(round(float(np.corrcoef(v, m)[0, 1]), 4))
        matrix.append(row)

    return {
        "fields":   numerical_attrs,
        "metrics":  metric_keys,
        "matrix":   matrix,
        "n_samples": len(records),
    }


# ── 메인 ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 65)
    print("  Segmentation Dashboard — Pre-computation  (v2 multi-experiment)")
    print("=" * 65)

    if not config.MANIFEST_PATH.exists():
        sys.exit(
            f"\n  Manifest not found: {config.MANIFEST_PATH}\n"
            "  먼저  python tools/build_manifest.py  를 실행하세요.\n"
        )

    manifest = seg_utils.load_manifest(config.MANIFEST_PATH)
    print(f"Manifest loaded: {len(manifest)} entries")

    attrs = seg_utils.load_attrs(config.ATTRS_PATH)

    # ── 메트릭 스펙 (config 기반, 자동) ─────────────────────────────────────
    metric_specs = _metric_specs()
    print(f"Metric specs: {list(metric_specs.keys())}  (from PANEL_COLUMN_META)")

    # ── 데이터셋 구축 ────────────────────────────────────────────────────────
    print()
    dataset = dataset_builder.build(manifest, attrs, force_rebuild=True)

    # ── 필드 스키마 수집 ──────────────────────────────────────────────────────
    schema = dataset.get_field_schema()
    attr_field_names = [
        name for name, ftype in schema.items()
        if _is_attr_field(name, ftype)
    ]
    print(f"\nAttribute fields: {attr_field_names}")

    # ── columns 메타 (config 기반, generate/compute 키 제외) ─────────────────
    columns_meta: dict[str, dict] = {}
    for name in attr_field_names:
        if name in config.PANEL_COLUMN_META:
            columns_meta[name] = {
                k: v for k, v in config.PANEL_COLUMN_META[name].items()
                if k in _DISPLAY_KEYS
            }
        else:
            ftype = schema[name]
            columns_meta[name] = {
                "kind":        "attribute",
                "type":        "categorical" if isinstance(ftype, fo.StringField) else "numerical",
                "description": "—",
            }
    # 메트릭도 columns 에 등록 (compute 키 제외)
    for mname, mmeta in metric_specs.items():
        columns_meta[mname] = {k: v for k, v in mmeta.items() if k in _DISPLAY_KEYS}

    # ── per-experiment 집계 ──────────────────────────────────────────────────
    all_eval_results = evaluation.run(dataset)

    # evaluation.run() 이 이미 {exp}_{metric} → {metric}_{exp} 리네임을 수행했다.
    # (pipeline/evaluation.py 의 _FO_EVAL_SCALARS 로직 참조)

    classes: list[str] = []
    exp_stats: dict[str, dict] = {}

    for exp_name in config.EXPERIMENTS:
        if exp_name not in all_eval_results:
            print(f"\n  ⚠  '{exp_name}': evaluation result not found — skipping.")
            continue

        results = all_eval_results[exp_name]
        exp_classes = [str(c) for c in results.classes]
        if not classes:
            classes = exp_classes

        print(f"\n── [{exp_name}] ──────────────────────────────────────────────────")
        print(f"  Classes ({len(exp_classes)}): {exp_classes[:4]}{'...' if len(exp_classes) > 4 else ''}")

        # confusion matrix
        try:
            cm = results.confusion_matrix()
        except TypeError:
            cm = results.confusion_matrix
        print(f"  CM shape: {cm.shape}")

        # per-class overall (픽셀 레벨, report() 기반)
        per_class = _per_class_overall(results)

        # categorical 속성별 픽셀-레벨 per-class (experiment 별 predictions_<exp> 필드 직접 사용)
        pred_field = f"predictions_{exp_name}"
        if pred_field not in schema:
            print(f"  ⚠  '{pred_field}' 없음 → per_class_by_value 건너뜀.")
            per_class_by_val: dict[str, dict] = {}
        else:
            per_class_by_val = _per_class_by_value(dataset, attr_field_names, exp_classes, schema, pred_field)

        # mask source 메트릭 사전 계산
        precomputed: dict[str, dict] = {}
        for mname, spec in metric_specs.items():
            if spec["compute"]["source"] == "mask":
                fn_name = spec["compute"]["fn"]
                fn = _MASK_FNS.get(fn_name)
                if fn is None:
                    print(f"  ⚠  mask fn '{fn_name}' 미등록 — {mname} 건너뜀.")
                    continue
                params = spec["compute"].get("params", {})
                print(f"  Computing '{mname}' (mask/{fn_name}) for '{exp_name}' …")
                result_map = fn(manifest, exp_name, **params)
                precomputed[fn_name] = result_map
                vals = [v for v in result_map.values() if v is not None]
                if vals:
                    print(f"    {mname}: mean={sum(vals)/len(vals):.3f}")

        # records (단일 소스: 속성 + 모든 메트릭)
        records = _build_records(
            dataset, attr_field_names, exp_name, metric_specs, precomputed
        )

        # fiftyone_eval 이외의 메트릭(derived, mask)을 {metric}_{exp} 샘플 필드로 저장.
        # configure_sidebar() 가 endswith(f"_{exp_name}") 패턴으로 감지해 "Metrics·{model}" 그룹에 표시.
        non_fo_metrics = [
            m for m, spec in metric_specs.items()
            if spec["compute"]["source"] != "fiftyone_eval"
        ]
        if non_fo_metrics:
            record_by_path = {r["image_path"]: r for r in records}
            for sample in dataset.iter_samples(autosave=True):
                rec = record_by_path.get(sample.filepath, {})
                for mname in non_fo_metrics:
                    val = rec.get(mname)
                    if val is not None:
                        sample[f"{mname}_{exp_name}"] = float(val)

        print(f"  records: {len(records)} rows, keys={list(records[0].keys()) if records else []}")

        # correlation (records 기반, 메트릭 동적)
        corr = _correlation_stats(records, attr_field_names, schema)

        exp_stats[exp_name] = {
            "confusion_matrix":   {"classes": exp_classes, "matrix": cm.tolist()},
            "per_class":          per_class,
            "per_class_by_value": per_class_by_val,
            "records":            records,
        }
        if corr:
            exp_stats[exp_name]["correlation"] = corr

    # 임시 sub-eval 정리
    try:
        if _SUB_EVAL_KEY in dataset.list_evaluations():
            dataset.delete_evaluation(_SUB_EVAL_KEY)
    except Exception:
        pass

    # ── panel_stats.json 저장 ─────────────────────────────────────────────
    exp_labels = {exp: cfg["label"] for exp, cfg in config.EXPERIMENTS.items()}
    panel_stats: dict = {
        "meta": {
            "dataset":            config.EVAL_DATASET_NAME,
            "num_samples":        len(dataset),
            "classes":            classes,
            "generated_at":       datetime.now(timezone.utc).isoformat(),
            "experiments":        list(exp_stats.keys()),
            "default_experiment": config.DEFAULT_EXPERIMENT,
            "experiment_labels":  exp_labels,
        },
        "columns":     columns_meta,
        "experiments": exp_stats,
    }

    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(config.PANEL_STATS_PATH, "w", encoding="utf-8") as fh:
        json.dump(panel_stats, fh, indent=2, ensure_ascii=False)

    print()
    print("=" * 65)
    print(f"  panel_stats.json saved -> {config.PANEL_STATS_PATH}")
    print(f"  experiments : {list(exp_stats.keys())}")
    print(f"  columns     : {list(columns_meta.keys())}")
    if classes:
        print(f"  classes     : {len(classes)} ({classes[:3]}...)")
    print()
    print("Next step -> python main.py")
    print("  App 우상단 '+' 에서 5개 패널을 열어보세요.")
    print("=" * 65)


if __name__ == "__main__":
    main()
