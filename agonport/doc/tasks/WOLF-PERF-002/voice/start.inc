; Task-only audio start cue. No BASIC, screen demo or firmware extension.
; Playback sequence from Extender network-hello/main.c / AgonJukebox PCM.
; All entry points are outside measured intervals; caller owns PRT failure exit.
    include "voice_duration.inc"
wp_voice_prepare:
    ld de,wp_voice_name
    call agnb_load_audio
    jp nz,wp_failed
    call w3d_audio_wait_for_vdp_ingress
    jp c,wp_failed
    ret
wp_voice_play:
    ; Match the donor: reset/enable channel, then settle6MOS ticks.
    ld hl,wp_voice_reset_enable
    ld bc,wp_voice_reset_enable_end-wp_voice_reset_enable
    rst.lil 18h
    ld hl,6
    call wp_voice_delay
    ld hl,wp_voice_select
    ld bc,wp_voice_select_end-wp_voice_select
    call wp_voice_send_ack
    ld hl,wp_voice_play_command
    ld bc,wp_voice_play_command_end-wp_voice_play_command
    call wp_voice_send_ack
    ld hl,wp_voice_play_ok
    call printString
    ld hl,WP_VOICE_WAIT_TICKS
    call wp_voice_delay
    ; Stop channel and release the dedicated sample before any timing starts.
    ld hl,wp_voice_cleanup
    ld bc,wp_voice_cleanup_end-wp_voice_cleanup
    rst.lil 18h
    call w3d_audio_wait_for_vdp_ingress
    jp c,wp_failed
    ld hl,wp_voice_rotation_start
    call printString
    ret
wp_voice_send_ack:
    push hl
    push bc
    ld c,08h
    MOSCALL mos_clearvdpflags
    pop bc
    pop hl
    rst.lil 18h
    ld c,08h
    MOSCALL mos_waitforvdpflags
    or a
    jp nz,wp_failed
    MOSCALL mos_sysvars
    ld a,(ix+0dh) ; public sysvar_audioChannel
    or a
    jp nz,wp_failed
    ld a,(ix+0eh) ; public sysvar_audioSuccess
    cp 1
    jp nz,wp_failed
    ret
wp_voice_delay:
    ld (wp_voice_delay_ticks),hl
    call wp_clock
    ld (wp_voice_delay_start),hl
@wait:
    call wp_clock
    ld de,(wp_voice_delay_start)
    or a
    sbc hl,de
    ld de,(wp_voice_delay_ticks)
    or a
    sbc hl,de
    jr c,@wait
    ret
wp_voice_delay_ticks: dl 0
wp_voice_delay_start: dl 0
wp_voice_name: db "voice.agnb",0
wp_voice_play_ok: db 13,10,"WOLF-VOICE PLAY OK",13,10,0
wp_voice_rotation_start: db 13,10,"WOLF-ROTATION START",13,10,0
wp_voice_rotation_done: db 13,10,"WOLF-ROTATION DONE",13,10,0
wp_voice_reset_enable:
    db 23,0,085h,0,10
    db 23,0,085h,0,8
wp_voice_reset_enable_end:
wp_voice_select:
    db 23,0,085h,0,4,8
    dw 0f100h
wp_voice_select_end:
wp_voice_play_command:
    db 23,0,085h,0,0,100
    dw 0,0
wp_voice_play_command_end:
wp_voice_cleanup:
    db 23,0,085h,0,10
    db 23,0,0a0h
    dw 0f100h
    db 2
wp_voice_cleanup_end:
