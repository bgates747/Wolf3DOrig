# Wolf audio host-ring stopped integration plan

Status: frozen before implementation on 2026-11-01. This selects preparation
only. It does not authorize an emulator process, audio-device session, GUI,
Oryx reservation, retry, behavioral repair, deployment, default, or publication.

The controlling contract is
`agon-dev-env/cross-agent/vdplet-rollout/wolf-audio-ring-consumer-v1.md`.
This project-owned integration will:

1. Create a new isolated Oryx profile named
   `wolf3d-vdplet-audio-ring-r01`. Preserve the accepted generation-64
   frontend `7e7d0e1b...`, firmware `8d980025...` and matching ELF, MOS
   `d5642432...`, application `5723cd60...`, module `12449bab...`, assets,
   autoexec behavior, and input semantics. Replace only backend `0866265b...`
   with private host-ring observer backend `0f4bdc1b...`.
2. Reuse exact helper source
   `agonport/vdplet/review/sdl_review.c` at SHA-256 `215bd248...`. Compile it
   locally on Oryx into the new profile and pin its compiler, SDL3 headers and
   libraries, `libdl`, binary, and dynamic dependencies. Do not invent a new
   input framework or guest/client marker.
3. Configure a fresh absolute `FLEXE_RING_OBSERVER_DIR` and
   `FLEXE_RING_WINDOW_AFTER_MS=90000`. The observer's actual setup-origin and
   absolute window in its finalized output remain authoritative; runner time
   zero is a separate clock.
4. Freeze a gameplay-ready framebuffer oracle from existing accepted package
   and renderer authority only. The predicate requires a complete 320x240 PPM,
   the unchanged lower-40-row HUD invariant, and a playfield distinct from the
   loader/menu. No new emulator run may manufacture the oracle.
5. Provide one finite runner which records monotonic command-write brackets,
   drives four separated Enter pairs, requires the ordered loader witnesses and
   gameplay readiness by runner T0+85 seconds, proposes one 50 ms Space pair at
   T0+92 seconds, Escape at T0+103 seconds, normal farewell/MOS return by
   T0+150 seconds, helper quit/process exit within 15 seconds, and a 180-second
   whole-session ceiling. Missing readiness or observer-window overlap is
   incomplete with no automatic retry.
6. Preserve real audio consumption. The runner may set only
   `SDL_VIDEODRIVER=dummy`; it must reject `SDL_AUDIODRIVER=dummy`, disk audio,
   or absent/unrecognized actual audio dependencies. It must not claim key
   admission, shot-sample identity, event-to-sound delay, device delivery, or
   audible latency.
7. Finalize observer output only after callbacks quiesce; validate it with the
   exact FX-124 reader, retain censored/unknown edges and existing drops, and
   label startup, functional, window, finalization, and cleanup outcomes
   independently. Cleanup is limited to the runner-owned process group.
8. Stage and verify the new profile stopped, with output paths absent and all
   source/runtime/helper/reader/environment/library pins recorded. Keep every
   existing profile intact. Return one coherent readiness record for central
   review; a later single run requires a distinct selection and normal FIFO.

The concurrently prepared physical-startup diagnostic application
`23a3968b...` is explicitly excluded from this profile and must not be copied,
rebuilt, or relabeled as the generation-64 audio cohort.
