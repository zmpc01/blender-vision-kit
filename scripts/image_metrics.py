#!/usr/bin/env python3
"""image_metrics.py -- numeric image statistics for the kit's GATE half.

Doctrine (vision-kit): EYES triage and compose; GATES decide. A
vision-native agent reads renders directly, but numeric image stats are
still the objective complement -- exposure/dynamic-range audits (M5 P2
was tuned with exactly these), before/after diffs, and regression
checkpoints that don't depend on subjective reading.

This module is deliberately image-metrics ONLY. There is no ascii
rendering and no external VLM anywhere in this kit: agents without
native vision are upstream blender-agent-kit's audience, not ours.

Usage:
    from image_metrics import luma, sat_val, sobel_energy, range_stats
    import numpy as np
    from PIL import Image

    arr = np.asarray(Image.open("render.png").convert("RGB"), dtype=np.float32) / 255.0
    print(range_stats(arr))            # dict: min/max/mean/stdev/p_dark
    print(sobel_energy(luma(arr)))     # edge energy (P2 exposure tuning)
    print(sat_val(arr))                # mean saturation (color identity)
"""
import numpy as np


def luma(arr: np.ndarray) -> np.ndarray:
    """Perceptual luma channel in [0, 1] from an RGB array in [0, 1]."""
    return 0.2126 * arr[..., 0] + 0.7152 * arr[..., 1] + 0.0722 * arr[..., 2]


def sat_val(arr: np.ndarray) -> float:
    """Mean HSV saturation in [0, 1] -- 'does this image carry color identity?'."""
    mx = arr.max(axis=-1)
    mn = arr.min(axis=-1)
    delta = mx - mn
    denom = np.maximum(mx, 1e-6)
    return float(np.mean(delta / denom))


def sobel_energy(gray: np.ndarray) -> float:
    """Mean Sobel edge magnitude -- structural detail / contrast energy."""
    gx = np.zeros_like(gray)
    gy = np.zeros_like(gray)
    gx[:, 1:-1] = gray[:, 2:] - gray[:, :-2]
    gy[1:-1, :] = gray[2:, :] - gray[:-2, :]
    return float(np.mean(np.sqrt(gx * gx + gy * gy)))


def range_stats(arr: np.ndarray) -> dict:
    """Dynamic-range usage of a render -- the P2 lesson in one dict.

    p_dark is the fraction of pixels in the darkest third of the range;
    the kit-default workbench config used to put 98% of pixels there
    before the +1.0EV exposure default landed.
    """
    g = luma(arr)
    return {
        "min": float(g.min()),
        "max": float(g.max()),
        "mean": float(g.mean()),
        "stdev": float(g.std()),
        "p_dark": float(np.mean(g < (g.max() / 3.0))) if g.max() > 0 else 1.0,
    }


if __name__ == "__main__":
    import sys
    from PIL import Image

    for path in sys.argv[1:]:
        a = np.asarray(Image.open(path).convert("RGB"), dtype=np.float32) / 255.0
        s = range_stats(a)
        print(f"{path}: stdev={s['stdev']:.1f}/255 p_dark={s['p_dark']:.0%} "
              f"sat={sat_val(a):.2f} edge={sobel_energy(luma(a)):.2f}")
