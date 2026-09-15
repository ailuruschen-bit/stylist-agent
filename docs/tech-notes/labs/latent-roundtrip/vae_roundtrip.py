"""Lab: compare "copy pixels through a mask" with "re-draw pixels through a latent space".

Segmentation-based cutout keeps the original pixels and only decides which
ones to keep. A latent image model first encodes the image into a smaller
latent tensor and decodes it back. This lab runs only that encode/decode round
trip with a public Stable Diffusion VAE (no denoising, no prompt) and measures
how much the garment pixels change.

Input: ../garment-palette/out/hoodie_cutout.png (run extract_palette.py first)
Run:   python vae_roundtrip.py   (needs torch, diffusers, pillow, numpy)
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
from diffusers import AutoencoderKL
from PIL import Image

HERE = Path(__file__).parent
SRC = HERE.parent / "garment-palette" / "out" / "hoodie_cutout.png"
OUT = HERE / "out"
VAE_ID = "stabilityai/sd-vae-ft-mse"
LOGO_BOX = (195, 240, 285, 282)  # x0, y0, x1, y1 around the navy chest logo


def stats(name: str, before: np.ndarray, after: np.ndarray, mask: np.ndarray) -> None:
    diff = np.abs(before.astype(int) - after.astype(int))[mask]  # (n, 3)
    per_pixel = diff.max(axis=1)
    mse = float(((before.astype(float) - after.astype(float))[mask] ** 2).mean())
    psnr = float("inf") if mse == 0 else 10 * np.log10(255**2 / mse)
    print(f"\n{name}")
    print(f"  mean abs diff per channel : {diff.mean():.2f} / 255")
    print(f"  max abs diff              : {int(diff.max())} / 255")
    print(f"  pixels changed at all     : {(per_pixel > 0).mean() * 100:.1f}%")
    print(f"  pixels changed by > 10    : {(per_pixel > 10).mean() * 100:.1f}%")
    print(f"  PSNR                      : {psnr:.1f} dB")


def main() -> None:
    OUT.mkdir(exist_ok=True)
    rgba = np.asarray(Image.open(SRC).convert("RGBA"))
    rgb = rgba[..., :3]
    mask = rgba[..., 3] > 0
    h, w = mask.shape
    print(f"input {w}x{h}, garment pixels {mask.sum()}")

    # A. Segmentation-style cutout: keep original pixels where the mask says so.
    white = np.full_like(rgb, 255)
    photo = np.where(mask[..., None], rgb, white)  # garment photographed on white
    cutout = np.where(mask[..., None], photo, white)
    stats("[A] mask-based cutout vs original garment pixels", rgb, cutout, mask)

    # B. Latent round trip through the VAE.
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    vae = AutoencoderKL.from_pretrained(VAE_ID).to(device).eval()
    x = torch.from_numpy(photo).permute(2, 0, 1).float().div(127.5).sub(1).unsqueeze(0).to(device)
    with torch.no_grad():
        latent = vae.encode(x).latent_dist.mode()
        y = vae.decode(latent).sample
    print(f"\nimage tensor {tuple(x.shape)} -> latent {tuple(latent.shape)}")
    ratio = x.numel() / latent.numel()
    print(f"  values in image / values in latent = {ratio:.0f}x")
    decoded = ((y.clamp(-1, 1) + 1) * 127.5).round().byte().squeeze(0).permute(1, 2, 0).cpu().numpy()
    stats("[B] VAE encode -> decode vs original garment pixels", rgb, decoded, mask)

    # Separate fine texture from overall color: compare after the same blur on both sides.
    from skimage.filters import gaussian

    def masked_blur(img: np.ndarray) -> np.ndarray:
        a = mask.astype(float)
        num = gaussian(img.astype(float) / 255 * a[..., None], sigma=3, channel_axis=-1)
        den = np.maximum(gaussian(a, sigma=3)[..., None], 1e-6)
        return np.clip(num / den * 255, 0, 255)

    inner = mask & (gaussian(mask.astype(float), sigma=3) > 0.99)  # ignore pixels next to the outline
    stats("[B-lowfreq] round trip after blurring both images (sigma=3), interior pixels",
          masked_blur(rgb).round().astype(np.uint8), masked_blur(decoded).round().astype(np.uint8), inner)
    to_hex = lambda v: "#" + "".join(f"{int(round(c)):02X}" for c in v)
    print(f"  garment mean color  original {to_hex(rgb[mask].mean(0))}  decoded {to_hex(decoded[mask].mean(0))}")
    print(f"  pixel std-dev (texture)  original {rgb[mask].std(0).mean():.1f}  decoded {decoded[mask].std(0).mean():.1f}")

    logo_mask = np.zeros_like(mask)
    x0, y0, x1, y1 = LOGO_BOX
    logo_mask[y0:y1, x0:x1] = True
    stats("[B-logo] same round trip, logo area only", rgb, decoded, logo_mask & mask)

    # Save a side-by-side crop of the logo area, scaled up 4x without smoothing.
    crop = lambda a: Image.fromarray(a[y0:y1, x0:x1]).resize(((x1 - x0) * 4, (y1 - y0) * 4), Image.NEAREST)
    diff = np.abs(photo.astype(int) - decoded.astype(int)).max(axis=2)
    heat = np.clip(diff * 8, 0, 255).astype(np.uint8)
    heat_rgb = np.dstack([heat, heat, heat])
    panel = Image.new("RGB", ((x1 - x0) * 4 * 3 + 20, (y1 - y0) * 4), (255, 255, 255))
    panel.paste(crop(photo), (0, 0))
    panel.paste(crop(decoded), ((x1 - x0) * 4 + 10, 0))
    panel.paste(crop(heat_rgb), ((x1 - x0) * 8 + 20, 0))
    panel.save(OUT / "logo_original_decoded_diff.png")
    Image.fromarray(decoded).save(OUT / "hoodie_vae_roundtrip.png")
    print(f"\nsaved {OUT / 'logo_original_decoded_diff.png'}")


if __name__ == "__main__":
    main()
