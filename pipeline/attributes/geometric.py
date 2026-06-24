"""
패치 기하 속성 계산 모듈.

출력 속성:
    bd_s                   (int)   — 패치 내 건물 수
    bd_portion             (float) — 건물 교차 면적 / 패치 면적 (0~1)
    bg_portion             (float) — 1.0 - bd_portion
    bd_avg_area            (float) — 건물 평균 교차 면적 (m²)
    bd_area_min            (float) — 최소 건물 교차 면적 (m²)
    bd_area_max            (float) — 최대 건물 교차 면적 (m²)
    bd_gap                 (float) — per-building avg_dist 평균 (m)
    bd_gap_min             (float) — per-building avg_dist 최솟값 (m)
    bd_adj_density         (float) — 인접 건물 면적 비율 (0~1)
    bd_completeness        (float) — 완전 포함 건물 수 비율 (0~1)
    bd_completeness_a      (float) — 건물 면적 기준 완전성 평균 (0~1)
    bd_fi                  (float) — Fragmentation Index (0~1)
    bd_cv                  (float) — Mean Convexity (0~1)
    bd_cluster_ratio       (float) — 연결성분 군집 비율 (0~1)
    bd_boundary_complexity (float) — 경계선 단위 길이당 방향 변화량 (rad/m)
    bd_elongation_mean     (float) — MBR 세장비 평균
    bd_orientation_entropy (float) — 건물 주축 방향 Shannon entropy (bits)
    bd_small_ratio         (float) — 소형(<100m²) 건물 비율
    bd_middle_ratio        (float) — 중형(100~500m²) 건물 비율
    bd_big_ratio           (float) — 대형(≥500m²) 건물 비율
"""

import json
import math

import numpy as np
import geopandas as gpd
from shapely.geometry import LineString, MultiLineString, Polygon


# ---------------------------------------------------------------------------
# 경계선 샘플링 · 거리 계산
# ---------------------------------------------------------------------------

def _sample_boundary_points(poly, step):
    """경계선을 step(m) 간격으로 샘플링한 Point 리스트 반환."""
    points = []
    boundary = poly.boundary
    if isinstance(boundary, LineString):
        lines = [boundary]
    elif isinstance(boundary, MultiLineString):
        lines = list(boundary.geoms)
    else:
        return points

    for line in lines:
        length = line.length
        if length <= 0:
            points.append(line.centroid)
            continue
        dists = np.arange(0.0, length, step)
        if len(dists) == 0 or dists[-1] < length:
            dists = np.append(dists, length)
        for d in dists:
            points.append(line.interpolate(float(d)))
    return points


def _topk_median_distance(points, poly_b, topk_percent):
    """경계 샘플 점들의 poly_b까지 거리 중 상위 topk_percent% 최솟값의 중앙값."""
    if not points:
        return float("nan")
    distances = np.array([p.distance(poly_b) for p in points], dtype=float)
    k = max(1, int(math.ceil(len(distances) * topk_percent / 100.0)))
    smallest = np.partition(distances, k - 1)[:k]
    return float(np.median(smallest))


def _compute_nn_distances(
    buildings,
    dist_threshold=20.0,
    topk_percent=5.0,
    sample_step=0.5,
):
    """각 건물의 nearest-neighbor avg_dist 리스트 반환."""
    geoms = list(buildings.geometry)
    n = len(geoms)
    sindex = buildings.sindex
    result = [None] * n

    for i, geom in enumerate(geoms):
        if geom is None or geom.is_empty:
            continue

        bbox = geom.buffer(dist_threshold).bounds
        candidates = [j for j in sindex.intersection(bbox) if j != i]
        if not candidates:
            continue

        min_dist = None
        nearest_j = None
        for j in candidates:
            other = geoms[j]
            if other is None or other.is_empty:
                continue
            d = geom.distance(other)
            if min_dist is None or d < min_dist:
                min_dist = d
                nearest_j = j

        if nearest_j is None or min_dist > dist_threshold:
            continue

        points = _sample_boundary_points(geom, sample_step)
        result[i] = _topk_median_distance(points, geoms[nearest_j], topk_percent)

    return result


