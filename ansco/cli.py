"""CLI: python -m ansco.cli compress|decompress|bench FILE"""
import argparse
import sys
import time
from . import compress, decompress, entropy, Model, huffman_lengths, huffman_encode, rans_encode


def bench(data):
    print("input bytes: %d   order 0 entropy: %.4f bits/byte  (ideal %d bytes)"
          % (len(data), entropy(data), int(entropy(data) * len(data) / 8) + 1))
    counts = [0] * 256
    for b in data:
        counts[b] += 1
    hb, _ = huffman_encode(data, huffman_lengths(counts))
    print("%-10s %9d bytes  (payload only, Huffman baseline)" % ("huffman", len(hb)))
    for codec in ("rans", "tans", "range", "adaptive0", "adaptive1"):
        t = time.time()
        c = compress(data, codec)
        dt = time.time() - t
        ok = decompress(c) == data
        print("%-10s %9d bytes  ratio %.3f  %.2fs  roundtrip %s"
              % (codec, len(c), len(c) / max(1, len(data)), dt, "ok" if ok else "FAIL"))


def main(argv=None):
    p = argparse.ArgumentParser(prog="ansco")
    p.add_argument("cmd", choices=["compress", "decompress", "bench"])
    p.add_argument("file")
    p.add_argument("-o", "--output")
    p.add_argument("-c", "--codec", default="rans",
                   choices=["rans", "tans", "range", "adaptive0", "adaptive1"])
    a = p.parse_args(argv)
    data = open(a.file, "rb").read()
    if a.cmd == "bench":
        bench(data)
        return 0
    out = compress(data, a.codec) if a.cmd == "compress" else decompress(data)
    if a.output:
        open(a.output, "wb").write(out)
    else:
        sys.stdout.buffer.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
