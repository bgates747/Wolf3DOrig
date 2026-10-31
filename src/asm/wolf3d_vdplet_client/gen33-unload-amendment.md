# Generation 33 production-client UNLOAD amendment

This amendment freezes the second production-client target failure before its
minimal Wolf-owned source correction. It does not alter the immutable
generation-31 diagnosis, accepted copied renderer/module, shared runtime,
standalone default, or any physical result.

## Frozen generation-33 result

- lease: `54f4fbacc55c4c4ab39d2b7505260424`
- client: `b65883fd8d7293430b3384ea1e5484fd04b72c4dd72abb6a5a6f8bfb96ca71d3`
- copied module: `57b635fc...`
- exact displayed scene: `42e227e80bba3cd7d65dc1bc1bee0b87e5d233e1cd8d3a1dd4f26805499bb4a2`
- `client.dat`: `b57ad1ceac22e1439cbe13cdd823573d75ab10eb7d60b28c5d8bc0bea70386e2`
- outbound wire: `f45118256adcb709290e19ef022dc1b295abc760701cd5d73153971282390f70a`
- delivered reverse wire:
  `36fbf8c95624513006ec2b9849c69646ff48ce9807c900ab173bd57fc018e28d`
- preserved ignored evidence: `tgt/oryx-failure-gen33/`

The one authorized run passed discovery, INFO0/1/2, package upload, LOAD,
CONFIG, RENDER, exact scene comparison and real key injection. Its result was:

```text
result=0 status=3 pending=0 callback_error=0
handle=1 native_error=8 token=8 schema=1
```

The host stopped its owned process after this mismatch. The guest did not claim
cleanup or return to MOS: it deliberately retained callback, handle and
referenced storage in the ambiguity hold. A fresh whole-host inspection was
empty, and generation 33 was released before this analysis.

## Exact wire diagnosis

The requested replies were:

```text
IDENT  token 0 value 31
VALUE  token 1 value 256   ; INFO0
VALUE  token 2 value 31    ; INFO1
VALUE  token 3 value 0     ; INFO2 before LOAD
LOADED token 4 value 1
DONE   token 5 value 0     ; CONFIG
DONE   token 6 value 0     ; RENDER
ERROR  token 7 value 8     ; UNLOAD
VALUE  token 8 value 1     ; INFO2 after error
```

The outbound UNLOAD tail was `01 01`, requesting handle `0x0101`, although the
owned handle was `0x0001`. The client loaded high byte zero into A, executed
`or b` with low byte one to test whether the handle was nonzero, and then stored
the combined A value into the packet's high byte. The runtime correctly rejected
the foreign/stale `0x0101` with HANDLE 8. INFO2 correctly proved that owned
handle 1 remained installed. The client therefore correctly retained ownership
and refused destructive cleanup.

This is an eZ80 packet-patching defect, not native FINI error provenance and
not a runtime, service or module defect.

## Proposed minimal correction

Store the original high byte into `@handle+1` before `or b` performs the zero
test. Patching zero/zero before the early return is harmless. No packet layout,
token, timeout, INFO2, ownership or cleanup semantics change.

Before any new readiness claim, a focused regression must pin the store-before-
OR order, the fixture and full candidate must assemble, both prior
zero-extension checks must remain, the standalone hash must remain exact, and
the stopped profile must be rebuilt with new source/app/manifest hashes.