# ---------------------------------------------------------------------------
# 개별 속성 함수
# ---------------------------------------------------------------------------

def building_count(buildings):
    return int(len(buildings))


def building_area_ratio(patch_geom, buildings, patch_area):
    if len(buildings) == 0 or patch_area <= 0:
        return 0.0
    total = sum(
        float(patch_geom.intersection(geom).area)
        for geom in buildings.geometry
        if geom is not None
    )
    return max(0.0, min(1.0, total / patch_area))


def background_area_ratio(bd_portion):
    return round(1.0 - bd_portion, 10)


def avg_building_area(patch_geom, buildings):
    if len(buildings) == 0:
        return 0.0
    areas = [
        float(patch_geom.intersection(geom).area)
        for geom in buildings.geometry
        if geom is not None
    ]
    return float(sum(areas) / len(areas)) if areas else 0.0


def min_building_area(patch_geom, buildings):
    if len(buildings) == 0:
        return None
    areas = [
        float(patch_geom.intersection(geom).area)
        for geom in buildings.geometry
        if geom is not None
    ]
    return float(min(areas)) if areas else None


def max_building_area(patch_geom, buildings):
    if len(buildings) == 0:
        return None
    areas = [
        float(patch_geom.intersection(geom).area)
        for geom in buildings.geometry
        if geom is not None
    ]
    return float(max(areas)) if areas else None


def avg_gap_distance(nn_dists):
    valid = [d for d in nn_dists if d is not None and not math.isnan(d)]
    return float(sum(valid) / len(valid)) if valid else None


def min_gap_distance(nn_dists):
    valid = [d for d in nn_dists if d is not None and not math.isnan(d)]
    return float(min(valid)) if valid else None


def adjacent_density(patch_geom, buildings, nn_dists, patch_area, tau=1.0):
    if len(buildings) < 2 or patch_area <= 0:
        return 0.0

    geoms = list(buildings.geometry)
    adj_area = 0.0
    for i, d in enumerate(nn_dists):
        if d is not None and not math.isnan(d) and d <= tau:
            geom = geoms[i]
            if geom is not None and not geom.is_empty:
                adj_area += float(patch_geom.intersection(geom).area)

    return max(0.0, min(1.0, adj_area / patch_area))


def building_completeness(patch_geom, buildings):
    n = len(buildings)
    if n == 0:
        return None
    complete = sum(
        1 for geom in buildings.geometry
        if geom is not None and patch_geom.contains(geom)
    )
    return float(complete / n)


def building_completeness_area(patch_geom, buildings):
    if len(buildings) == 0:
        return None

    ratios = []
    for geom in buildings.geometry:
        if geom is None or geom.is_empty:
            continue
        full_area = float(geom.area)
        if full_area <= 0:
            continue
        clipped_area = float(patch_geom.intersection(geom).area)
        ratios.append(clipped_area / full_area)

    return float(sum(ratios) / len(ratios)) if ratios else None


def fragmentation_index(patch_geom, buildings):
    if len(buildings) == 0:
        return None

    areas = [
        float(patch_geom.intersection(geom).area)
        for geom in buildings.geometry
        if geom is not None and not geom.is_empty
    ]
    areas = [a for a in areas if a > 0]
    total = sum(areas)
    if total <= 0:
        return None

    return float(1.0 - sum((a / total) ** 2 for a in areas))


def mean_convexity(patch_geom, buildings):
    if len(buildings) == 0:
        return None

    numerator = 0.0
    denominator = 0.0

    for geom in buildings.geometry:
        if geom is None or geom.is_empty:
            continue
        clipped = patch_geom.intersection(geom)
        if clipped.is_empty:
            continue
        a_i = float(clipped.area)
        if a_i <= 0:
            continue
        a_ch = float(clipped.convex_hull.area)
        if a_ch <= 0:
            continue
        numerator += (a_i * a_i) / a_ch
        denominator += a_i

    if denominator <= 0:
        return None

    return float(min(1.0, numerator / denominator))


