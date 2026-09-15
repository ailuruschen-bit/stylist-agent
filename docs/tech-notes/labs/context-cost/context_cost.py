"""Lab: how the context of one conversation grows, and what prompt caching saves.

This lab is pure arithmetic over the estimated size of StyleAI's context. It
does not call any API: it shows how the input volume grows with the number of
turns, and how much of it is identical from request to request.

Adjust the assumptions at the top to match measured values once the API is wired up.

Run:  python context_cost.py
"""

from __future__ import annotations

# --- assumptions (estimates, to be replaced with measured values in M0) ---
STABLE_PREFIX = 9000  # tools + system prompt + technique card index, identical every request
PER_TURN_USER = 120
PER_TURN_ASSISTANT = 400
PER_TURN_TOOLS = 1500  # tool calls and tool results appended to the history
MODEL_CALLS_PER_TURN = 3
OUTPUT_PER_TURN = PER_TURN_ASSISTANT + 600

PRICE_IN = 5.0 / 1_000_000  # USD per input token, Claude Opus 5 list price
PRICE_OUT = 25.0 / 1_000_000
CACHE_READ_RATIO = 0.1  # assumption: a cache read costs about 10% of an input token


def main() -> None:
    print(f"{'turn':>4} {'history':>8} {'input/req':>10} {'in tokens':>10} {'no cache $':>11} {'cached $':>9}")
    history = 0
    total_plain = total_cached = 0.0
    for turn in range(1, 11):
        history += PER_TURN_USER
        # Each model call in this turn resends the prefix plus the history so far.
        turn_input = sum(
            STABLE_PREFIX + history + call * (PER_TURN_TOOLS / MODEL_CALLS_PER_TURN)
            for call in range(MODEL_CALLS_PER_TURN)
        )
        history_before_turn = history - PER_TURN_USER
        history += PER_TURN_ASSISTANT + PER_TURN_TOOLS

        plain = turn_input * PRICE_IN + OUTPUT_PER_TURN * PRICE_OUT
        # Cached: the stable prefix and everything sent in earlier turns are cache reads.
        cached_tokens = (STABLE_PREFIX + history_before_turn) * MODEL_CALLS_PER_TURN
        fresh_tokens = max(0.0, turn_input - cached_tokens)
        cached = (
            cached_tokens * PRICE_IN * CACHE_READ_RATIO
            + fresh_tokens * PRICE_IN
            + OUTPUT_PER_TURN * PRICE_OUT
        )
        total_plain += plain
        total_cached += cached
        print(
            f"{turn:>4} {history:>8.0f} {turn_input / MODEL_CALLS_PER_TURN:>10.0f} "
            f"{turn_input:>10.0f} {plain:>11.4f} {cached:>9.4f}"
        )
    print(f"{'total':>4} {'':>8} {'':>10} {'':>10} {total_plain:>11.4f} {total_cached:>9.4f}")
    print(f"saving: {(1 - total_cached / total_plain) * 100:.0f}%")


if __name__ == "__main__":
    main()
