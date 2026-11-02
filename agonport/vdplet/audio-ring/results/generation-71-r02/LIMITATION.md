# Observer initialization limitation

This note qualifies the generation-71 host-ring observation without changing
its saved records or derived result.

Subsequent Flexe source review found that private observer backend `0f4bdc1b...`
initialized shared observer state outside the mutex used by callback readers and
published the armed flag before publishing all window bounds. This creates a
startup publication race. The saved generation-71 records are internally
coherent, but they do not prove race-free initialization. They also do not show
whether the race occurred or whether it contributed to formation of the
observed backlog.

The equal 163,840 produced/dequeued real samples and the matching 5,277-sample
depth at the observer-window edges show preservation of the backlog during that
window; they do not explain how the backlog formed. Ordinary I2S0 audio uses
this same host ring upstream of SDL, but the observed approximately 325.774 ms
known-sample residence must not be presented as a pristine baseline until the
initialization issue has been bounded independently.

The authoritative supplemental record is
`agon-dev-env/cross-agent/vdplet-rollout/reviews/fx124-init-publication-limitation.json`.
Golem selected a Flexe-private, host-only preparation that initializes under the
existing lock and publishes armed last. No repeat consumer run, startup-window
experiment, audio-policy change, or behavior repair is selected.