def cluster_ratio(buildings, cluster_dist: float = 5.0):
    n = len(buildings)
    if n == 0:
        return None
    if n == 1:
        return 1.0

    geoms = list(buildings.geometry)
    parent = list(range(n))

    def _find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def _union(x: int, y: int) -> None:
        rx, ry = _find(x), _find(y)
        if rx != ry:
            parent[rx] = ry

    try:
        from shapely.strtree import STRtree
        tree = STRtree(geoms)
        for i, poly in enumerate(geoms):
            if poly is None or poly.is_empty:
                continue
            buffered = poly.buffer(cluster_dist)
            candidates = tree.query(buffered)
            for j in candidates:
                if j != i and geoms[j] is not None and geoms[j].distance(poly) < cluster_dist:
                    _union(i, int(j))
    except Exception:
        for i in range(n):
            for j in range(i + 1, n):
                g_i, g_j = geoms[i], geoms[j]
                if g_i is not None and g_j is not None and g_i.distance(g_j) < cluster_dist:
                    _union(i, j)

    n_clusters = len({_find(i) for i in range(n)})
    return float(n_clusters) / float(n)


def boundary_complexity(buildings):
    if len(buildings) == 0:
        return None

    complexities = []
    for geom in buildings.geometry:
        if geom is None or geom.is_empty:
            continue
        perimeter = geom.length
        if perimeter <= 0:
            continue
        polys = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
        total_angle = 0.0
        counted = False
        for poly in polys:
            coords = list(poly.exterior.coords)
            pts = coords[:-1]
            n = len(pts)
            if n < 3:
                continue
            for i in range(n):
                p0 = pts[(i - 1) % n]
                p1 = pts[i]
                p2 = pts[(i + 1) % n]
                v1x, v1y = p1[0] - p0[0], p1[1] - p0[1]
                v2x, v2y = p2[0] - p1[0], p2[1] - p1[1]
                cross = v1x * v2y - v1y * v2x
                dot = v1x * v2x + v1y * v2y
                total_angle += abs(math.atan2(cross, dot))
            counted = True
        if counted:
            complexities.append(total_angle / perimeter)

    return float(sum(complexities) / len(complexities)) if complexities else None


def elongation_mean(patch_geom, buildings):
    if len(buildings) == 0:
        return None

    elongations = []
    for geom in buildings.geometry:
        if geom is None or geom.is_empty:
            continue
        try:
            clipped = patch_geom.intersection(geom)
            if clipped is None or clipped.is_empty:
                continue
            mbr = clipped.minimum_rotated_rectangle
            coords = list(mbr.exterior.coords)
            if len(coords) < 5:
                continue
            d0 = math.hypot(coords[1][0] - coords[0][0], coords[1][1] - coords[0][1])
            d1 = math.hypot(coords[2][0] - coords[1][0], coords[2][1] - coords[1][1])
            if min(d0, d1) <= 0:
                continue
            elongations.append(max(d0, d1) / min(d0, d1))
        except Exception:
            continue

    return float(sum(elongations) / len(elongations)) if elongations else None


