"""Carry-less-free range coder (Subbotin style with carry propagation via
big output buffer) plus an adaptive order-0 / order-1 byte model.

32 bit low/range with carry propagation into already written bytes.
"""

TOP = 1 << 24
MASK32 = 0xFFFFFFFF


class _Enc:
    def __init__(self):
        self.low = 0  # may exceed 32 bits (carry)
        self.range = MASK32
        self.out = bytearray()

    def encode(self, cum, freq, total):
        r = self.range // total
        self.low += r * cum
        self.range = r * freq
        while self.range < TOP:
            self._shift()

    def _shift(self):
        if self.low >> 32:  # carry
            i = len(self.out) - 1
            while self.out[i] == 0xFF:
                self.out[i] = 0
                i -= 1
            self.out[i] += 1
            self.low &= MASK32
        self.out.append((self.low >> 24) & 0xFF)
        self.low = (self.low << 8) & MASK32
        self.range = (self.range << 8) & 0xFFFFFFFF

    def finish(self):
        for _ in range(5):
            self._shift_flush()
        return bytes(self.out)

    def _shift_flush(self):
        if self.low >> 32:
            i = len(self.out) - 1
            while self.out[i] == 0xFF:
                self.out[i] = 0
                i -= 1
            self.out[i] += 1
            self.low &= MASK32
        self.out.append((self.low >> 24) & 0xFF)
        self.low = (self.low << 8) & MASK32


class _Dec:
    def __init__(self, blob):
        self.blob = blob
        self.pos = 0
        self.low = 0
        self.range = MASK32
        self.code = 0
        for _ in range(4):
            self.code = (self.code << 8) | self._next()

    def _next(self):
        b = self.blob[self.pos] if self.pos < len(self.blob) else 0
        self.pos += 1
        return b

    def target(self, total):
        self.r = self.range // total
        return min(self.code // self.r, total - 1)

    def consume(self, cum, freq):
        self.code -= self.r * cum
        self.range = self.r * freq
        while self.range < TOP:
            self.code = ((self.code << 8) | self._next()) & MASK32
            self.range = (self.range << 8) & MASK32


def rc_encode(data, model):
    e = _Enc()
    for s in data:
        e.encode(model.cum[s], model.freqs[s], model.M)
    return e.finish()


def rc_decode(blob, model, n):
    d = _Dec(blob)
    out = bytearray()
    for _ in range(n):
        t = d.target(model.M)
        s = model.slot[t]
        d.consume(model.cum[s], model.freqs[s])
        out.append(s)
    return bytes(out)


class _Adaptive:
    """Order-k adaptive frequency model with periodic halving."""

    LIMIT = 1 << 15
    INC = 24

    def __init__(self, order):
        self.order = order
        self.tables = {}

    def ctx(self, history):
        return bytes(history[-self.order:]) if self.order else b""

    def table(self, ctx):
        t = self.tables.get(ctx)
        if t is None:
            t = [1] * 256
            self.tables[ctx] = t
        return t

    def update(self, t, s):
        t[s] += self.INC
        if sum(t) > self.LIMIT:
            for i in range(256):
                t[i] = (t[i] + 1) >> 1


def adaptive_encode(data, order=1):
    m = _Adaptive(order)
    e = _Enc()
    hist = bytearray()
    for s in data:
        t = m.table(m.ctx(hist))
        cum = sum(t[:s])
        e.encode(cum, t[s], sum(t))
        m.update(t, s)
        hist.append(s)
    return e.finish()


def adaptive_decode(blob, n, order=1):
    m = _Adaptive(order)
    d = _Dec(blob)
    hist = bytearray()
    for _ in range(n):
        t = m.table(m.ctx(hist))
        total = sum(t)
        target = d.target(total)
        acc = 0
        s = 0
        while acc + t[s] <= target:
            acc += t[s]
            s += 1
        d.consume(acc, t[s])
        m.update(t, s)
        hist.append(s)
    return bytes(hist)
