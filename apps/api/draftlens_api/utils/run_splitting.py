from __future__ import annotations


def split_indices_for_runs(total: int, batch_size: int) -> list[tuple[int, int]]:
    """
    Deterministic half-open index ranges [start, end) for batched / parallel review runs.

    Used by the pipeline when fanning work across blocks or model calls; tests lock the contract.
    """
    if total < 0:
        raise ValueError("total must be non-negative")
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    out: list[tuple[int, int]] = []
    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        out.append((start, end))
    return out
