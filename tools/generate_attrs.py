"""
tools/generate_attrs.py
───────────────────────
샘플별 intrinsic attribute를 직접 계산해 sample_attrs.json에 저장한다.

compute.source별 처리:
  "geometric"   → GT SHP + patch geometry → pipeline/attributes/geometric.py
  "radiometric" → TIF windowed read       → pipeline/attributes/radiometric.py

패치 geometry는 manifest의 geo.bbox에서 복원한다 (build_manifest.py가 저장한 값).
결과는 sample_attrs.json에 캐싱된다.
수식 변경 시 make regen-attr [DS=...] 로 강제 재계산.

Run (after build_manifest.py):
    python tools/generate_attrs.py [--dataset <name>]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import config

_p = argparse.ArgumentParser(add_help=False)
_p.add_argument("--dataset", default=None)
config.activate_dataset(_p.parse_known_args()[0].dataset)

from pipeline import seg_io

try:
    import numpy as np
    import geopandas as gpd
    import rasterio
    from shapely.geometry import box as shapely_box
except ImportError as exc:
    sys.exit(
        f"필수 패키지 미설치.\n  {exc}\n"
        "  pip install rasterio geopandas shapely numpy"
    )

from pipeline.attributes.geometric import compute_geometric
from pipeline.attributes.radiometric import (
    compute_radiometric,
    compute_shadow_ratio,
    compute_vegetation_ratio,
)

RESOLUTION_M = 0.25  # 소스와 동일: 0.25 m/pixel


# ── 헬퍼 ─────────────────────────────────────────────────────────────────────

def _find_single_file(directory: Path, pattern: str) -> Path | None:
    matches = list(directory.glob(pattern))
    if not matches:
        return None
    if len(matches) > 1:
        print(f"  [warn] {directory}/{pattern} 여러 매칭 → 첫 번째 사용: {matches[0].name}")
    return matches[0]


def _build_schema() -> dict[str, dict[str, str]]:
    """활성 데이터셋의 attribute 키를 source별로 분류한다.

    Returns:
        {"geometric": {key: field}, "radiometric": {key: field}}
    """
    active_keys = set(config.dataset_attribute_keys(config.ACTIVE_DATASET))
    schema: dict[str, dict[str, str]] = {"geometric": {}, "radiometric": {}}
    for key, meta in config.PANEL_COLUMN_META.items():
        if meta.get("kind") != "attribute" or key not in active_keys:
            continue
        source = meta.get("compute", {}).get("source")
        field = meta.get("compute", {}).get("field", key)
        if source in schema:
            schema[source][key] = field
        else:
            print(f"  [warn] 알 수 없는 compute.source '{source}' ({key}) → 건너뜀", file=sys.stderr)
    return schema


def _patch_geom_from_entry(entry: dict):
    """manifest 엔트리의 geo.bbox로 패치 Shapely geometry를 복원한다."""
    bbox = entry.get("geo", {}).get("bbox")
    if bbox is None or len(bbox) != 4:
        return None
    return shapely_box(*bbox)


def _intersect_buildings(gdf: gpd.GeoDataFrame, patch_geom) -> gpd.GeoDataFrame:
    """GDF에서 patch_geom과 교차하는 건물만 필터링한다."""
    candidates = list(gdf.sindex.intersection(patch_geom.bounds))
    if not candidates:
        return gdf.iloc[0:0].copy()
    cands = gdf.iloc[candidates]
    return cands[cands.geometry.intersects(patch_geom)].copy()


def _read_raster_window(tif_path: Path, patch_geom) -> np.ndarray | None:
    """TIF에서 패치 영역을 windowed read해 (bands, H, W) ndarray를 반환한다.

    패치 geometry는 EPSG:5186 기준이며, TIF CRS가 다른 경우 bounds를
    TIF CRS로 변환한 뒤 windowed read를 수행한다.
    """
    minx, miny, maxx, maxy = patch_geom.bounds
    # 픽셀 크기는 5186 기준 거리(m)로 계산 — 마스크와 격자 일치
    cols_px = max(1, int(round((maxx - minx) / RESOLUTION_M)))
    rows_px = max(1, int(round((maxy - miny) / RESOLUTION_M)))
    try:
        with rasterio.open(str(tif_path)) as src:
            from rasterio.windows import from_bounds as window_from_bounds
            from rasterio.warp import transform_bounds
            # TIF CRS가 EPSG:5186이 아니면 bounds를 TIF CRS로 변환
            win_minx, win_miny, win_maxx, win_maxy = minx, miny, maxx, maxy
            if src.crs is not None and src.crs.to_epsg() != 5186:
                win_minx, win_miny, win_maxx, win_maxy = transform_bounds(
                    "EPSG:5186", src.crs, minx, miny, maxx, maxy
                )
            window = window_from_bounds(win_minx, win_miny, win_maxx, win_maxy, transform=src.transform)
            data = src.read(
                out_shape=(src.count, rows_px, cols_px),
                window=window,
                resampling=rasterio.enums.Resampling.bilinear,
                boundless=True,
                fill_value=0,
            )
        return data
    except Exception as exc:
        print(f"  [warn] TIF windowed read 실패: {exc}", file=sys.stderr)
        return None


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 65)
    print(f"  Sample Attribute Generation  — {config.ACTIVE_DATASET}")
    print("=" * 65)

    if not config.MANIFEST_PATH.exists():
        sys.exit(
            f"Manifest not found: {config.MANIFEST_PATH}\n"
            "먼저  python tools/build_manifest.py  를 실행하세요."
        )

    schema = _build_schema()
    print(f"geometric  ({len(schema['geometric'])}): {list(schema['geometric'].keys())}")
    print(f"radiometric({len(schema['radiometric'])}): {list(schema['radiometric'].keys())}")

    manifest = seg_io.load_manifest(config.MANIFEST_PATH)
    print(f"Manifest: {len(manifest)} entries\n")

    # ── 데이터 소스 준비 ─────────────────────────────────────────────────────
    tif_path = gt_gdf = None

    if schema["radiometric"]:
        tif_dir = config.SOURCE_DIR / "data" / "aerial_image" / config.REGION / str(config.YEAR)
        tif_path = _find_single_file(tif_dir, "*.tif")
        if tif_path is None:
            sys.exit(f"항공영상 TIF 없음: {tif_dir}/*.tif")
        print(f"TIF: {tif_path}")

    if schema["geometric"]:
        gt_shp_dir = config.SOURCE_DIR / "data" / "gt_shp" / config.REGION / str(config.YEAR)
        gt_shp_path = _find_single_file(gt_shp_dir, "*.shp")
        if gt_shp_path is None:
            sys.exit(f"GT SHP 없음: {gt_shp_dir}/*.shp")
        print(f"GT SHP 로드 중 … {gt_shp_path}")
        gt_gdf = gpd.read_file(str(gt_shp_path))
        if gt_gdf.crs is None:
            gt_gdf = gt_gdf.set_crs("EPSG:5186")
        elif gt_gdf.crs.to_epsg() != 5186:
            gt_gdf = gt_gdf.to_crs("EPSG:5186")
        gt_gdf.sindex  # 사전 빌드
        print(f"  건물 폴리곤: {len(gt_gdf)}개\n")

    # ── 패치별 속성 계산 ─────────────────────────────────────────────────────
    print("속성 계산 중 …")
    updates: dict[str, dict] = {}

    for entry in manifest:
        image_path = entry["image_path"]
        patch_id   = str(entry.get("patch_id") or Path(image_path).stem)
        attrs: dict = {}

        patch_geom = _patch_geom_from_entry(entry)

        # geometric
        if schema["geometric"]:
            if patch_geom is not None:
                buildings = _intersect_buildings(gt_gdf, patch_geom)
                geo = compute_geometric(patch_geom, buildings, float(patch_geom.area))
                for key in schema["geometric"]:
                    attrs[key] = geo.get(key)
            else:
                print(f"  [warn] patch_id={patch_id} geo.bbox 없음 → geometric all None", file=sys.stderr)
                for key in schema["geometric"]:
                    attrs[key] = None

        # radiometric
        if schema["radiometric"]:
            raster = _read_raster_window(tif_path, patch_geom) if patch_geom is not None else None
            if raster is not None:
                radio = {
                    **compute_radiometric(raster),
                    **compute_shadow_ratio(raster),
                    **compute_vegetation_ratio(raster),
                }
                for key in schema["radiometric"]:
                    attrs[key] = radio.get(key)
            else:
                for key in schema["radiometric"]:
                    attrs[key] = None

        updates[image_path] = attrs

    # ── 속성별 요약 출력 ──────────────────────────────────────────────────────
    print()
    all_keys = list(schema["geometric"]) + list(schema["radiometric"])
    for key in all_keys:
        meta     = config.PANEL_COLUMN_META.get(key, {})
        vals     = [v.get(key) for v in updates.values()]
        nulls    = sum(1 for v in vals if v is None)
        non_null = [v for v in vals if v is not None]
        sfx      = f"  (null: {nulls}/{len(vals)})" if nulls else ""

        if not non_null:
            print(f"  {key:<28}: all null{sfx}")
            continue

        if meta.get("type") == "categorical":
            from collections import Counter
            print(f"  {key:<28}: {dict(Counter(str(v) for v in non_null))}{sfx}")
        else:
            try:
                fv = [float(v) for v in non_null]
                print(
                    f"  {key:<28}: min={min(fv):.4f}, "
                    f"max={max(fv):.4f}, "
                    f"mean={sum(fv)/len(fv):.4f}"
                    f"{sfx}"
                )
            except (TypeError, ValueError):
                print(f"  {key:<28}: {non_null[:3]}...{sfx}")

    # ── 저장 ─────────────────────────────────────────────────────────────────
    config.ATTRS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(config.ATTRS_PATH, "w", encoding="utf-8") as fh:
        json.dump(updates, fh, indent=2, ensure_ascii=False)
    print(f"\nAttrs saved → {config.ATTRS_PATH}  ({len(updates)} entries)")
    print("Done. Next step → python tools/precompute_panel_stats.py")


if __name__ == "__main__":
    main()
