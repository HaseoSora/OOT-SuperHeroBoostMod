"""CityHash64 (Google CityHash v1.1.1), strings up to 64 bytes. Own implementation.

The game's UI resources store a 64-bit hash next to every pane/part name; a part
we register under a new name needs the matching hash.
"""
M = (1 << 64) - 1
K0 = 0xC3A5C85C97CB3127
K1 = 0xB492B66FBE98F273
K2 = 0x9AE16A3B2F90404F


def _f64(s, i): return int.from_bytes(s[i:i + 8], "little")
def _f32(s, i): return int.from_bytes(s[i:i + 4], "little")
def _rot(v, n): return v if n == 0 else ((v >> n) | (v << (64 - n))) & M
def _smix(v): return v ^ (v >> 47)
def _bswap(v): return int.from_bytes(v.to_bytes(8, "little"), "big")


def _h16(u, v, mul):
    a = ((u ^ v) * mul) & M
    a ^= a >> 47
    b = ((v ^ a) * mul) & M
    b ^= b >> 47
    return (b * mul) & M


def city_hash64(data: bytes) -> int:
    n = len(data)
    if n > 64:
        raise ValueError("only names up to 64 bytes are supported")
    s = data
    if n <= 16:
        if n >= 8:
            mul = (K2 + n * 2) & M
            a = (_f64(s, 0) + K2) & M
            b = _f64(s, n - 8)
            c = (_rot(b, 37) * mul + a) & M
            d = ((_rot(a, 25) + b) * mul) & M
            return _h16(c, d, mul)
        if n >= 4:
            mul = (K2 + n * 2) & M
            a = _f32(s, 0)
            return _h16((n + (a << 3)) & M, _f32(s, n - 4), mul)
        if n > 0:
            a, b, c = s[0], s[n >> 1], s[n - 1]
            y = (a + (b << 8)) & 0xFFFFFFFF
            z = (n + (c << 2)) & 0xFFFFFFFF
            return (_smix((y * K2) ^ (z * K0)) * K2) & M
        return K2
    if n <= 32:
        mul = (K2 + n * 2) & M
        a = (_f64(s, 0) * K1) & M
        b = _f64(s, 8)
        c = (_f64(s, n - 8) * mul) & M
        d = (_f64(s, n - 16) * K2) & M
        return _h16((_rot((a + b) & M, 43) + _rot(c, 30) + d) & M,
                    (a + _rot((b + K2) & M, 18) + c) & M, mul)
    mul = (K2 + n * 2) & M
    a = (_f64(s, 0) * K2) & M
    b = _f64(s, 8)
    c = _f64(s, n - 24)
    d = _f64(s, n - 32)
    e = (_f64(s, 16) * K2) & M
    f = (_f64(s, 24) * 9) & M
    g = _f64(s, n - 8)
    h = (_f64(s, n - 16) * mul) & M
    u = (_rot((a + g) & M, 43) + (_rot(b, 30) + c) * 9) & M
    v = ((((a + g) & M) ^ d) + f + 1) & M
    w = (_bswap(((u + v) * mul) & M) + h) & M
    x = (_rot((e + f) & M, 42) + c) & M
    y = ((_bswap(((v + w) * mul) & M) + g) * mul) & M
    z = (e + f + c) & M
    a = (_bswap((((x + z) * mul) + y) & M) + b) & M
    b = (_smix((((z + a) * mul) + d + h) & M) * mul) & M
    return (b + x) & M
