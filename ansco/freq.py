"""Frequency tables: counting, normalization to a power of two total, entropy."""
import math
from collections import Counter


def entropy(data):
    """Shannon entropy in bits per symbol of a byte string."""
    n = len(data)
    if n == 0:
        return 0.0
    return -sum(c / n * math.log2(c / n) for c in Counter(data).values())


def normalize_freqs(counts, total_bits):
    """Scale raw counts (list of 256 ints) so they sum to exactly 2**total_bits.

    Every symbol that occurs keeps frequency >= 1. The rounding error is
    repaired greedily by the symbol whose change costs the least expected
    code length (steal from / give to the best candidate), so the result is
    near optimal rather than just 'dump the error on the largest symbol'.
    """
    M = 1 << total_bits
    total = sum(counts)
    present = [i for i, c in enumerate(counts) if c]
    if not present:
        raise ValueError("empty model")
    if len(present) > M:
        raise ValueError("alphabet larger than table size")
    freqs = [0] * len(counts)
    for i in present:
        freqs[i] = max(1, counts[i] * M // total)
    diff = M - sum(freqs)
    while diff != 0:
        best, best_cost = None, None
        for i in present:
            f = freqs[i]
            if diff > 0:
                # cost change of f -> f+1 :  c * log2(f/(f+1))  (negative gain)
                cost = counts[i] * math.log2(f / (f + 1))
            else:
                if f <= 1:
                    continue
                cost = counts[i] * math.log2(f / (f - 1))
            if best_cost is None or cost < best_cost:
                best, best_cost = i, cost
        freqs[best] += 1 if diff > 0 else -1
        diff += -1 if diff > 0 else 1
    return freqs


class Model:
    """Static model: normalized freqs, cumulative table, slot->symbol lookup."""

    def __init__(self, freqs, total_bits):
        self.bits = total_bits
        self.M = 1 << total_bits
        if sum(freqs) != self.M:
            raise ValueError("frequencies must sum to 2**bits")
        self.freqs = list(freqs)
        self.cum = [0] * (len(freqs) + 1)
        for i, f in enumerate(freqs):
            self.cum[i + 1] = self.cum[i] + f
        self.slot = bytearray(self.M)
        for s, f in enumerate(freqs):
            for j in range(self.cum[s], self.cum[s] + f):
                self.slot[j] = s

    @classmethod
    def from_data(cls, data, total_bits=12):
        counts = [0] * 256
        for b in data:
            counts[b] += 1
        return cls(normalize_freqs(counts, total_bits), total_bits)

    def cost_bits(self, data):
        """Ideal code length of data under this model."""
        return sum(-math.log2(self.freqs[b] / self.M) for b in data)
