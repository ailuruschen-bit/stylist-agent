"""Lab: how vector search behaves on a small wardrobe.

The lab builds toy "embeddings" for garments, then compares:

  1. cosine similarity vs. Euclidean distance on normalized vectors
  2. exact (brute force) search vs. an IVF-style search that only scans a few clusters
  3. how recall and scanned-vector count change with the number of probed clusters
  4. what filtering by category before or after the vector search does to the result

Run:  python vector_lab.py   (needs numpy)
"""

from __future__ import annotations

import time

import numpy as np

RNG_SEED = 11
DIM = 64
N_GARMENTS = 20000
CATEGORIES = ["tops", "bottoms", "outerwear", "shoes", "accessories"]


def make_dataset() -> tuple[np.ndarray, np.ndarray]:
    """Build clustered unit vectors: each category forms a few style clusters."""
    rng = np.random.default_rng(RNG_SEED)
    centers = rng.normal(size=(len(CATEGORIES) * 6, DIM))
    centers /= np.linalg.norm(centers, axis=1, keepdims=True)
    assign = rng.integers(0, len(centers), size=N_GARMENTS)
    vectors = centers[assign] + rng.normal(scale=0.35, size=(N_GARMENTS, DIM))
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    categories = np.array([CATEGORIES[c % len(CATEGORIES)] for c in assign])
    return vectors, categories


def brute_force(vectors: np.ndarray, query: np.ndarray, k: int) -> np.ndarray:
    scores = vectors @ query  # cosine similarity, vectors and query are unit length
    return np.argpartition(-scores, k)[:k][np.argsort(-scores[np.argpartition(-scores, k)[:k]])]


def kmeans(points: np.ndarray, k: int, iters: int = 15) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(RNG_SEED)
    centers = points[rng.choice(len(points), size=k, replace=False)]
    for _ in range(iters):
        labels = np.argmax(points @ centers.T, axis=1)
        for i in range(k):
            members = points[labels == i]
            if len(members):
                centers[i] = members.mean(0) / np.linalg.norm(members.mean(0))
    return centers, np.argmax(points @ centers.T, axis=1)


def main() -> None:
    vectors, categories = make_dataset()
    rng = np.random.default_rng(RNG_SEED + 1)
    queries = vectors[rng.choice(len(vectors), size=50, replace=False)] + rng.normal(
        scale=0.2, size=(50, DIM)
    )
    queries /= np.linalg.norm(queries, axis=1, keepdims=True)
    k = 10

    print(f"{N_GARMENTS} garments, {DIM} dimensions, {len(queries)} queries, top-{k}")

    # 1. Cosine vs Euclidean on unit vectors.
    q = queries[0]
    cos = vectors @ q
    l2 = np.linalg.norm(vectors - q, axis=1)
    order_cos = np.argsort(-cos)[:k]
    order_l2 = np.argsort(l2)[:k]
    print("\n[1] cosine similarity vs Euclidean distance (unit vectors)")
    print(f"  same top-{k} set: {set(order_cos.tolist()) == set(order_l2.tolist())}")
    print(f"  relation check: max |L2^2 - (2 - 2*cos)| = {np.abs(l2**2 - (2 - 2 * cos)).max():.2e}")

    # 2. Exact search timing.
    t0 = time.perf_counter()
    exact = [brute_force(vectors, q, k) for q in queries]
    exact_ms = (time.perf_counter() - t0) / len(queries) * 1000
    print(f"\n[2] exact search: {exact_ms:.1f} ms per query, scans {N_GARMENTS} vectors")

    # 3. IVF-style search: cluster once, then scan only the nearest clusters.
    n_lists = 64
    centers, labels = kmeans(vectors, n_lists)
    buckets = [np.where(labels == i)[0] for i in range(n_lists)]
    print(f"\n[3] IVF-style index: {n_lists} clusters, average {N_GARMENTS / n_lists:.0f} vectors per cluster")
    print("  probes  recall@10  scanned  ms/query")
    for probes in (1, 2, 4, 8, 16, 32):
        hits = 0
        scanned_total = 0
        t0 = time.perf_counter()
        for q, truth in zip(queries, exact):
            nearest_lists = np.argsort(-(centers @ q))[:probes]
            candidate_idx = np.concatenate([buckets[i] for i in nearest_lists])
            scanned_total += len(candidate_idx)
            scores = vectors[candidate_idx] @ q
            top = candidate_idx[np.argsort(-scores)[:k]]
            hits += len(set(top.tolist()) & set(truth.tolist()))
        ms = (time.perf_counter() - t0) / len(queries) * 1000
        print(
            f"  {probes:>6}  {hits / (k * len(queries)):>9.2%}  {scanned_total / len(queries):>7.0f}  {ms:>8.1f}"
        )

    # 4. Filtering by category: filter first vs filter after the vector search.
    target = "outerwear"
    mask = categories == target
    print(f"\n[4] filtering by category '{target}' ({mask.sum()} of {N_GARMENTS} garments)")
    post_kept = []
    pre_hits = 0
    for q in queries:
        top = brute_force(vectors, q, k)
        post_kept.append(mask[top].sum())
        sub_idx = np.where(mask)[0]
        sub_top = sub_idx[np.argsort(-(vectors[sub_idx] @ q))[:k]]
        pre_hits += len(sub_top)
    print(f"  filter after search: on average {np.mean(post_kept):.1f} of {k} results survive the filter")
    print(f"  filter before search: always {pre_hits / len(queries):.0f} results, scans only matching vectors")


if __name__ == "__main__":
    main()
