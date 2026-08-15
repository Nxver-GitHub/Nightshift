#!/usr/bin/env python3
"""
A minimal QR encoder — byte mode, versions 1-10, error-correction levels M and H.
Pure Python stdlib: no pip, no network, no build step, same discipline as the rest of the repo.

It exists because a printed poster must regenerate from a URL at 5pm on a hotspot, and a QR
fetched from someone's web API at that moment is a poster that doesn't print.

Reference: ISO/IEC 18004. Implemented here: data encoding -> Reed-Solomon ECC -> block
interleaving -> matrix construction -> masking (all 8, scored) -> format/version info.
"""

# ── Galois field GF(256), primitive polynomial 0x11D ───────────────────────────────────────────
EXP = [0] * 512
LOG = [0] * 256
_x = 1
for _i in range(255):
    EXP[_i] = _x
    LOG[_x] = _i
    _x <<= 1
    if _x & 0x100:
        _x ^= 0x11D
for _i in range(255, 512):
    EXP[_i] = EXP[_i - 255]


def _gf_mul(a: int, b: int) -> int:
    if a == 0 or b == 0:
        return 0
    return EXP[LOG[a] + LOG[b]]


def _rs_generator(n: int) -> list:
    """Generator polynomial for n error-correction codewords."""
    g = [1]
    for i in range(n):
        g = _poly_mul(g, [1, EXP[i]])
    return g


def _poly_mul(a: list, b: list) -> list:
    out = [0] * (len(a) + len(b) - 1)
    for i, av in enumerate(a):
        for j, bv in enumerate(b):
            out[i + j] ^= _gf_mul(av, bv)
    return out


def _rs_ecc(data: list, n: int) -> list:
    """The n Reed-Solomon codewords for this data block."""
    gen = _rs_generator(n)
    rem = list(data) + [0] * n
    for i in range(len(data)):
        coef = rem[i]
        if coef:
            for j, gv in enumerate(gen):
                rem[i + j] ^= _gf_mul(gv, coef)
    return rem[len(data):]


# ── Version tables (versions 1-10 only — a URL never needs more) ──────────────────────────────
# version -> total codewords
TOTAL_CODEWORDS = {1: 26, 2: 44, 3: 70, 4: 100, 5: 134,
                   6: 172, 7: 196, 8: 242, 9: 292, 10: 346}

# (level, version) -> (ec codewords per block, [(block count, data codewords per block), ...])
BLOCKS = {
    ("M", 1): (10, [(1, 16)]),   ("H", 1): (17, [(1, 9)]),
    ("M", 2): (16, [(1, 28)]),   ("H", 2): (28, [(1, 16)]),
    ("M", 3): (26, [(1, 44)]),   ("H", 3): (22, [(2, 13)]),
    ("M", 4): (18, [(2, 32)]),   ("H", 4): (16, [(4, 9)]),
    ("M", 5): (24, [(2, 43)]),   ("H", 5): (22, [(2, 11), (2, 12)]),
    ("M", 6): (16, [(4, 27)]),   ("H", 6): (28, [(4, 15)]),
    ("M", 7): (18, [(4, 31)]),   ("H", 7): (26, [(4, 13), (1, 14)]),
    ("M", 8): (22, [(2, 38), (2, 39)]), ("H", 8): (26, [(4, 14), (2, 15)]),
    ("M", 9): (22, [(3, 36), (2, 37)]), ("H", 9): (24, [(4, 12), (4, 13)]),
    ("M", 10): (26, [(4, 43), (1, 44)]), ("H", 10): (28, [(6, 15), (2, 16)]),
}

ALIGN = {1: [], 2: [6, 18], 3: [6, 22], 4: [6, 26], 5: [6, 30],
         6: [6, 34], 7: [6, 22, 38], 8: [6, 24, 42], 9: [6, 26, 46], 10: [6, 28, 50]}

EC_BITS = {"L": 0b01, "M": 0b00, "Q": 0b11, "H": 0b10}


def _capacity(level: str, version: int) -> int:
    """Data codewords available at this version/level."""
    _, groups = BLOCKS[(level, version)]
    return sum(count * size for count, size in groups)


def _pick_version(n_bytes: int, level: str) -> int:
    """Smallest version that fits the payload, header included."""
    for v in range(1, 11):
        header = 4 + (8 if v < 10 else 16)         # mode indicator + char count
        if (header + n_bytes * 8 + 7) // 8 <= _capacity(level, v):
            return v
    raise ValueError(f"payload of {n_bytes} bytes is too long for versions 1-10 at level {level}")


