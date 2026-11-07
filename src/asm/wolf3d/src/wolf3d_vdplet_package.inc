; The durable backend builder rewrites this value only in its temporary source
; tree. Zero is a fail-closed placeholder: tracked source never claims that a
; production module package exists.
W3D_VDPLET_PACKAGE_BYTES: equ 0
; Also serves as a 4096-byte zero-upload scratch page after native LOAD.
W3D_VDPLET_PACKAGE_STORAGE_BYTES: equ 4096
