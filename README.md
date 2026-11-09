# ans-entropy-coder

Entropy coding from scratch in pure Python: **rANS**, **tANS (FSE)**, a **range coder** with carry propagation, adaptive order 0 and order 1 context models, and a canonical **Huffman** baseline. Zero dependencies.

## Why

Asymmetric numeral systems (Duda, 2013) replaced Huffman and arithmetic coding in Zstandard, LZFSE, JPEG XL and AV1 tooling because they reach arithmetic coding compression at Huffman speed. This repo implements the whole family side by side so you can read the code, compare sizes and see exactly where each method wins.

## What is inside

| Module | Contents |
| --- | --- |
| `ansco/freq.py` | Counting, entropy, normalisation of counts to a power of two total with a greedy minimum cost rounding repair, slot lookup table |
| `ansco/rans.py` | Byte renormalising rANS (state in `[2^23, 2^31)`), encodes in reverse so decoding is forward |
| `ansco/tans.py` | Table ANS / Finite State Entropy: FSE symbol spread, decode table with `(symbol, nbits, base)`, no multiplications when decoding |
| `ansco/rangecoder.py` | 32 bit range coder with carry propagation, plus adaptive order 0/1 models with periodic halving |
| `ansco/huffman.py` | Canonical Huffman codes as the classic baseline |
| `ansco/container.py` | Self describing `ANSC` file format (codec id, length, frequency table, payload) |
| `ansco/cli.py` | `compress`, `decompress` and `bench` commands |

## Run it

```
python -m ansco.cli bench some_file.txt
python -m ansco.cli compress some_file.txt -c rans -o some_file.ansc
python -m ansco.cli decompress some_file.ansc -o roundtrip.txt
python -m unittest discover -s tests
```

Codecs: `rans`, `tans`, `range`, `adaptive0`, `adaptive1`. Python 3.8+.

```python
from ansco import compress, decompress
blob = compress(b"abracadabra" * 100, "rans")
assert decompress(blob) == b"abracadabra" * 100
```

## Design notes

* **Reverse encoding.** ANS is a stack: the last symbol encoded is the first decoded. Both rANS and tANS therefore encode the input back to front, so the decoder streams forward.
* **Normalisation matters.** Rounding frequencies to a 12 bit table costs real bits if done carelessly. `normalize_freqs` keeps every present symbol at frequency at least 1 and repairs the rounding error by repeatedly picking the symbol whose change increases expected code length least, instead of dumping the error on the most common symbol.
* **Where ANS beats Huffman.** Huffman spends at least one bit per symbol. On a source that is 99% one byte, Huffman cannot go below 1 bit per symbol while ANS approaches the entropy of roughly 0.08 bits. A test asserts rANS is more than 5 times smaller there.
* **Carry handling.** The range coder keeps `low` wider than 32 bits and propagates a carry backwards through trailing `0xFF` bytes. A dedicated test uses long runs of `0xFF` and `0x00` to exercise it.
* **tANS.** Uses the FSE step `(size>>1) + (size>>3) + 3`, which is coprime to power of two sizes, so the spread visits every slot exactly once.

## Testing

`tests/test_ansco.py` covers roundtrips for every codec on edge inputs (single byte, runs, all 256 values, random data, source text), 150 randomised fuzz cases with varied table sizes, empty input, frequency normalisation invariants, carry propagation, closeness to Shannon entropy (within 1% on a 20k byte skewed source) and the Huffman comparison.

## Limits

This is a clear reference implementation, not a fast one: pure Python runs at roughly a few hundred KB per second. The adaptive coders use linear cumulative sums per symbol for simplicity.

## License

MIT