# ── Stage 1: data -> codewords ────────────────────────────────────────────────────────────────
def _encode_data(data: bytes, version: int, level: str) -> list:
    count_bits = 8 if version < 10 else 16
    bits = []

    def put(value, n):
        for i in range(n - 1, -1, -1):
            bits.append((value >> i) & 1)

    put(0b0100, 4)                                  # byte mode
    put(len(data), count_bits)
    for byte in data:
        put(byte, 8)

    cap_bits = _capacity(level, version) * 8
    put(0, min(4, cap_bits - len(bits)))            # terminator
    while len(bits) % 8:                            # pad to a byte boundary
        bits.append(0)

    codewords = [int("".join(str(b) for b in bits[i:i + 8]), 2) for i in range(0, len(bits), 8)]
    for pad in _cycle_pad(_capacity(level, version) - len(codewords)):
        codewords.append(pad)
    return codewords


def _cycle_pad(n: int) -> list:
    """The standard alternating pad bytes."""
    return [0xEC if i % 2 == 0 else 0x11 for i in range(n)]


def _interleave(codewords: list, version: int, level: str) -> list:
    """Split into blocks, compute ECC per block, then interleave data and ECC as the spec requires."""
    ec_per_block, groups = BLOCKS[(level, version)]
    blocks, pos = [], 0
    for count, size in groups:
        for _ in range(count):
            blocks.append(codewords[pos:pos + size])
            pos += size
    eccs = [_rs_ecc(b, ec_per_block) for b in blocks]

    out = []
    for i in range(max(len(b) for b in blocks)):
        for b in blocks:
            if i < len(b):
                out.append(b[i])
    for i in range(ec_per_block):
        for e in eccs:
            out.append(e[i])
    return out


# ── Stage 2: the matrix ───────────────────────────────────────────────────────────────────────
def _new_matrix(version: int):
    size = version * 4 + 17
    return [[None] * size for _ in range(size)], size


def _place_function_patterns(m, size, version):
    """Finders, separators, timing, alignment, the dark module, and the reserved format areas."""
    def finder(r, c):
        for i in range(-1, 8):
            for j in range(-1, 8):
                rr, cc = r + i, c + j
                if 0 <= rr < size and 0 <= cc < size:
                    on = (0 <= i <= 6 and j in (0, 6)) or (0 <= j <= 6 and i in (0, 6)) \
                         or (2 <= i <= 4 and 2 <= j <= 4)
                    m[rr][cc] = 1 if on else 0

    finder(0, 0)
    finder(0, size - 7)
    finder(size - 7, 0)

    for i in range(size):                            # timing patterns
        if m[6][i] is None:
            m[6][i] = 1 if i % 2 == 0 else 0
        if m[i][6] is None:
            m[i][6] = 1 if i % 2 == 0 else 0

    centers = ALIGN[version]                         # alignment patterns
    if centers:
        # Only the three that would collide with a finder are omitted. The ones sitting on the
        # timing lines are legitimate and overwrite the timing modules there.
        first, last = centers[0], centers[-1]
        skip = {(first, first), (first, last), (last, first)}
        for r in centers:
            for c in centers:
                if (r, c) in skip:
                    continue
                for i in range(-2, 3):
                    for j in range(-2, 3):
                        m[r + i][c + j] = 1 if (max(abs(i), abs(j)) != 1) else 0

    m[size - 8][8] = 1                               # the always-dark module

    for i in range(9):                               # reserve format-info areas
        if m[8][i] is None:
            m[8][i] = 0
        if m[i][8] is None:
            m[i][8] = 0
    for i in range(8):
        if m[8][size - 1 - i] is None:
            m[8][size - 1 - i] = 0
        if m[size - 1 - i][8] is None:
            m[size - 1 - i][8] = 0

    if version >= 7:                                 # reserve version-info areas
        for i in range(6):
            for j in range(3):
                m[size - 11 + j][i] = 0
                m[i][size - 11 + j] = 0


def _place_data(m, size, bits):
    """Zigzag from bottom-right, two columns at a time, skipping the vertical timing column."""
    idx, upward, col = 0, True, size - 1
    while col > 0:
        if col == 6:                                  # timing column is never data
            col -= 1
        rows = range(size - 1, -1, -1) if upward else range(size)
        for row in rows:
            for c in (col, col - 1):
                if m[row][c] is None:
                    m[row][c] = bits[idx] if idx < len(bits) else 0
                    idx += 1
        upward = not upward
        col -= 2


