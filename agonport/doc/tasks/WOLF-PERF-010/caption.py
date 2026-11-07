"""Small fixture-owned capital bitmap; no dependency on the selected VDP font."""
TEXT = 'STATIC TIMER TESTING ONLY'
GLYPHS = {
    ' ': ['00000'] * 7,
    'A': ['01110','10001','10001','11111','10001','10001','10001'],
    'C': ['01111','10000','10000','10000','10000','10000','01111'],
    'E': ['11111','10000','10000','11110','10000','10000','11111'],
    'G': ['01111','10000','10000','10111','10001','10001','01111'],
    'I': ['11111','00100','00100','00100','00100','00100','11111'],
    'L': ['10000','10000','10000','10000','10000','10000','11111'],
    'M': ['10001','11011','10101','10101','10001','10001','10001'],
    'N': ['10001','11001','11001','10101','10011','10011','10001'],
    'O': ['01110','10001','10001','10001','10001','10001','01110'],
    'R': ['11110','10001','10001','11110','10100','10010','10001'],
    'S': ['01111','10000','10000','01110','00001','00001','11110'],
    'T': ['11111','00100','00100','00100','00100','00100','00100'],
    'Y': ['10001','10001','01010','00100','00100','00100','00100'],
}
WIDTH = len(TEXT) * 12 - 2
HEIGHT = 14
X = (320 - WIDTH) // 2
Y = 183
BUFFER = 0xf1b0


def pixels():
    out = bytearray([0xc0] * (WIDTH * HEIGHT))
    for i, char in enumerate(TEXT):
        for row, bits in enumerate(GLYPHS[char]):
            for col, bit in enumerate(bits):
                if bit == '1':
                    for dy in range(2):
                        for dx in range(2):
                            out[(row * 2 + dy) * WIDTH + i * 12 + col * 2 + dx] = 0xff
    return bytes(out)


def assembly():
    raw = pixels()
    # This entire include is conditional on the STATIC control mode.
    text = f'''wp_static_caption_paint:
    ld a,(wp_static_caption_owned)
    or a
    jr nz,@draw
    ; This fixture owns this private ID; no production bank uses it.
    ld hl,0{BUFFER:04x}h
    call vdu_clear_buffer
    ld hl,0{BUFFER:04x}h
    ld bc,{len(raw)}
    ld de,wp_static_caption_pixels
    call vdu_load_buffer
    ld hl,0{BUFFER:04x}h
    call vdu_buff_select
    ld a,1 ; RGBA2222, opaque black/white bytes
    ld bc,{WIDTH}
    ld de,{HEIGHT}
    call vdu_bmp_create
    ld a,1
    ld (wp_static_caption_owned),a
@draw:
    ld hl,wp_static_caption_draw
    ld bc,wp_static_caption_draw_end-wp_static_caption_draw
    rst.lil 018h
    ret
wp_static_caption_close:
    ld a,(wp_static_caption_owned)
    or a
    ret z
    ; Parser order: drain every queued bitmap draw before destroying its bytes.
    ld hl,wp_static_caption_flush
    ld bc,3
    rst.lil 018h
    ld hl,0{BUFFER:04x}h
    call vdu_clear_buffer
    call w3d_audio_wait_for_vdp_ingress
    jr c,@failed
    xor a
    ld (wp_static_caption_owned),a
    ret
@failed:
    ld hl,wp_static_caption_failure
    jp printString
wp_static_caption_failure: db "STATIC CAPTION CLEANUP FAILED",13,10,0
wp_static_caption_owned: db 0
wp_static_caption_flush: db 23,0,0cah
wp_static_caption_draw:
    db 23,27,020h
    dw 0{BUFFER:04x}h
    db 23,27,3
    dw {X},{Y}
wp_static_caption_draw_end:
wp_static_caption_pixels:
'''
    text += ''.join('    db ' + ','.join(f'0{x:02x}h' for x in raw[i:i+24]) + '\n'
                    for i in range(0, len(raw), 24))
    return text
