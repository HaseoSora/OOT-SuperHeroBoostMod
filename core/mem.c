/* Minimal libc pieces the compiler may emit calls to (freestanding build). */
typedef unsigned long size_t;

__attribute__((optnone)) void *memcpy(void *d, const void *s, size_t n) {
    unsigned char *dd = d;
    const unsigned char *ss = s;
    while (n--) *dd++ = *ss++;
    return d;
}

__attribute__((optnone)) void *memset(void *d, int c, size_t n) {
    unsigned char *dd = d;
    while (n--) *dd++ = (unsigned char)c;
    return d;
}

__attribute__((optnone)) int memcmp(const void *a, const void *b, size_t n) {
    const unsigned char *x = a, *y = b;
    while (n--) {
        if (*x != *y) return *x < *y ? -1 : 1;
        x++; y++;
    }
    return 0;
}
