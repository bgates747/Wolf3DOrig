# Existing-row support and intended work

Control renderer is PERF-004/r03/candidate native-source and production
wolf3d_renderer.cpp SHAbe04d1a8511c8ccee6a4d8d39800c8b3bde45b54d63d7e8a7f06c89d76424adb.
It built exact54568e45 and passed physical63. The immutable PERF-003/r04 SDK,
native7593 and ABI1.6 scoped COLOR_FRAME rows remain the target. Source review
verdict for this one local correction: supported as presently constituted;
no firmware/API/provider extension or replacement method is required.

| Source unit/method | Existing support and disposition | Work/invariants |
| --- | --- | --- |
| fill_span linear path | Existing clear_bytes(target_pixel(...)); unchanged | Keep copied RGB222 oracle semantics and all callers |
| Direct fill_span/put_pixel/target_pixel chain | Already admitted finite hidden-row bytes and mapping fields; specialize this local branch only | One row lookup and invariant mapping/mask setup per nonempty span instead of repeating generic helper calls |
| Per-byte pixel address | Same uint32 mapping (x_bias+x)^pixel_xor | Preserve addition/XOR order and unsigned wrap; never assume contiguous mapped pixels or whole contiguous framebuffer |
| Colour merge | Same (old_byte & preserve_mask) OR (color & color_mask) | Read each actual old byte at its store, including varied/overlapping masks; do not hoist old sync bits |
| Zero count | Original direct loop touches no row/pixel for count0 | Return before row-table lookup; include null-row/invalid-y zero-count regression |
| Bounds/clipping | Existing fill_rect clips and valid render callers bound spans | Preserve inclusive edge/count semantics; no new accepted out-of-range access or widened store |
| Row lifetime | Existing BEGIN/ROW/END; wrapper owns row-pointer table/descriptor separately from pixels | Borrow one row pointer only within span/frame; no callbacks/service calls/persistent pointer, caching across END, page change or metadata alias introduced |
| Target safety/byte semantics | Existing SDK Os/PIC/fno-builtin/PSRAM workaround | Inspect actual L8UI/S8I path and retained required barriers; no wider writes or hand-added private fast helper |
| Other draw units and helpers | Existing module/render pipeline unchanged | Keep all other put_pixel callers, lower40clear, DDA/divider/trig/assets/leases/publication/error/observer/representation unchanged |
| Host/physical consumer support | Existing module transaction and qualified runner | Explicit verify-owned backup retirement; no hidden fallback or altered work/completion witness |

The production wrapper currently admits native rows with x_bias0/XOR2,
colour3f/preservec0 and stable geometry until END. Pure-helper tests should also
retain the generic mapping/mask algebra rather than relying on complements or
one fixed sync-bit pattern. Such tests are not qualification of additional
physical ABI modes. Valid row storage does not overlap its descriptor/table;
those are separately owned wrapper/workspace objects. The candidate performs
no intervening service call that could change their values. Hidden DMA scanout
and sync values remain read/merged independently for each written byte.

Source-level prediction is removal of repeated generic local dispatch and
field/address loads in the fill path. Actual compiled control/candidate code
must establish whether the calls/branches disappear and byte accesses/safety
remain. Keep exact control reproduction, numerical/provider/code/resource and
pixel/state/lifetime gates before measuring. Any mismatch reopens the relevant
binding; unsupported mechanisms are recorded without a workaround. This local
supported correction does not retrospectively approve the historical Canvas-
to-per-pixel method substitution identified by the conversion self-review.
