"""
패치 방사 속성 계산 모듈.

출력 속성:
    brightness_mean   (float) — RGB → luminance 픽셀 평균 (0~255)
    brightness_std    (float) — luminance 픽셀 표준편차 (0~255)
    shadow_area_ratio (float) — 그림자 픽셀 비율 (0~1)
    vegetation_ratio  (float) — 식생 픽셀 비율 (0~1)
"""

import numpy as np


def compute_radiometric(raster_data: np.ndarray) -> dict:
    """(bands, H, W) ndarray로 brightness_mean/std 계산."""
    arr = np.asarray(raster_data)

    if arr.size == 0:
        return {"brightness_mean": None, "brightness_std": None}

    if isinstance(arr, np.ma.MaskedArray):
        arr = arr.filled(np.nan)

    arr = arr.astype(np.float64, copy=False)

    if arr.ndim == 3:
        n_bands = arr.shape[0]
        if n_bands >= 3:
            lum = 0.299 * arr[0] + 0.587 * arr[1] + 0.114 * arr[2]
        elif n_bands == 1:
            lum = arr[0]
        else:
            lum = arr.mean(axis=0)
    elif arr.ndim == 2:
        lum = arr
    else:
        return {"brightness_mean": None, "brightness_std": None}

    finite = lum[np.isfinite(lum)]
    if finite.size == 0:
        return {"brightness_mean": None, "brightness_std": None}

    return {
        "brightness_mean": float(np.mean(finite)),
        "brightness_std": float(np.std(finite)),
    }


def compute_shadow_ratio(
    raster_data: np.ndarray,
    v_thresh: float = 80.0,
    b_ratio_thresh: float = 0.35,
) -> dict:
    """RGB 픽셀로 그림자 비율 계산. 조건: V(HSV) < v_thresh AND B/(R+G+B) > b_ratio_thresh."""
    arr = np.asarray(raster_data)
    if isinstance(arr, np.ma.MaskedArray):
        arr = arr.filled(np.nan)
    arr = arr.astype(np.float64, copy=False)

    if arr.ndim != 3 or arr.shape[0] < 3 or arr.size == 0:
        return {"shadow_area_ratio": None}

    r, g, b = arr[0], arr[1], arr[2]
    valid = np.isfinite(r) & np.isfinite(g) & np.isfinite(b)
    if valid.sum() == 0:
        return {"shadow_area_ratio": None}

    v = np.maximum(np.maximum(r, g), b)
    rgb_sum = r + g + b
    safe_sum = np.where(rgb_sum > 0, rgb_sum, 1.0)
    b_ratio = np.where(rgb_sum > 0, b / safe_sum, 0.0)

    shadow = valid & (v < v_thresh) & (b_ratio > b_ratio_thresh)
    return {"shadow_area_ratio": float(shadow.sum() / valid.sum())}


def compute_vegetation_ratio(
    raster_data: np.ndarray,
    exg_thresh: float = 0.0,
) -> dict:
    """ExG 지수로 식생 픽셀 비율 계산 (RGB only). ExG = 2*g' - r' - b'."""
    arr = np.asarray(raster_data)
    if isinstance(arr, np.ma.MaskedArray):
        arr = arr.filled(np.nan)
    arr = arr.astype(np.float64, copy=False)

    if arr.ndim != 3 or arr.shape[0] < 3 or arr.size == 0:
        return {"vegetation_ratio": None}

    r, g, b = arr[0], arr[1], arr[2]
    valid = np.isfinite(r) & np.isfinite(g) & np.isfinite(b)
    if valid.sum() == 0:
        return {"vegetation_ratio": None}

    rgb_sum = r + g + b
    nz = rgb_sum > 0
    safe_sum = np.where(nz, rgb_sum, 1.0)
    r_n = np.where(nz, r / safe_sum, 0.0)
    g_n = np.where(nz, g / safe_sum, 0.0)
    b_n = np.where(nz, b / safe_sum, 0.0)

    exg = 2.0 * g_n - r_n - b_n
    veg = valid & nz & (exg > exg_thresh)
    return {"vegetation_ratio": float(veg.sum() / valid.sum())}
