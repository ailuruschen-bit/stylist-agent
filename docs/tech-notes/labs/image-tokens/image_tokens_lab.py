"""Lab: what an image costs when it is sent to a vision model.

Claude counts images in 28x28 pixel patches: an image costs
ceil(width / 28) * ceil(height / 28) visual tokens, after being downscaled to
fit the model's resolution tier. This lab implements that rule, checks it
against the table in the official documentation, and then applies it to the
requests StyleAI actually sends.

Run:  python image_tokens_lab.py   (standard library only)
"""

from __future__ import annotations

import math

PATCH = 28

TIERS = {
    # name: (max long edge in px, max visual tokens)
    "standard": (1568, 1568),
    "high-res": (2576, 4784),
}

PRICE_IN_PER_MTOK = {"claude-opus-5": 5.0, "claude-haiku-4-5": 1.0}


def tokens_for(width: int, height: int) -> int:
    return math.ceil(width / PATCH) * math.ceil(height / PATCH)


def downscale(width: int, height: int, tier: str) -> tuple[int, int]:
    """Largest size that fits both the long-edge and the visual-token limit."""
    max_edge, max_tokens = TIERS[tier]
    scale = min(1.0, max_edge / max(width, height))
    # Shrink further, if needed, until the token count fits.
    while True:
        w, h = max(1, round(width * scale)), max(1, round(height * scale))
        if tokens_for(w, h) <= max_tokens:
            return w, h
        scale *= 0.99


def cost_per_1000(tokens: int, model: str) -> float:
    return tokens * 1000 * PRICE_IN_PER_MTOK[model] / 1_000_000


def check_against_docs() -> None:
    """The documentation lists these sizes; the rule above should reproduce them."""
    cases = [
        # (w, h, standard size, standard tokens, high-res size, high-res tokens)
        (200, 200, (200, 200), 64, (200, 200), 64),
        (1000, 1000, (1000, 1000), 1296, (1000, 1000), 1296),
        (1092, 1092, (1092, 1092), 1521, (1092, 1092), 1521),
        (1920, 1080, (1456, 819), 1560, (1920, 1080), 2691),
        (2000, 1500, (1269, 952), 1564, (2000, 1500), 3888),
        (3840, 2160, (1456, 819), 1560, (2576, 1449), 4784),
    ]
    print("[1] check the rule against the sizes listed in the documentation")
    print(f"  {'input':<14}{'tier':<10}{'docs size':<13}{'ours':<13}{'docs tok':>9}{'ours':>7}  ok")
    for w, h, std_size, std_tok, hr_size, hr_tok in cases:
        for tier, doc_size, doc_tok in (("standard", std_size, std_tok), ("high-res", hr_size, hr_tok)):
            ours = downscale(w, h, tier)
            tok = tokens_for(*ours)
            size_ok = abs(ours[0] - doc_size[0]) <= 2 and abs(ours[1] - doc_size[1]) <= 2
            ok = "yes" if size_ok and tok == doc_tok else f"no ({ours}, {tok})"
            print(
                f"  {f'{w}x{h}':<14}{tier:<10}{f'{doc_size[0]}x{doc_size[1]}':<13}"
                f"{f'{ours[0]}x{ours[1]}':<13}{doc_tok:>9}{tok:>7}  {ok}"
            )


def main() -> None:
    check_against_docs()

    print("\n[2] photos StyleAI actually receives (high-resolution tier, claude-opus-5)")
    photos = [
        ("iPhone photo", 4032, 3024),
        ("Android photo", 4000, 3000),
        ("screenshot", 1290, 2796),
        ("resized upload, long edge 2048", 2048, 1536),
        ("resized upload, long edge 1024", 1024, 768),
        ("garment cutout in this lab", 480, 560),
        ("rendered look 3:4 at 1K", 768, 1024),
    ]
    print(f"  {'image':<32}{'input':<12}{'sent as':<12}{'tokens':>8}{'$/1000 imgs':>13}")
    for name, w, h in photos:
        sent = downscale(w, h, "high-res")
        tok = tokens_for(*sent)
        print(
            f"  {name:<32}{f'{w}x{h}':<12}{f'{sent[0]}x{sent[1]}':<12}"
            f"{tok:>8}{cost_per_1000(tok, 'claude-opus-5'):>12.2f}"
        )

    print("\n[3] one render critique request: final image + truth images of each garment")
    for garments in (2, 3, 5):
        final = tokens_for(*downscale(768, 1024, "high-res"))
        truth = garments * tokens_for(*downscale(1024, 1024, "high-res"))
        total = final + truth
        print(
            f"  {garments} garments: {total:>6} visual tokens "
            f"(final {final} + truth {truth}) = ${total * PRICE_IN_PER_MTOK['claude-opus-5'] / 1_000_000:.4f} per request"
        )

    print("\n[4] what pre-resizing saves for bulk tagging (claude-haiku-4-5)")
    print(f"  {'long edge':<12}{'size':<12}{'tokens':>8}{'$/1000 imgs':>13}")
    for edge in (2048, 1536, 1024, 768, 512):
        w, h = downscale(edge, int(edge * 4 / 3), "high-res")
        tok = tokens_for(w, h)
        print(f"  {edge:<12}{f'{w}x{h}':<12}{tok:>8}{cost_per_1000(tok, 'claude-haiku-4-5'):>12.2f}")

    print("\n[5] resending images every turn vs referencing them")
    per_image = tokens_for(*downscale(1024, 1024, "high-res"))
    for turns in (1, 5, 10):
        print(
            f"  {turns:>2} turns, 3 images in history: "
            f"{turns * 3 * per_image:>7} visual tokens if resent each turn, "
            f"{3 * per_image:>6} if sent once"
        )


if __name__ == "__main__":
    main()
