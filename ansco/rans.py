"""Byte-wise renormalizing rANS (Duda 2013, Giesen's variant).

State x lives in [L, 256*L) with L = 2**23. Encoding runs over the data in
reverse so decoding emerges in forward order. The final state is flushed as
4 bytes. Compression is within ~0.01% of the model entropy for 12 bit tables.
"""
from .freq import Model

L = 1 << 23


def rans_encode(data, model):
    x = L
    out = bytearray()
    bits, freqs, cum = model.bits, model.freqs, model.cum
    for s in reversed(data):
        f = freqs[s]
        if f == 0:
            raise ValueError("symbol %d has zero frequency" % s)
        x_max = ((L >> bits) << 8) * f
        while x >= x_max:
            out.append(x & 0xFF)
            x >>= 8
        x = ((x // f) << bits) + (x % f) + cum[s]
    for _ in range(4):
        out.append(x & 0xFF)
        x >>= 8
    out.reverse()
    return bytes(out)


def rans_decode(blob, model, n):
    x = int.from_bytes(blob[:4], "big")
    pos = 4
    mask = model.M - 1
    bits, freqs, cum, slot = model.bits, model.freqs, model.cum, model.slot
    out = bytearray()
    for _ in range(n):
        r = x & mask
        s = slot[r]
        out.append(s)
        x = freqs[s] * (x >> bits) + r - cum[s]
        while x < L:
            x = (x << 8) | blob[pos]
            pos += 1
    return bytes(out)
