namespace original {
union WideWords {
    uint64_t value;
    struct { uint32_t low, high; } words;
};

static bool wide_at_least(const WideWords &left, const WideWords &right) {
    return left.words.high > right.words.high ||
        (left.words.high == right.words.high && left.words.low >= right.words.low);
}

static void wide_subtract(WideWords &left, const WideWords &right) {
    const uint32_t old_low = left.words.low;
    left.words.low -= right.words.low;
    left.words.high -= right.words.high + (old_low < right.words.low ? 1u : 0u);
}

static WideWords wide_negate(WideWords value) {
    value.words.low = ~value.words.low + 1u;
    value.words.high = ~value.words.high + (value.words.low == 0 ? 1u : 0u);
    return value;
}

static uint64_t divide_u64(uint64_t numerator, uint64_t denominator) {
    WideWords dividend = {numerator};
    WideWords divisor = {denominator};
    if (divisor.words.low == 0 && divisor.words.high == 0) return UINT64_MAX;
    WideWords quotient = {0};
    WideWords remainder = {0};
    for (int bit = 63; bit >= 0; --bit) {
        const uint32_t source_bit = bit >= 32
            ? ((dividend.words.high >> (bit - 32)) & 1u)
            : ((dividend.words.low >> bit) & 1u);
        remainder.words.high = (remainder.words.high << 1) |
                               (remainder.words.low >> 31);
        remainder.words.low = (remainder.words.low << 1) | source_bit;
        if (wide_at_least(remainder, divisor)) {
            wide_subtract(remainder, divisor);
            if (bit >= 32) quotient.words.high |= 1u << (bit - 32);
            else quotient.words.low |= 1u << bit;
        }
    }
    return quotient.value;
}

extern "C" uint64_t original_udiv(uint64_t numerator, uint64_t denominator) {
    return divide_u64(numerator, denominator);
}

extern "C" int64_t original_sdiv(int64_t numerator, int64_t denominator) {
    const bool negative = (numerator < 0) != (denominator < 0);
    WideWords unsigned_numerator = {static_cast<uint64_t>(numerator)};
    WideWords unsigned_denominator = {static_cast<uint64_t>(denominator)};
    if (numerator < 0) unsigned_numerator = wide_negate(unsigned_numerator);
    if (denominator < 0) unsigned_denominator = wide_negate(unsigned_denominator);
    WideWords quotient = {
        divide_u64(unsigned_numerator.value, unsigned_denominator.value)};
    if (negative) quotient = wide_negate(quotient);
    return static_cast<int64_t>(quotient.value);
}
}
