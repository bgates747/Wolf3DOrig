// Private scalar wall sampler. No borrowed pointer survives this column.
template<bool Linear>
void sample_wall_column(const RenderTarget &frame, uint32_t x, uint32_t y,
                        int count, const uint8_t *texture, uint8_t source_x,
                        int32_t fraction, int32_t step) {
    const uint32_t mapped_x = (frame.x_bias + x) ^ frame.pixel_xor;
    const uint8_t preserve_mask = frame.preserve_mask;
    const uint8_t color_mask = static_cast<uint8_t>(frame.color_mask & 63u);
    const uint8_t *const column = texture + source_x;
    for (int row = 0; row < count; ++row) {
        int source_y = fraction >> 16;
        if (source_y >= kTextureSize) source_y = kTextureSize - 1;
        const uint8_t color = column[source_y * kTextureSize];
        if constexpr (Linear) {
            frame.linear[(y + static_cast<uint32_t>(row)) * W3P_SCREEN_WIDTH + x] =
                static_cast<uint8_t>(color & 63u);
        } else {
            uint8_t *const pixel = reinterpret_cast<uint8_t *>(
                frame.rows[y + static_cast<uint32_t>(row)]) + mapped_x;
            *pixel = static_cast<uint8_t>((*pixel & preserve_mask) |
                                         (color & color_mask));
        }
        fraction += step;
    }
}

void draw_wall_column(const RenderTarget &frame, uint32_t x, uint32_t y,
                      int count, const uint8_t *texture, uint8_t source_x,
                      int32_t fraction, int32_t step) {
    if (frame.linear != nullptr)
        sample_wall_column<true>(frame, x, y, count, texture, source_x, fraction, step);
    else
        sample_wall_column<false>(frame, x, y, count, texture, source_x, fraction, step);
}
