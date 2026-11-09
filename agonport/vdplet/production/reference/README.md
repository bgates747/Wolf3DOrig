# Older reciprocal-DDA test reference

This is the pre-promotion maintained renderer, retained only for numerical and
legacy-method regression checks. It is not linked into the production game.
`fixed_div` now scales with an int64 multiplication by 65536; a negative signed
left shift is undefined in C++17. The existing nonzero-divisor and int32 quotient
domains are unchanged. Boundary/negative cases execute under UBSan. Historical
frozen controls remain unchanged. The new original-tangent renderer has no
`fixed_div` and uses the separately qualified original-method geometry.
