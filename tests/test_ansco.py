import os, random, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ansco import *
from ansco.freq import normalize_freqs


def samples():
    rnd = random.Random(7)
    yield b"a"
    yield b"aaaaaaaaaaaaaaaaaaaa"
    yield bytes(range(256))
    yield b"abracadabra" * 50
    yield bytes(rnd.choice(b"aaaaaaab") for _ in range(3000))
    yield bytes(int(rnd.expovariate(0.1)) % 256 for _ in range(5000))
    yield os.urandom(2000)
    yield open(__file__, "rb").read()


class Roundtrip(unittest.TestCase):
    def test_all_codecs(self):
        for codec in ("rans", "tans", "range", "adaptive0", "adaptive1"):
            for d in samples():
                self.assertEqual(decompress(compress(d, codec)), d, codec)

    def test_empty(self):
        for codec in ("rans", "range", "tans"):
            self.assertEqual(decompress(compress(b"", codec)), b"")

    def test_fuzz(self):
        rnd = random.Random(1)
        for _ in range(150):
            n = rnd.randint(1, 400)
            k = rnd.randint(1, 20)
            d = bytes(rnd.randrange(k) for _ in range(n))
            for codec in ("rans", "tans", "range"):
                self.assertEqual(decompress(compress(d, codec, bits=rnd.choice([8, 10, 12]))), d)

    def test_huffman(self):
        for d in samples():
            counts = [0] * 256
            for b in d:
                counts[b] += 1
            L = huffman_lengths(counts)
            blob, nb = huffman_encode(d, L)
            self.assertEqual(huffman_decode(blob, nb, L, len(d)), d)


class Efficiency(unittest.TestCase):
    def test_rans_near_entropy(self):
        rnd = random.Random(3)
        d = bytes(rnd.choice(b"aaaaaaaabbbbccd") for _ in range(20000))
        ideal = entropy(d) * len(d) / 8
        for codec in ("rans", "range", "tans"):
            size = len(compress(d, codec)) - 40
            self.assertLess(size, ideal * 1.01 + 8, codec)

    def test_beats_huffman_on_skewed(self):
        d = b"a" * 9900 + b"b" * 100
        counts = [0] * 256
        counts[97], counts[98] = 9900, 100
        hb, _ = huffman_encode(d, huffman_lengths(counts))
        self.assertLess(len(compress(d, "rans")), len(hb) // 5)

    def test_normalize_sums(self):
        rnd = random.Random(5)
        for _ in range(50):
            counts = [rnd.choice([0, 0, 1, 5, 1000]) for _ in range(256)]
            counts[0] = max(counts[0], 1)
            f = normalize_freqs(counts, 12)
            self.assertEqual(sum(f), 4096)
            self.assertTrue(all((f[i] > 0) == (counts[i] > 0) for i in range(256)))

    def test_carry_propagation(self):
        d = b"\xff" * 3000 + b"\x00" * 3000 + b"\xff" * 10
        self.assertEqual(decompress(compress(d, "range", bits=15)), d)


if __name__ == "__main__":
    unittest.main()
