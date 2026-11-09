"""tANS / FSE: table based asymmetric numeral systems (finite state entropy).

Symbols are spread over a table of size 2**R with the FSE step function,
then encode/decode tables are derived. Decoding is a single table lookup
plus a bit read per symbol, with no multiplication.
"""


class TANS:
    def __init__(self, freqs, table_bits):
        self.R = table_bits
        self.size = 1 << table_bits
        if sum(freqs) != self.size:
            raise ValueError("freqs must sum to 2**table_bits")
        self.freqs = list(freqs)
        size = self.size
        step = (size >> 1) + (size >> 3) + 3
        spread = [0] * size
        pos = 0
        for s, f in enumerate(freqs):
            for _ in range(f):
                spread[pos] = s
                pos = (pos + step) & (size - 1)
        if pos != 0:
            raise ValueError("table size must make the step coprime (use >= 5 bits)")
        # decode table: state i in [0,size) -> (symbol, nbits, newbase)
        nxt = list(freqs)
        self.dec = [None] * size
        for i in range(size):
            s = spread[i]
            x = nxt[s]
            nxt[s] += 1
            nb = self.R - (x.bit_length() - 1)
            self.dec[i] = (s, nb, (x << nb) - size)
        # encode table: for each symbol, list of target states indexed by x - f
        self.enc = {}
        for i in range(size):
            s = spread[i]
            self.enc.setdefault(s, []).append(i)

    def encode(self, data):
        """Returns (bitstring_bytes, nbits, final_state). Encodes in reverse."""
        size, freqs = self.size, self.freqs
        x = size  # any state in [size, 2*size) valid; start at size
        chunks = []  # list of (value, nbits) in encode order
        for s in reversed(data):
            f = freqs[s]
            # shrink x into [f, 2f) by emitting low bits
            nb = 0
            while (x >> nb) >= 2 * f:
                nb += 1
            chunks.append((x & ((1 << nb) - 1), nb))
            x >>= nb
            x = self.enc[s][x - f] + size
        acc, total = 0, 0
        # write chunks so the decoder, reading forward, gets them in reverse
        for v, nb in reversed(chunks):
            acc = (acc << nb) | v
            total += nb
        pad = (-total) % 8
        acc <<= pad
        nbytes = (total + pad) // 8
        return acc.to_bytes(nbytes, "big"), total, x - size

    def decode(self, blob, nbits, state, n):
        acc = int.from_bytes(blob, "big")
        total = len(blob) * 8
        pad = total - nbits
        acc >>= pad
        remaining = nbits
        out = bytearray()
        x = state
        for _ in range(n):
            s, nb, base = self.dec[x]
            out.append(s)
            remaining -= nb
            v = (acc >> remaining) & ((1 << nb) - 1) if nb else 0
            x = base + v
        return bytes(out)
