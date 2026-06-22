"""
main.py
───────
얇은 오케스트레이터. 분석 파이프라인을 순서대로 호출한다.

실행 순서 (전체):
  1. python tools/build_manifest.py          ← 1회성: 패치 PNG·마스크 생성 + manifest.json
  2. python tools/generate_attrs.py          ← 1회성: SQLite에서 속성 읽기 + sample_attrs.json
  3. python tools/precompute_panel_stats.py  ← 1회성(또는 데이터 변경 시): 패널용 집계
  4. python main.py                          ← 매 실행: 평가 + App

데이터셋 선택 (기본: config.DEFAULT_DATASET):
  python main.py --dataset building-seocho-2022

pipeline 단계:
  dataset_builder  →  evaluation  →  app
  (시각화는 FiftyOne App 내 5개 패널에서 확인)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

# ── 플러그인 경로를 FiftyOne import 전에 설정 ─────────────────────────────────
# FiftyOne은 최초 import 시 FIFTYONE_PLUGINS_DIR 환경변수를 읽는다.
# 이 블록은 fiftyone을 직접·간접으로 import하는 코드보다 반드시 먼저 실행돼야 한다.
_PLUGINS_DIR = str(Path(__file__).parent.resolve() / "plugins")
os.environ["FIFTYONE_PLUGINS_DIR"] = _PLUGINS_DIR

import config

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument("--dataset", default=None)
_args, _ = parser.parse_known_args()
config.activate_dataset(_args.dataset)

# plugins_dir을 config 초기화 이후에도 명시적으로 재확인
os.environ["FIFTYONE_PLUGINS_DIR"] = str(config.PLUGINS_DIR)

import seg_utils
from pipeline import app, dataset_builder, evaluation
from pipeline.app import configure_sidebar

try:
    import fiftyone as fo
except ImportError as exc:
    sys.exit(f"FiftyOne not installed.\nError: {exc}")

# fiftyone import 이후에도 config 객체에 반영 (이중 보장)
fo.config.plugins_dir = str(config.PLUGINS_DIR)


def _cleanup_stale_fo_datasets() -> None:
    """불필요한 FiftyOne 데이터셋을 App 시작 시 정리한다.

    - 구버전 seg-eval-* 데이터셋 (config.DATASETS 에 없는 것)
    - 데이터셋 키와 이름이 같은 FiftyOne 잔여 데이터셋
    """
    valid_eval    = {f"seg-eval-{k}" for k in config.DATASETS}
    dataset_names = set(config.DATASETS.keys())   # "building-jungrang-2022" 등

    for name in fo.list_datasets():
        if name.startswith("seg-eval-") and name not in valid_eval:
            fo.delete_dataset(name)
            print(f"  [cleanup] Deleted stale seg-eval dataset: {name}")
        elif name in dataset_names:
            fo.delete_dataset(name)
            print(f"  [cleanup] Removed stale dataset from App: {name}")


def _run_tool(script: str, dataset: str) -> None:
    """tools/ 스크립트를 현재 Python 인터프리터로 실행한다."""
    import subprocess
    result = subprocess.run(
        [sys.executable, script, "--dataset", dataset],
        cwd=str(config.ROOT_DIR),
    )
    if result.returncode != 0:
        print(f"  [auto-sync] WARNING: {script} exited with code {result.returncode}")


def _auto_sync_if_stale() -> None:
    """config.py 또는 sample_attrs.json 이 stale 이면 자동으로 sync 를 실행한다.

    트리거 규칙:
      config.py > sample_attrs.json  → generate_attrs + precompute (속성 정의 변경)
      sample_attrs.json > panel_stats.json → precompute only (attrs 만 갱신)
      manifest.json > panel_stats.json  → precompute only (추론 결과 변경, 새 모델 추가 등)

    manifest.json 이 없는 데이터셋(inference 미실행)은 건너뛴다.
    """
    config_mtime = (config.ROOT_DIR / "config.py").stat().st_mtime

    for ds_key, ds_cfg in config.DATASETS.items():
        manifest = ds_cfg["data_dir"] / "manifest.json"
        attrs    = ds_cfg["data_dir"] / "sample_attrs.json"
        stats    = ds_cfg["data_dir"] / "panel_stats.json"

        if not manifest.exists():
            continue  # inference 미실행 → 건너뜀

        attrs_mtime    = attrs.stat().st_mtime if attrs.exists() else 0
        stats_mtime    = stats.stat().st_mtime if stats.exists() else 0
        manifest_mtime = manifest.stat().st_mtime

        need_attrs = config_mtime > attrs_mtime
        need_stats = need_attrs or (attrs_mtime > stats_mtime) or (manifest_mtime > stats_mtime)

        if need_attrs:
            print(f"\n  [auto-sync] {ds_key}: config.py changed — regenerating attrs ...")
            _run_tool("tools/generate_attrs.py", ds_key)

        if need_stats:
            print(f"  [auto-sync] {ds_key}: stats outdated — recomputing panel stats ...")
            _run_tool("tools/precompute_panel_stats.py", ds_key)


def _build_all_datasets() -> fo.Dataset:
    """manifest 가 존재하는 모든 데이터셋을 FiftyOne DB 에 로드한다.

    FiftyOne 의 MongoDB 인스턴스는 main.py 프로세스가 소유한다.
    precompute 의 subprocess 에서 빌드된 데이터셋은 프로세스 종료 후 DB 에 남지 않으므로,
    App 에서 사용할 모든 데이터셋을 이 프로세스 안에서 직접 빌드한다.

    Returns:
        ACTIVE 데이터셋 (App 에 기본으로 표시될 데이터셋).
    """
    original_active = config.ACTIVE_DATASET
    active_dataset  = None

    for ds_key, ds_cfg in config.DATASETS.items():
        manifest_path = ds_cfg["data_dir"] / "manifest.json"
        attrs_path    = ds_cfg["data_dir"] / "sample_attrs.json"

        if not manifest_path.exists():
            print(f"  [skip] {ds_key}: manifest not found")
            continue

        print(f"\n── Building dataset: {ds_key} ───────────────────────────────")
        config.activate_dataset(ds_key)

        manifest = seg_utils.load_manifest(config.MANIFEST_PATH)
        attrs    = seg_utils.load_attrs(attrs_path)

        ds          = dataset_builder.build(manifest, attrs)
        all_results = evaluation.run(ds)

        # derived/mask 메트릭(f1/f2/biou 등)을 {metric}_{exp} sample 필드로 부착.
        # fiftyone_eval 메트릭(accuracy/recall/precision)은 evaluation.run() 이 이미 붙였다.
        # 사이드바 배치 기준은 kind — metric 이면 전부 "Metrics · {model}" 그룹에 표시.
        if config.PANEL_STATS_PATH.exists():
            with open(config.PANEL_STATS_PATH, encoding="utf-8") as _f:
                _stats = json.load(_f)
            dataset_builder.attach_derived_metric_fields(ds, _stats)

        # 사이드바 설정: config.activate_dataset(ds_key) 가 유효한 구간에서 수행.
        # 같은 속성그룹을 가진 데이터셋은 자동으로 같은 사이드바를 갖게 된다.
        configure_sidebar(ds)

        if ds_key == original_active or active_dataset is None:
            active_dataset = ds
            evaluation.print_report(all_results)

    config.activate_dataset(original_active)
    return active_dataset


def main() -> None:
    print("=" * 70)
    print(f"  FiftyOne Semantic Segmentation Evaluation — {config.ACTIVE_DATASET}")
    print("=" * 70)

    _cleanup_stale_fo_datasets()
    _auto_sync_if_stale()

    if not config.MANIFEST_PATH.exists():
        sys.exit(
            f"\n  Manifest not found: {config.MANIFEST_PATH}\n"
            "  먼저  python tools/build_manifest.py  를 실행하세요.\n"
        )

    if not config.PANEL_STATS_PATH.exists():
        print(
            "  ℹ  panel_stats.json 없음 — 패널 통계 없이 App을 실행합니다.\n"
            "     (패널 통계 생성: python tools/precompute_panel_stats.py)"
        )

    dataset = _build_all_datasets()
    app.launch(dataset)


if __name__ == "__main__":
    main()
