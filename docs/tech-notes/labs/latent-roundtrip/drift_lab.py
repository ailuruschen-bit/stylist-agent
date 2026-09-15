"""Lab: what happens when each stage edits the previous stage's output.

StyleAI renders complex looks in several stages: stage 2 edits stage 1's
image, stage 3 edits stage 2's, and so on. Each stage is a full pass through
an image model, so whatever that pass changes is carried into the next stage.

This lab isolates that accumulation. It repeats the same encode/decode round
trip from vae_roundtrip.py and compares two strategies:

  chained:   stage N works on stage N-1's output      (drift accumulates)
  anchored:  stage N works on the original every time  (error stays flat)

Input: ../garment-palette/out/hoodie_cutout.png (run extract_palette.py first)
Run:   python drift_lab.py   (needs torch, diffusers, pillow, numpy, scikit-image)
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
from diffusers import AutoencoderKL
from PIL import Image
from skimage.color import deltaE_ciede2000, rgb2lab
from skimage.filters import gaussian

HERE = Path(__file__).parent
SRC = HERE.parent / "garment-palette" / "out" / "hoodie_cutout.png"
OUT = HERE / "out"
VAE_ID = "stabilityai/sd-vae-ft-mse"
PASSES = 6


def to_hex(rgb: np.ndarray) -> str:
    return "#" + "".join(f"{int(round(c)):02X}" for c in rgb)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    rgba = np.asarray(Image.open(SRC).convert("RGBA"))
    mask = rgba[..., 3] > 0
    original = np.where(mask[..., None], rgba[..., :3], 255).astype(np.uint8)
    original_lab_mean = rgb2lab((original[mask] / 255).reshape(-1, 1, 3)).reshape(-1, 3).mean(0)

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    vae = AutoencoderKL.from_pretrained(VAE_ID).to(device).eval()

    def roundtrip(image: np.ndarray) -> np.ndarray:
        x = torch.from_numpy(image).permute(2, 0, 1).float().div(127.5).sub(1).unsqueeze(0).to(device)
        with torch.no_grad():
            y = vae.decode(vae.encode(x).latent_dist.mode()).sample
        return ((y.clamp(-1, 1) + 1) * 127.5).round().byte().squeeze(0).permute(1, 2, 0).cpu().numpy()

    def report(tag: str, pass_no: int, current: np.ndarray) -> None:
        diff = np.abs(original.astype(int) - current.astype(int))[mask]
        blur_o = gaussian(original / 255, sigma=3, channel_axis=-1)
        blur_c = gaussian(current / 255, sigma=3, channel_axis=-1)
        low = np.abs(blur_o - blur_c)[mask].mean() * 255
        lab_mean = rgb2lab((current[mask] / 255).reshape(-1, 1, 3)).reshape(-1, 3).mean(0)
        de = float(deltaE_ciede2000(original_lab_mean, lab_mean))
        print(
            f"  {tag:<9}{pass_no:>5}{diff.mean():>10.2f}{low:>10.2f}"
            f"{current[mask].std(0).mean():>10.1f}  {to_hex(current[mask].mean(0))}  {de:>6.2f}"
        )

    print(f"input {original.shape[1]}x{original.shape[0]}, garment pixels {mask.sum()}")
    print(f"  {'mode':<9}{'pass':>5}{'meandiff':>10}{'lowfreq':>10}{'texture':>10}  {'mean':<9}{'dE00':>6}")
    report("original", 0, original)

    chained = original.copy()
    for i in range(1, PASSES + 1):
        chained = roundtrip(chained)
        report("chained", i, chained)
        if i in (1, 3, PASSES):
            Image.fromarray(chained).save(OUT / f"drift_chained_pass{i}.png")

    for i in (1, 3, PASSES):
        anchored = roundtrip(original)  # always starts from the original
        report("anchored", i, anchored)

    print("\nsaved drift_chained_pass*.png in", OUT)


if __name__ == "__main__":
    main()
