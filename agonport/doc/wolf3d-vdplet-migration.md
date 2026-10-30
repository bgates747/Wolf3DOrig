# Wolf3D renderer VDPlet migration

## Executive summary

Wolf3DOrig currently requires a complete custom VDP firmware containing its
renderer. This task will determine whether that renderer can instead be built
as a loadable VDPlet on the shared VDPlet runtime, allowing ordinary runtime
firmware to load Wolf3D support only when the game needs it. The first phase is
research and planning only. No renderer, firmware, protocol, or application
implementation may begin until the Author reviews the feasibility result.

## Objective

Preserve the accepted Wolf3DOrig game, rendering behavior, assets, maps,
simulation/render separation, and practical frame rate while replacing its
Wolf-only firmware dependency with an independently built module uploaded and
controlled by the eZ80 application.

The maintained VDPlet runtime and SDK live in
`/home/smith/Agon/mystuff/agon-vdplet`. Golem owns related compiler integration
and historical evidence, but this task concerns the hand-written Wolf3D
renderer and its application protocol rather than conversion of the renderer
to the Golem language.

## Phase 1: feasibility study

The study will inspect the current standalone Wolf3D VDP extension, the
Wolf3DOrig eZ80 client, and the promoted VDPlet ABI/runtime. It must establish:

1. Which renderer code and state can move unchanged into a module and which
   parts currently depend directly on firmware-private C++ objects, global
   buffers, graphics-controller internals, callbacks, or stream-parser state.
2. Whether existing VDPlet buffer, drawing, VDU-submission, lifecycle, and
   return-channel services are sufficient; every required runtime extension
   must be described without implementing it.
3. The proposed ownership boundary among the eZ80 application, shared VDPlet
   firmware, and Wolf3D module, including upload, load, initialization, frame
   invocation, completion notification, error handling, and unloading.
4. Code, static-memory, heap, stack, asset, wire-traffic, and frame-time
   envelopes, using measurements where available and clearly labelled bounds
   where physical measurement is not yet possible.
5. Compatibility and safety risks, including stock/VDPlet firmware discovery,
   ABI versioning, module admission, stale handles, renderer failure, buffer
   lifetime, asynchronous frame completion, and clean application exit.
6. A go, no-go, or conditional-go recommendation with explicit blockers and a
   staged implementation and qualification plan.

The feasibility report will distinguish facts demonstrated by current code or
tests from inferences and proposals. It will not claim hardware performance or
compatibility without corresponding evidence.

## Required implementation map

If the recommendation is not no-go, the report will map the later work into
small ordered stages covering shared-runtime changes, module extraction,
application protocol adaptation, build and packaging, automated regression,
emulator review, physical-hardware qualification, documentation, deployment,
and rollback. These stages are planning output, not authorization to implement
them.

## Review gate

Phase 1 ends when the feasibility findings and implementation map are ready for
the Author. Work pauses at that point. No source migration, runtime extension,
new module, client protocol change, bespoke emulator change, or hardware flash
is authorized by this task until the Author explicitly releases an
implementation phase.