MASKS = [
    lambda i, j: (i + j) % 2 == 0,
    lambda i, j: i % 2 == 0,
    lambda i, j: j % 3 == 0,
    lambda i, j: (i + j) % 3 == 0,
    lambda i, j: (i // 2 + j // 3) % 2 == 0,
    lambda i, j: (i * j) % 2 + (i * j) % 3 == 0,
    lambda i, j: ((i * j) % 2 + (i * j) % 3) % 2 == 0,
    lambda i, j: ((i + j) % 2 + (i * j) % 3) % 2 == 0,
]


def _penalty(m, size) -> int:
    """The four scoring rules — lower is more scannable."""
    score = 0
    # Rule 1: runs of 5+ same-colour modules in a row or column.
    for line in list(m) + [[m[r][c] for r in range(size)] for c in range(size)]:
        run, prev = 1, line[0]
        for v in line[1:]:
            if v == prev:
                run += 1
            else:
                if run >= 5:
                    score += 3 + (run - 5)
                run, prev = 1, v
        if run >= 5:
            score += 3 + (run - 5)
    # Rule 2: 2x2 blocks of one colour.
    for r in range(size - 1):
        for c in range(size - 1):
            if m[r][c] == m[r][c + 1] == m[r + 1][c] == m[r + 1][c + 1]:
                score += 3
    # Rule 3: finder-like 1:1:3:1:1 patterns with 4 light modules on either side.
    pat_a = [1, 0, 1, 1, 1, 0, 1, 0, 0, 0, 0]
    pat_b = [0, 0, 0, 0, 1, 0, 1, 1, 1, 0, 1]
    for r in range(size):
        for c in range(size - 10):
            row = [m[r][c + k] for k in range(11)]
            if row == pat_a or row == pat_b:
                score += 40
            col = [m[c + k][r] for k in range(11)]
            if col == pat_a or col == pat_b:
                score += 40
    # Rule 4: deviation from a 50/50 light-dark balance.
    dark = sum(sum(row) for row in m)
    pct = dark * 100 // (size * size)
    score += 10 * (abs(pct - 50) // 5)
    return score


def _format_bits(level: str, mask: int) -> int:
    """5 data bits + 10 BCH remainder, XOR'd with the spec's fixed mask."""
    data = (EC_BITS[level] << 3) | mask
    rem = data << 10
    while rem.bit_length() > 10:                     # generator 0b10100110111, degree 10
        rem ^= 0b10100110111 << (rem.bit_length() - 11)
    return ((data << 10) | rem) ^ 0b101010000010010


def _version_bits(version: int) -> int:
    """6 data bits + 12 BCH remainder (versions 7+ only)."""
    rem = version << 12
    while rem.bit_length() > 12:                     # generator 0b1111100100101, degree 12
        rem ^= 0b1111100100101 << (rem.bit_length() - 13)
    return (version << 12) | rem


def _apply_format(m, size, level, mask):
    """Both copies of the format info. Indices are [row][col] — easy to transpose by accident."""
    bits = _format_bits(level, mask)

    def bit(i):
        return (bits >> i) & 1

    for i in range(6):                               # copy 1: down the left, then along the top
        m[i][8] = bit(i)
    m[7][8] = bit(6)
    m[8][8] = bit(7)
    m[8][7] = bit(8)
    for i in range(9, 15):
        m[8][14 - i] = bit(i)

    for i in range(8):                               # copy 2: up from the bottom-left...
        m[8][size - 1 - i] = bit(i)
    for i in range(8, 15):                           # ...and in from the top-right
        m[size - 15 + i][8] = bit(i)
    m[size - 8][8] = 1                               # the always-dark module


def _apply_version(m, size, version):
    if version < 7:
        return
    bits = _version_bits(version)
    for i in range(18):
        bit = (bits >> i) & 1
        m[i // 3][size - 11 + i % 3] = bit
        m[size - 11 + i % 3][i // 3] = bit


def encode(text: str, level: str = "H") -> list:
    """Return the QR matrix as a list of rows of 0/1. Level H survives a scuffed print."""
    data = text.encode("utf-8")
    version = _pick_version(len(data), level)
    codewords = _encode_data(data, version, level)
    final = _interleave(codewords, version, level)

    bits = []
    for cw in final:
        for i in range(7, -1, -1):
            bits.append((cw >> i) & 1)

    base, size = _new_matrix(version)
    _place_function_patterns(base, size, version)
    reserved = [[base[r][c] is not None for c in range(size)] for r in range(size)]
    _place_data(base, size, bits)

    best, best_score = None, None
    for mask_i, mask_fn in enumerate(MASKS):
        m = [row[:] for row in base]
        for r in range(size):
            for c in range(size):
                if not reserved[r][c] and mask_fn(r, c):
                    m[r][c] ^= 1
        _apply_format(m, size, level, mask_i)
        _apply_version(m, size, version)
        s = _penalty(m, size)
        if best_score is None or s < best_score:
            best, best_score = m, s
    return best


def to_svg(matrix: list, box: int = 8, quiet: int = 4) -> str:
    """One <path> for every dark module — prints crisply at any size, no image file."""
    n = len(matrix)
    dim = (n + quiet * 2) * box
    parts = []
    for r, row in enumerate(matrix):
        for c, v in enumerate(row):
            if v:
                parts.append(f"M{(c + quiet) * box} {(r + quiet) * box}h{box}v{box}h-{box}z")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {dim} {dim}" '
            f'width="{dim}" height="{dim}" shape-rendering="crispEdges">'
            f'<rect width="{dim}" height="{dim}" fill="#fff"/>'
            f'<path fill="#000" d="{"".join(parts)}"/></svg>')


if __name__ == "__main__":
    import sys
    print(to_svg(encode(sys.argv[1] if len(sys.argv) > 1 else "https://example.com")))
