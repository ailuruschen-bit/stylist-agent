"""Lab: what "constrained decoding" does, on a toy model.

Structured output guarantees that a response matches a JSON Schema. The
mechanism is easy to state: at every step, the sampler is only allowed to pick
tokens that can still lead to a valid document.

This lab replaces the language model with a small biased random generator over
a fixed vocabulary, so the mechanism can be observed without any API call:

  1. free sampling: how often the toy model produces a valid tagging result
  2. constrained sampling: the same generator, with invalid tokens masked out
  3. what masking does to the probabilities at one step
  4. where the remaining errors live once the structure is guaranteed

Run:  python constrained_lab.py   (needs numpy)
"""

from __future__ import annotations

import json

import numpy as np

RNG_SEED = 5
SAMPLES = 2000

CATEGORIES = ["tops", "bottoms", "outerwear", "shoes", "accessories"]
# The toy vocabulary: structural pieces, category values, numbers and distractors.
VOCAB = (
    ['{', '}', '"category"', '"formality"', ':', ',']
    + [f'"{c}"' for c in CATEGORIES]
    + [str(n) for n in range(1, 6)]
    + ['"hoodie"', '"grey"', "6", "null", "Sure!", "```json"]
)
VOCAB_INDEX = {t: i for i, t in enumerate(VOCAB)}

TRUTH = {"category": "tops", "formality": 2}


def model_logits(state: str, rng: np.random.Generator) -> np.ndarray:
    """A stand-in for a language model: mostly right, sometimes not."""
    logits = rng.normal(scale=1.0, size=len(VOCAB))
    # The toy model "knows" roughly what should come next, with a wide margin of error.
    preferred = {
        "start": ['{', "Sure!", "```json"],
        "key1": ['"category"', '"formality"'],
        "colon1": [':'],
        "value1": ['"tops"', '"hoodie"', '"outerwear"', '"grey"'],
        "comma": [',', '}'],
        "key2": ['"formality"', '"category"'],
        "colon2": [':'],
        "value2": ["2", "3", "6", "null"],
        "end": ['}'],
    }[state]
    for i, token in enumerate(preferred):
        logits[VOCAB_INDEX[token]] += 4.0 - i * 1.2
    return logits


def softmax(logits: np.ndarray) -> np.ndarray:
    e = np.exp(logits - logits.max())
    return e / e.sum()


# The grammar: which tokens may follow in each state, and where they lead.
ALLOWED: dict[str, list[str]] = {
    "start": ['{'],
    "key1": ['"category"'],
    "colon1": [':'],
    "value1": [f'"{c}"' for c in CATEGORIES],
    "comma": [','],
    "key2": ['"formality"'],
    "colon2": [':'],
    "value2": [str(n) for n in range(1, 6)],
    "end": ['}'],
}
STATES = list(ALLOWED)


def sample_document(rng: np.random.Generator, *, constrained: bool) -> str:
    tokens: list[str] = []
    for state in STATES:
        probs = softmax(model_logits(state, rng))
        if constrained:
            mask = np.zeros(len(VOCAB))
            for token in ALLOWED[state]:
                mask[VOCAB_INDEX[token]] = 1.0
            probs = probs * mask
            probs = probs / probs.sum()  # renormalize over the allowed tokens only
        tokens.append(VOCAB[rng.choice(len(VOCAB), p=probs)])
    return "".join(tokens)


def check(document: str) -> tuple[bool, bool]:
    """Returns (parses as JSON and matches the schema, has the right values)."""
    try:
        data = json.loads(document)
    except json.JSONDecodeError:
        return False, False
    if set(data) != {"category", "formality"}:
        return False, False
    if data["category"] not in CATEGORIES:
        return False, False
    if not isinstance(data["formality"], int) or not 1 <= data["formality"] <= 5:
        return False, False
    return True, data == TRUTH


def run(constrained: bool) -> tuple[float, float, list[str]]:
    rng = np.random.default_rng(RNG_SEED)
    valid = correct = 0
    examples: list[str] = []
    for _ in range(SAMPLES):
        doc = sample_document(rng, constrained=constrained)
        ok, right = check(doc)
        valid += ok
        correct += right
        if not ok and len(examples) < 3:
            examples.append(doc)
    return valid / SAMPLES, correct / SAMPLES, examples


def main() -> None:
    print(f"toy vocabulary of {len(VOCAB)} tokens, {SAMPLES} samples per run")

    free_valid, free_correct, bad = run(constrained=False)
    print("\n[1] free sampling")
    print(f"  valid against the schema : {free_valid:6.1%}")
    print(f"  exactly the right values : {free_correct:6.1%}")
    for doc in bad:
        print(f"  invalid example          : {doc[:70]}")

    con_valid, con_correct, _ = run(constrained=True)
    print("\n[2] constrained sampling (same generator, invalid tokens masked)")
    print(f"  valid against the schema : {con_valid:6.1%}")
    print(f"  exactly the right values : {con_correct:6.1%}")

    print("\n[3] what masking does at one step (state 'value2': the formality number)")
    rng = np.random.default_rng(RNG_SEED)
    probs = softmax(model_logits("value2", rng))
    mask = np.zeros(len(VOCAB))
    for token in ALLOWED["value2"]:
        mask[VOCAB_INDEX[token]] = 1.0
    masked = probs * mask / (probs * mask).sum()
    order = np.argsort(-probs)[:6]
    print(f"  {'token':<12}{'free':>9}{'constrained':>13}")
    for i in order:
        allowed = "" if mask[i] else "  (blocked)"
        print(f"  {VOCAB[i]:<12}{probs[i]:>8.1%}{masked[i]:>12.1%}{allowed}")

    print("\n[4] where the errors go")
    print(f"  free sampling      : {1 - free_valid:5.1%} unusable output, {free_valid - free_correct:5.1%} valid but wrong values")
    print(f"  constrained        : {1 - con_valid:5.1%} unusable output, {con_valid - con_correct:5.1%} valid but wrong values")


if __name__ == "__main__":
    main()
