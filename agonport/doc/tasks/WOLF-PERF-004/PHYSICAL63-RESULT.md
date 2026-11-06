# Removing the redundant clear cuts draw time by25.14%

The corrected candidate reduced mean VDP draw time from91.5588ms to68.5399ms,
saving23.0188ms per completed pose in this fixture. Unpaced completed throughput
rose from10.5230 to13.8823FPS (+31.92%). This is a measured improvement from one
fill-extent correction, not default adoption or an ordinary gameplay FPS claim.

| Frozen module | Draw ms | Module scope ms | Complete-command ms | Completed fixture FPS |
| --- | ---: | ---: | ---: | ---: |
| Original1907 |91.5588|92.0259|92.1401|10.5230|
| Candidate54568e45 |68.5399|69.0108|69.1343|13.8823|

All native milliseconds use the unchanged configured240MHz conversion. Draw
starts inside the native dispatch after the full command has arrived; scope
and command are the already-qualified surrounding local brackets. They include
preemption/service waits, not exclusive processor work. FPS uses the guest's
unchanged nominal1kHz PRT and counts every completed pose. The independent MOS
counter gives10.5033/13.8568FPS respectively. No external clock calibration,
optical scanout/display-latency measurement or ordinary interactive game trial
was performed. Asset loads, module selection, resource probes and file transfers
are outside the measured intervals.

## Matched evidence

Actual63 ran the frozen833eefe hardware03 kit with167 verified input pins,
unchanged native7593, guest/asset/clock/observer/compiler policies and mainboard
UART carrier. Matrix: original-control, candidate-control, original-unpaced,
candidate-unpaced, candidate-unpaced, original-unpaced. Four600-pose runs give
1200measured samples per arm. All run angles/indexes/order/lengths/counter bounds,
returns, registers/timer state and stack pointers passed the retained checks.

| Measured case | Module | Draw ms | Completed fixture FPS |
| --- | --- | ---: | ---: |
|03|Original|91.6190|10.5184|
|04|Candidate|68.7157|13.8498|
|05|Candidate|68.3641|13.9150|
|06|Original|91.4986|10.5276|

Corresponding original-minus-candidate draw savings are22.9032ms and23.1344ms.
The second pair reverses execution order. These are repeated deterministic,
correlated samples; no independence/confidence-interval claim is made. RawPRID
is0xCDCD throughout, interpreted under the existing pinned SDK as PRO/core0.
Script is unchanged E1L1 tile34,36 center34.5,36.5,720degrees/600poses,
300distinct integer-degree headings, no enemies, fixed HUD/weapon and two
unmeasured warmups. This unpaced capacity fixture completes its poses without
skipping; it is not a20second paced run.

All six guests pass470asset loads/952setup fences, zero timeouts/errors, normal
return and rawmode0/callback0 checks. All seven INFO probes pass with zero live
module slots/leases and whole-command minimum stack1908B versus512B refusal
threshold. Memory counters are cumulative/non-atomic halves, not peak per-call
attribution. All six physical module selections verify previous target, selected
target and retained backup, then complete explicit supported RECOVER3/state1.
No guard, SDK, firmware or journal policy was weakened.

The renderer control remains exact1907; candidate54568e45 changes only the
initial fill extent in the isolated generated code. The separately corrected
common scaling source still yields identical original target bytes. Host output,
geometry, page guards, sync-bit and lifecycle checks retain their precise R03/
M1 coverage limits; these are not a new physical framebuffer pixel capture.
The measured saving supports the selected redundant-write removal. It does not
attribute the remaining gap to dispatch, wider stores, helpers or another
unmeasured mechanism.

## Restoration, history and next boundary

Exact incoming profile8 native application/touched-tail1105920B span85f9 was
restored and independently read back. P4d9bcb/EMOSa25f/startuped403/listener0566
were preserved. Selected bootstrap, rawmode0/callback0/Legacy0/fullfile/rootCLI/
cursor command/inputneutral/offlineidle/freeUSB checks passed; all owned actors
joined. Actual63 released2026-11-06T22:44:20.019912UTC and Extender, the actual
next owner, was notified before quantitative analysis. SD stayed mounted.

Physical61 remains an honestly stopped cohort, with its original module/backup
and failure journals preserved. Its omission was a consumer repeated-replacement
lifecycle bug. The previous packet already warned that backup blocks the next
upload; reviewers missed the consequence. Later availability of detailed source
was not the sole explanation. The fixed composition tests exercise actual
consumer selection against the retained real listener engine; HTTP/UART/FAT/
power failure and lost-response uncertainty remain separate. A lost RECOVER3
reply could follow successful deletion: stop and retain available evidence and
custody, rather than promising both files still exist or retrying speculatively.

PHYSICAL63-RESULT.json retains aggregate/raw identities and per-case/probe/module
receipts. Full raw outputs, binary hash ledger, original staged transaction
journals and release proof remain under ignored build/hardware03. No production
source/default was changed. Any next span candidate requires its own task,
pre-code support/work review, exact control reproduction, host/code/resource
qualification and separately frozen fresh physical comparison.
