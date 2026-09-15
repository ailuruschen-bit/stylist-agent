"""Lab: extract a garment palette from a cutout image.

The lab draws a synthetic heather-grey hoodie (so the result is reproducible
and free of copyright issues), then compares several ways of turning its
pixels into a palette:

  1. mean color, with and without the background
  2. k-means in RGB on raw pixels
  3. k-means in CIELAB on raw pixels
  4. k-means in CIELAB after a masked blur, then merging clusters by CIEDE2000
  5. naming the final colors against a small reference table

Run:  python extract_palette.py   (needs numpy, pillow, scikit-image)
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from skimage.color import deltaE_ciede2000, lab2rgb, rgb2lab
from skimage.filters import gaussian

OUT = Path(__file__).parent / "out"
RNG_SEED = 7

# Reference colors used for naming. Values are sRGB.
REFERENCE_COLORS = {
    "white / 白 / ホワイト": (250, 250, 250),
    "off-white / 米白 / オフホワイト": (236, 234, 226),
    "light grey / 浅灰 / ライトグレー": (190, 190, 190),
    "heather grey / 麻灰 / 杢グレー": (150, 151, 155),
    "charcoal / 炭灰 / チャコール": (70, 72, 76),
    "black / 黑 / ブラック": (20, 20, 20),
    "navy / 藏青 / ネイビー": (32, 42, 80),
}


def to_hex(rgb: np.ndarray) -> str:
    r, g, b = (int(round(v)) for v in np.clip(rgb, 0, 255))
    return f"#{r:02X}{g:02X}{b:02X}"


def draw_hoodie(size: tuple[int, int] = (480, 560)) -> Image.Image:
    """Draw a hoodie with heather texture, shading, drawstrings and a small logo."""
    w, h = size
    rng = np.random.default_rng(RNG_SEED)

    mask_img = Image.new("L", size, 0)
    d = ImageDraw.Draw(mask_img)
    # Body, sleeves and hood as simple polygons.
    d.polygon([(130, 150), (350, 150), (360, 520), (120, 520)], fill=255)
    d.polygon([(130, 150), (40, 440), (95, 460), (150, 260)], fill=255)
    d.polygon([(350, 150), (440, 440), (385, 460), (330, 260)], fill=255)
    d.ellipse([(170, 40), (310, 200)], fill=255)
    mask = np.asarray(mask_img) > 0

    # Heather: light and dark fibers mixed at pixel level.
    light = np.array([172, 173, 177], dtype=float)
    dark = np.array([112, 113, 117], dtype=float)
    fiber_is_dark = rng.random((h, w)) < 0.35
    rgb = np.where(fiber_is_dark[..., None], dark, light)

    # Soft vertical shading, like studio light falling off toward the hem.
    shade = np.linspace(1.04, 0.86, h)[:, None, None]
    rgb = rgb * shade

    canvas = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB")
    d = ImageDraw.Draw(canvas)
    # Off-white drawstrings.
    d.line([(222, 190), (214, 330)], fill=(237, 236, 230), width=7)
    d.line([(258, 190), (266, 330)], fill=(237, 236, 230), width=7)
    # Small navy chest logo.
    d.rectangle([(205, 250), (275, 272)], fill=(34, 44, 84))

    rgba = np.dstack([np.asarray(canvas), (mask * 255).astype(np.uint8)])
    return Image.fromarray(rgba, "RGBA")


def kmeans(points: np.ndarray, k: int, iters: int = 40) -> tuple[np.ndarray, np.ndarray]:
    """Plain k-means with k-means++ init. Returns (centers, labels)."""
    rng = np.random.default_rng(RNG_SEED)
    centers = [points[rng.integers(len(points))]]
    for _ in range(1, k):
        d2 = np.min(((points[:, None, :] - np.array(centers)[None]) ** 2).sum(-1), axis=1)
        centers.append(points[rng.choice(len(points), p=d2 / d2.sum())])
    centers = np.array(centers)
    for _ in range(iters):
        labels = np.argmin(((points[:, None, :] - centers[None]) ** 2).sum(-1), axis=1)
        new = np.array([points[labels == i].mean(0) if np.any(labels == i) else centers[i] for i in range(k)])
        if np.allclose(new, centers):
            break
        centers = new
    return centers, labels


def shares(labels: np.ndarray, k: int) -> np.ndarray:
    return np.bincount(labels, minlength=k) / len(labels)


def print_palette(title: str, rgb_centers: np.ndarray, share: np.ndarray) -> None:
    print(f"\n{title}")
    for i in np.argsort(-share):
        print(f"  {to_hex(rgb_centers[i])}  {share[i] * 100:5.1f}%")


def lab_to_rgb255(lab: np.ndarray) -> np.ndarray:
    return lab2rgb(lab.reshape(-1, 1, 3)).reshape(-1, 3) * 255


def merge_by_delta_e(lab_centers: np.ndarray, share: np.ndarray, threshold: float) -> tuple[np.ndarray, np.ndarray]:
    """Greedily merge clusters whose CIEDE2000 distance is below the threshold."""
    centers, weights = list(lab_centers), list(share)
    merged = True
    while merged and len(centers) > 1:
        merged = False
        best = None
        for i in range(len(centers)):
            for j in range(i + 1, len(centers)):
                de = float(deltaE_ciede2000(centers[i], centers[j]))
                if de < threshold and (best is None or de < best[0]):
                    best = (de, i, j)
        if best:
            _, i, j = best
            wi, wj = weights[i], weights[j]
            centers[i] = (centers[i] * wi + centers[j] * wj) / (wi + wj)
            weights[i] = wi + wj
            del centers[j], weights[j]
            merged = True
    return np.array(centers), np.array(weights)


def name_color(lab: np.ndarray) -> tuple[str, float]:
    best = None
    for name, rgb in REFERENCE_COLORS.items():
        ref_lab = rgb2lab(np.array(rgb, dtype=float).reshape(1, 1, 3) / 255).reshape(3)
        de = float(deltaE_ciede2000(lab, ref_lab))
        if best is None or de < best[1]:
            best = (name, de)
    return best


def hex_to_lab(hex_color: str) -> np.ndarray:
    rgb = np.array([int(hex_color[i : i + 2], 16) for i in (1, 3, 5)], dtype=float) / 255
    return rgb2lab(rgb.reshape(1, 1, 3)).reshape(3)


def print_distance_comparison() -> None:
    print("[0] RGB distance vs CIEDE2000")
    pairs = [
        ("#202020", "#404040", "two dark greys"),
        ("#D0D0D0", "#F0F0F0", "two light greys"),
        ("#1E3A8A", "#1E3AAA", "two blues"),
        ("#808080", "#80A080", "grey vs grey-green"),
    ]
    for a, b, note in pairs:
        rgb_a = np.array([int(a[i : i + 2], 16) for i in (1, 3, 5)], dtype=float)
        rgb_b = np.array([int(b[i : i + 2], 16) for i in (1, 3, 5)], dtype=float)
        de = float(deltaE_ciede2000(hex_to_lab(a), hex_to_lab(b)))
        print(f"  {a} vs {b}  RGB distance {np.linalg.norm(rgb_a - rgb_b):5.1f}  dE00 {de:5.1f}   {note}")


def print_lch(hex_colors: list[str]) -> None:
    print("\n[7] CIELAB and LCh of the extracted colors")
    for hex_color in hex_colors:
        L, a, b = hex_to_lab(hex_color)
        chroma = (a * a + b * b) ** 0.5
        hue = (np.degrees(np.arctan2(b, a)) + 360) % 360
        print(f"  {hex_color}  L*={L:5.1f}  a*={a:5.1f}  b*={b:6.1f}  C*={chroma:5.1f}  h={hue:3.0f}")


def main() -> None:
    OUT.mkdir(exist_ok=True)
    print_distance_comparison()
    print()
    hoodie = draw_hoodie()
    hoodie.save(OUT / "hoodie_cutout.png")
    on_white = Image.new("RGB", hoodie.size, (255, 255, 255))
    on_white.paste(hoodie, mask=hoodie.split()[3])
    on_white.save(OUT / "hoodie_on_white.png")

    rgba = np.asarray(hoodie).astype(float)
    mask = rgba[..., 3] > 0
    garment_rgb = rgba[..., :3][mask]
    print(f"image {hoodie.size[0]}x{hoodie.size[1]}, garment pixels {mask.sum()} ({mask.mean() * 100:.1f}% of image)")

    # 1. Mean color.
    print("\n[1] mean color")
    print(f"  whole photo on white background : {to_hex(np.asarray(on_white).reshape(-1, 3).mean(0))}")
    print(f"  garment pixels only (cutout)    : {to_hex(garment_rgb.mean(0))}")

    rng = np.random.default_rng(RNG_SEED)
    sample_idx = rng.choice(len(garment_rgb), size=min(20000, len(garment_rgb)), replace=False)

    # 2. k-means in RGB on raw pixels.
    k = 5
    centers_rgb, _ = kmeans(garment_rgb[sample_idx], k)
    labels = np.argmin(((garment_rgb[:, None, :] - centers_rgb[None]) ** 2).sum(-1), axis=1)
    print_palette(f"[2] k-means in RGB, raw pixels, k={k}", centers_rgb, shares(labels, k))

    # 3. k-means in CIELAB on raw pixels.
    garment_lab = rgb2lab((garment_rgb / 255).reshape(-1, 1, 3)).reshape(-1, 3)
    centers_lab, _ = kmeans(garment_lab[sample_idx], k)
    labels = np.argmin(((garment_lab[:, None, :] - centers_lab[None]) ** 2).sum(-1), axis=1)
    raw_share = shares(labels, k)
    print_palette(f"[3] k-means in CIELAB, raw pixels, k={k}", lab_to_rgb255(centers_lab), raw_share)
    print("  CIEDE2000 between the two largest clusters:",
          f"{float(deltaE_ciede2000(*centers_lab[np.argsort(-raw_share)[:2]])):.1f}")

    # 4. Masked blur (simulates viewing distance), k-means in CIELAB, merge by CIEDE2000.
    alpha = mask.astype(float)
    rgb01 = rgba[..., :3] / 255
    blurred = gaussian(rgb01 * alpha[..., None], sigma=3, channel_axis=-1) / np.maximum(
        gaussian(alpha, sigma=3)[..., None], 1e-6
    )
    blurred_lab = rgb2lab(np.clip(blurred, 0, 1))[mask]
    centers_lab, _ = kmeans(blurred_lab[sample_idx], k)
    labels = np.argmin(((blurred_lab[:, None, :] - centers_lab[None]) ** 2).sum(-1), axis=1)
    blur_share = shares(labels, k)
    print_palette(f"[4a] k-means in CIELAB after masked blur, k={k}", lab_to_rgb255(centers_lab), blur_share)
    merged_lab, merged_share = merge_by_delta_e(centers_lab, blur_share, threshold=10.0)
    print_palette("[4b] merged by CIEDE2000 < 10", lab_to_rgb255(merged_lab), merged_share)
    # Dominant colors must cover a visible part of the garment. Blurred trims
    # (drawstrings smeared into grey) form small in-between clusters and are dropped here.
    keep = merged_share >= 0.10
    print_palette("[4c] dominant colors: merged clusters with share >= 10% (share renormalized)",
                  lab_to_rgb255(merged_lab[keep]), merged_share[keep] / merged_share[keep].sum())

    # 5. Naming.
    print("\n[5] naming against the reference table")
    order = np.argsort(-merged_share[keep])
    for lab, share in zip(merged_lab[keep][order], merged_share[keep][order]):
        name, de = name_color(lab)
        print(f"  {to_hex(lab_to_rgb255(lab)[0])}  {share / merged_share[keep].sum() * 100:5.1f}%  -> {name}  (dE00 {de:.1f})")

    # 6. Accents: small but distinct clusters from the raw (unblurred) pixels.
    # The blur in step 4 is good for the dominant color but washes out logos and trims.
    dominant_lab = merged_lab[keep]
    k_raw = 8
    centers_raw, _ = kmeans(garment_lab[sample_idx], k_raw)
    labels_raw = np.argmin(((garment_lab[:, None, :] - centers_raw[None]) ** 2).sum(-1), axis=1)
    raw_share8 = shares(labels_raw, k_raw)
    print(f"\n[6] accents: raw CIELAB clusters (k={k_raw}) with share >= 0.5% and dE00 >= 20 from every dominant color")
    accent_hexes: list[str] = []
    for i in np.argsort(-raw_share8):
        nearest = min(float(deltaE_ciede2000(centers_raw[i], d)) for d in dominant_lab)
        is_accent = raw_share8[i] >= 0.005 and nearest >= 20
        tag = "ACCENT" if is_accent else "      "
        hex_color = to_hex(lab_to_rgb255(centers_raw[i])[0])
        line = f"  {tag} {hex_color}  {raw_share8[i] * 100:5.1f}%  nearest dominant dE00 {nearest:5.1f}"
        if is_accent:
            name, de = name_color(centers_raw[i])
            line += f"  -> {name} (dE00 {de:.1f})"
            accent_hexes.append(hex_color)
        print(line)

    print_lch([to_hex(lab_to_rgb255(lab)[0]) for lab in dominant_lab] + accent_hexes)


if __name__ == "__main__":
    main()
