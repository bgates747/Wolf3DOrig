# s01: bounded observation of intermittent setup stalls

q01 and q02 both stopped on a300-second pre-render timeout, at different
upload boundaries. Keep those failures and their literal frozen harnesses.
The unchanged bespoke CPU binary passed q01 and stalled q02. No rendering
comparison or UART repair follows from those observations.

Prepare fresh stopped profiles by verifying/copying the complete inputs from
these two owned stopped profiles, in this exact order:

|Order|Source|Purpose|
|---|---|---|
|1|q02/02-bespoke-cpu, r05 guest|Observe the most recent SFX upload stall|
|2|q01/06-vdplet-paced, r04 guest|Observe the original zero-log upload boundary|

At most two sequential headless JIT invocations. No screenshots/audio/GUI.
Each has a300-second outer bound including ordinary setup; an observer's
complete three-sample stasis window ends the diagnostic early. Normal guest
completion also ends a case. Stop the tranche at the first observed stall or
unexpected failure; only a normally completed first case permits the second.
No rescue bytes, replay, transfer chunking/pacing change, firmware correction,
guest change, interpreter substitution or additional cases are included.

Enable only FLEXE_TX_OBSERVER_OUTPUT at a fresh absolute private output path.
Retain fixed50s no-completed-send trigger,100ms poll,0/250/500ms samples,
630s observer lifetime,<=5lines/20KiB and existing one reader thread/no new
observer process. The shorter outer bound may produce interrupted/null/late
evidence; preserve that as unavailable/incomplete. Validate the final JSONL
with the exact versioned reader after normal Quit/join. A complete window
locates published producer/TX/CTS state, not guest intent, parser state or a
hardware cause. A no-stall pass provides no live stall diagnosis. Observer
execution may perturb timing; discard all such timings for speed comparison.

For all Olimex bench procedures, use the sole authoritative [bench guide](/Agon/mystuff/agon-extender/docs/operations/olimex-bench/README.md).
