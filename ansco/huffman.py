"""Canonical Huffman coding, as the classic baseline to compare ANS against."""
import heapq


def huffman_lengths(counts):
    items = [(c, i, (i,)) for i, c in enumerate(counts) if c]
    if not items:
        return [0] * len(counts)
    lengths = [0] * len(counts)
    if len(items) == 1:
        lengths[items[0][1]] = 1
        return lengths
    heap = [(c, i, syms) for c, i, syms in items]
    heapq.heapify(heap)
    uid = len(counts)
    while len(heap) > 1:
        c1, _, s1 = heapq.heappop(heap)
        c2, _, s2 = heapq.heappop(heap)
        for s in s1 + s2:
            lengths[s] += 1
        heapq.heappush(heap, (c1 + c2, uid, s1 + s2))
        uid += 1
    return lengths


def _canonical(lengths):
    syms = sorted((l, s) for s, l in enumerate(lengths) if l)
    codes, code, prev = {}, 0, 0
    for l, s in syms:
        code <<= (l - prev)
        codes[s] = (code, l)
        code += 1
        prev = l
    return codes


def huffman_encode(data, lengths):
    codes = _canonical(lengths)
    acc, nbits = 0, 0
    for s in data:
        c, l = codes[s]
        acc = (acc << l) | c
        nbits += l
    pad = (-nbits) % 8
    acc <<= pad
    return acc.to_bytes((nbits + pad) // 8, "big"), nbits


def huffman_decode(blob, nbits, lengths, n):
    codes = _canonical(lengths)
    rev = {(l, c): s for s, (c, l) in codes.items()}
    acc = int.from_bytes(blob, "big") >> (len(blob) * 8 - nbits)
    out = bytearray()
    code, l = 0, 0
    for i in range(nbits - 1, -1, -1):
        code = (code << 1) | ((acc >> i) & 1)
        l += 1
        s = rev.get((l, code))
        if s is not None:
            out.append(s)
            code, l = 0, 0
    assert len(out) == n
    return bytes(out)
