; Generated builds override only W3D_RENDER_BACKEND in a temporary source tree.
; The tracked source and ordinary manual build always retain the accepted
; standalone renderer as the default rollback path.
W3D_RENDER_BACKEND_STANDALONE: equ 0
W3D_RENDER_BACKEND_VDPLET_DIRECT: equ 1
W3D_RENDER_BACKEND:            equ W3D_RENDER_BACKEND_STANDALONE

; Acceptance-only compile-time hook. The durable builder changes this only in
; its disposable source copy when a staged scene needs indefinite observation.
; Every production build retains normal player damage and death.
W3D_DIAGNOSTIC_INVULNERABLE:   equ 0

; Acceptance-only high-score entry. 0 is every production build, 1 presents
; a guaranteed qualifying name-entry candidate, and 2 presents the original
; timed non-qualifying table. The durable builder changes only a disposable
; source copy.
W3D_DIAGNOSTIC_HIGHSCORE_MODE: equ 0

; Acceptance-only starting player state. 0xff leaves the production new-game
; defaults untouched. Disposable death-lifecycle profiles may instead begin
; on a chosen health/lives value so final-life and respawn paths can be
; reviewed without repeatedly losing ordinary games.
W3D_DIAGNOSTIC_START_HEALTH:   equ 0ffh
W3D_DIAGNOSTIC_START_LIVES:    equ 0ffh
