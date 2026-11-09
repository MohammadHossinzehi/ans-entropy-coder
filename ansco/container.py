"""Self describing file format: magic, codec id, length, frequency table, payload."""
import struct
from .freq import Model, normalize_freqs
from .rans import rans_encode, rans_decode
from .rangecoder import rc_encode, rc_decode, adaptive_encode, adaptive_decode
from .tans import TANS

MAGIC = b"ANSC"
CODECS = {"rans": 1, "range": 2, "adaptive0": 3, "adaptive1": 4, "tans": 5}
NAMES = {v: k for k, v in CODECS.items()}


def _table_bytes(freqs):
    present = [(i, f) for i, f in enumerate(freqs) if f]
    out = struct.pack(">H", len(present))
    for i, f in present:
        out += struct.pack(">BI", i, f)
    return out


def _read_table(buf, pos):
    (k,) = struct.unpack_from(">H", buf, pos)
    pos += 2
    freqs = [0] * 256
    for _ in range(k):
        i, f = struct.unpack_from(">BI", buf, pos)
        freqs[i] = f
        pos += 5
    return freqs, pos


def compress(data, codec="rans", bits=12):
    head = MAGIC + bytes([CODECS[codec]]) + struct.pack(">Q", len(data))
    if not data:
        return head
    if codec.startswith("adaptive"):
        order = int(codec[-1])
        return head + adaptive_encode(data, order)
    counts = [0] * 256
    for b in data:
        counts[b] += 1
    if codec == "tans":
        bits = min(bits, 11)
    freqs = normalize_freqs(counts, bits)
    head += bytes([bits]) + _table_bytes(freqs)
    if codec == "tans":
        t = TANS(freqs, bits)
        blob, nbits, state = t.encode(data)
        return head + struct.pack(">QI", nbits, state) + blob
    model = Model(freqs, bits)
    blob = rans_encode(data, model) if codec == "rans" else rc_encode(data, model)
    return head + blob


def decompress(buf):
    if buf[:4] != MAGIC:
        raise ValueError("not an ansco file")
    codec = NAMES[buf[4]]
    (n,) = struct.unpack_from(">Q", buf, 5)
    pos = 13
    if n == 0:
        return b""
    if codec.startswith("adaptive"):
        return adaptive_decode(buf[pos:], n, int(codec[-1]))
    bits = buf[pos]
    pos += 1
    freqs, pos = _read_table(buf, pos)
    if codec == "tans":
        nbits, state = struct.unpack_from(">QI", buf, pos)
        pos += 12
        return TANS(freqs, bits).decode(buf[pos:], nbits, state, n)
    model = Model(freqs, bits)
    if codec == "rans":
        return rans_decode(buf[pos:], model, n)
    return rc_decode(buf[pos:], model, n)