def orientation_entropy(patch_geom, buildings, n_bins=9):
    if len(buildings) == 0:
        return None

    angles = []
    for geom in buildings.geometry:
        if geom is None or geom.is_empty:
            continue
        try:
            clipped = patch_geom.intersection(geom)
            if clipped is None or clipped.is_empty:
                continue
            mbr = clipped.minimum_rotated_rectangle
            coords = list(mbr.exterior.coords)
            if len(coords) < 5:
                continue
            d0 = math.hypot(coords[1][0] - coords[0][0], coords[1][1] - coords[0][1])
            d1 = math.hypot(coords[2][0] - coords[1][0], coords[2][1] - coords[1][1])
            if d0 >= d1:
                dx, dy = coords[1][0] - coords[0][0], coords[1][1] - coords[0][1]
            else:
                dx, dy = coords[2][0] - coords[1][0], coords[2][1] - coords[1][1]
            angle_deg = math.degrees(math.atan2(dy, dx)) % 180.0
            if angle_deg >= 90.0:
                angle_deg -= 90.0
            angles.append(angle_deg)
        except Exception:
            continue

    if len(angles) < 2:
        return None

    bin_width = 90.0 / n_bins
    counts = [0] * n_bins
    for a in angles:
        idx = min(int(a / bin_width), n_bins - 1)
        counts[idx] += 1

    total = sum(counts)
    entropy = 0.0
    for c in counts:
        if c > 0:
            p = c / total
            entropy -= p * math.log2(p)

    return float(entropy)


def size_ratios(buildings, small_m2=100.0, big_m2=500.0):
    n = len(buildings)
    if n == 0:
        return 0.0, 0.0, 0.0

    small = middle = big = 0
    for geom in buildings.geometry:
        if geom is None or geom.is_empty:
            continue
        area = float(geom.area)
        if area < small_m2:
            small += 1
        elif area < big_m2:
            middle += 1
        else:
            big += 1

    total = small + middle + big
    if total == 0:
        return 0.0, 0.0, 0.0
    return float(small / total), float(middle / total), float(big / total)


# ---------------------------------------------------------------------------
# 통합 함수
# ---------------------------------------------------------------------------

def compute_geometric(
    patch_geom,
    buildings,
    patch_area,
    tau=1.0,
    dist_threshold=20.0,
    topk_percent=5.0,
    sample_step=0.5,
    small_m2=100.0,
    big_m2=500.0,
):
    """20개 기하 속성을 dict로 반환."""
    bd_s = building_count(buildings)
    bd_portion = building_area_ratio(patch_geom, buildings, patch_area)
    bg_portion = background_area_ratio(bd_portion)
    bd_avg_area = avg_building_area(patch_geom, buildings)
    bd_area_min = min_building_area(patch_geom, buildings)
    bd_area_max = max_building_area(patch_geom, buildings)

    if bd_s >= 2:
        nn_dists = _compute_nn_distances(buildings, dist_threshold, topk_percent, sample_step)
    else:
        nn_dists = []

    bd_gap = avg_gap_distance(nn_dists)
    bd_gap_min = min_gap_distance(nn_dists)
    bd_adj = adjacent_density(patch_geom, buildings, nn_dists, patch_area, tau=tau)
    bd_complete = building_completeness(patch_geom, buildings)
    bd_complete_a = building_completeness_area(patch_geom, buildings)
    bd_fi = fragmentation_index(patch_geom, buildings)
    bd_cv = mean_convexity(patch_geom, buildings)
    bd_cluster = cluster_ratio(buildings)
    bd_bc = boundary_complexity(buildings)
    bd_elong = elongation_mean(patch_geom, buildings)
    bd_oe = orientation_entropy(patch_geom, buildings)
    bd_sr, bd_mr, bd_br = size_ratios(buildings, small_m2=small_m2, big_m2=big_m2)

    return {
        "bd_s": bd_s,
        "bd_portion": bd_portion,
        "bg_portion": bg_portion,
        "bd_avg_area": bd_avg_area,
        "bd_area_min": bd_area_min,
        "bd_area_max": bd_area_max,
        "bd_gap": bd_gap,
        "bd_gap_min": bd_gap_min,
        "bd_adj_density": bd_adj,
        "bd_completeness": bd_complete,
        "bd_completeness_a": bd_complete_a,
        "bd_fi": bd_fi,
        "bd_cv": bd_cv,
        "bd_cluster_ratio": bd_cluster,
        "bd_boundary_complexity": bd_bc,
        "bd_elongation_mean": bd_elong,
        "bd_orientation_entropy": bd_oe,
        "bd_small_ratio": bd_sr,
        "bd_middle_ratio": bd_mr,
        "bd_big_ratio": bd_br,
    }
