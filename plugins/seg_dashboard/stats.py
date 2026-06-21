"""
plugins/seg_dashboard/stats.py
-------------------------------
panel_stats.json 로더 + experiment / dataset / column / records 조회 헬퍼.

파일 수정 시각을 추적해 캐시를 무효화하므로, precompute_panel_stats.py 를
재실행해도 App 재시작 없이 즉시 반영된다.

스키마 (v2):
  experiments.<exp>.{confusion_matrix, per_class, per_class_by_value, records, correlation}
  + 최상위 columns (컬럼 메타: kind/type/description/values/range)

records 가 단일 소스다. 분포·상관 등 모든 파생 통계는 records 에서 계산한다.
픽셀 전용 데이터(confusion_matrix, per_class, per_class_by_value)만 별도 블록으로 존재한다.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import config  # noqa: E402

# 경로별 캐시: {path_str -> (mtime, data)}
_stats_cache: dict[str, tuple[float, dict]] = {}


# ── 로더 ──────────────────────────────────────────────────────────────────────

def _stats_path_for(dataset: Optional[str]) -> Path:
    """dataset 키에 해당하는 panel_stats.json 경로를 반환한다."""
    if dataset and dataset in config.DATASETS:
        return config.DATASETS[dataset]["data_dir"] / "panel_stats.json"
    return config.PANEL_STATS_PATH


def load_stats(dataset: Optional[str] = None) -> Optional[dict]:
    """panel_stats.json 을 읽어 반환한다. 파일이 없으면 None.

    dataset 이름이 주어지면 해당 데이터셋의 stats 를 읽는다.
    없으면 현재 활성 데이터셋(config.PANEL_STATS_PATH) 를 읽는다.
    파일 수정 시각 기반 캐시를 사용한다.
    """
    path = _stats_path_for(dataset)
    if not path.exists():
        return None

    mtime = path.stat().st_mtime
    key   = str(path)
    cached = _stats_cache.get(key)
    if cached is None or cached[0] != mtime:
        with open(path, "r", encoding="utf-8") as fh:
            _stats_cache[key] = (mtime, json.load(fh))

    return _stats_cache[key][1]


# ── 데이터셋 헬퍼 ─────────────────────────────────────────────────────────────

def list_datasets() -> list[dict]:
    """panel_stats.json 이 실제로 존재하는 데이터셋 목록을 반환한다.

    Returns:
        [{"key": str, "label": str}, ...]  -- 빌드된 데이터셋만 포함.
    """
    result = []
    for key, cfg in config.DATASETS.items():
        path = cfg["data_dir"] / "panel_stats.json"
        if path.exists():
            result.append({"key": key, "label": cfg.get("label", key)})
    return result


# ── experiment 헬퍼 ───────────────────────────────────────────────────────────

def get_experiment_stats(stats: dict, experiment: Optional[str] = None) -> dict:
    """experiment 이름으로 해당 집계 블록을 반환한다.

    experiment 가 None 이거나 없는 이름이면 default_experiment 또는 첫 번째 사용.
    experiments 키가 없으면 빈 dict 반환 (크래시 없음).
    """
    experiments = stats.get("experiments", {})

    if not experiments:
        return {}

    if experiment and experiment in experiments:
        return experiments[experiment]

    default = stats.get("meta", {}).get("default_experiment")
    if default and default in experiments:
        return experiments[default]

    return next(iter(experiments.values()))


def list_experiments(stats: dict) -> list[str]:
    """사용 가능한 experiment 이름 목록. 없으면 빈 리스트."""
    return list(stats.get("experiments", {}).keys())


# ── records 헬퍼 ──────────────────────────────────────────────────────────────

def get_records(stats: dict, experiment: Optional[str] = None) -> list[dict]:
    """per-sample 통합 테이블(records)을 반환한다. 없으면 빈 리스트.

    records 는 속성 + 모든 메트릭을 담은 단일 소스 표다.
    분포·상관·메트릭 차트는 모두 이 records 에서 계산한다.
    """
    return get_experiment_stats(stats, experiment).get("records", [])


# ── columns 헬퍼 ──────────────────────────────────────────────────────────────

def get_columns(stats: dict) -> dict:
    """컬럼 메타 dict 를 반환한다. 없으면 빈 dict."""
    return stats.get("columns", {})


def list_metrics(stats: dict) -> list[str]:
    """columns 에서 kind=="metric" 인 키 목록을 반환한다.

    차트·섹션·드롭다운이 이 함수를 사용해야 새 메트릭을 config 에만
    추가해도 자동으로 드롭다운·차트에 반영된다.
    stats 에 columns 가 없으면 빈 리스트 반환 (크래시 없음).
    """
    return [
        name
        for name, meta in stats.get("columns", {}).items()
        if meta.get("kind") == "metric"
    ]


def list_attributes(stats: dict) -> list[str]:
    """columns 에서 kind=="attribute" 인 키 목록을 반환한다."""
    return [
        name
        for name, meta in stats.get("columns", {}).items()
        if meta.get("kind") == "attribute"
    ]
