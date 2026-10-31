# Generation 33 diagnosis correction r2

This document corrects one cleanup statement in the earlier immutable
`gen33-unload-amendment.md`. The wire diagnosis and proposed UNLOAD packet fix
remain correct, but `client.dat` result zero exposed a second carry-preservation
defect that the first amendment did not account for.

## Corrected guest outcome

The runtime rejected outbound handle `0x0101` with HANDLE 8 and INFO2 returned
the still-installed owned handle 1. `w3d_vdplet_unload_module` correctly set
carry after recording runtime status and retaining the handle. Its caller,
`w3d_vdplet_close`, then loaded the two handle bytes and used `or b` to test
whether the handle remained nonzero. That `or` cleared carry before `ret nz`.

The fixture therefore took the nominal-success branch, set result zero,
removed the callback, restored the video mode, wrote `client.dat`, and returned
a zero MOS status while the module handle remained installed. The headless
verifier rejected the inconsistent 16-byte result and stopped the owned
frontend. It did **not** accept cleanup. The result and source establish this
control path even though the host terminated before a restored prompt appeared
in the short UART tail.

The exact result remains:

```text
result=0 status=3 pending=0 callback_error=0
handle=1 native_error=8 token=8 schema=1
```

## Complete minimal correction

Two local changes are required:

1. Patch the original saved UNLOAD high byte into `@handle+1` before `or b`
   performs the zero test. This sends owned handle `0x0001`, not `0x0101`.
2. In `w3d_vdplet_close`, branch on the combined handle value and explicitly
   `scf` before returning when a live handle remains. Never let the handle test
   erase the unload failure carry.

If an UNLOAD error is nevertheless followed by INFO2 zero, the existing code
may clear ordinary owned buffers, retain runtime status and return carry set.
If the handle remains or ownership is foreign, callback/storage disposal stays
forbidden. No pending-reply protection or exit contract is relaxed.

Focused source regressions must pin both store-before-OR packet construction
and explicit carry reassertion on the unsafe live-handle path. The finite
fixture must continue to write result 2 and hold when pending or ownership is
ambiguous, or return a nonzero MOS status for a safe completed failure. Result
zero is reserved for completed UNLOAD, zero handle and cleanup.
