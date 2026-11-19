# WOLF-WEAPON-001 — Full-game cropped plot comparison on Olimex

Build the full game with cropped first-person weapon frames and compare its
ordinary 1:1 bitmap plot with the accepted renderer’s per-frame sampling.
Use the bench’s current production firmware. The test requires no firmware
exception and does not use hardware sprites.

Prepare the 20 cropped RGBA2222 images from the verified production payload.
Place them in both arms’ ordinary level sprite containers so resource loading
and resident asset memory match. The experimental module omits the normal
weapon draw for these shapes when the palette is unshifted. It selects and
plots the appropriate bitmap only after releasing the hidden color rows.
Keep the current weapon draw during damage and bonus flashes. Retain normal
game entry in a separately named interactive build.

Build two full-game timing arms with the same test entry. Each runs the first
stock E1L1 attract recording once and exits after it drains. Remove the
world-dirty render admission restriction in both timing arms. Submit the
latest pose whenever the previous frame finishes and simulation is caught up.
Repeated poses still count as presentations. Keep the 30 Hz simulation clock,
ordinary C3 page flips and existing sound paths. Use the existing PRT profiler
to record ordered flip completions. Report presentation FPS and intervals
outside recorded SD flush gaps. This measures the completed game flip path.

Check the candidate’s generated asset origins, image lengths and linked module
storage offline. Compare full-frame output with the accepted renderer through
the public VDPlet path before the bench run. Stage only the matched comparison
pair in separate test directories. Run each arm once in baseline then candidate
order. Keep the physical run bounded to the first demo and collect the profile
from each arm. Use the [bench guide](/Agon/mystuff/agon-extender/docs/operations/olimex-bench/README.md)
for scheduling, staging, execution and check-in.
