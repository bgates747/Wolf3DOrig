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
