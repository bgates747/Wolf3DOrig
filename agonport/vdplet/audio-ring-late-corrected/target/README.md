# Custody-only target staging

These scripts may be used only after this task is first in the shared FIFO,
Oryx is freshly idle, and `wolf3dorig` holds a live checkout. `stage_oryx.py`
requires the lease token and asserts ownership before its first target contact.

The stager performs no build. It clones the accepted old late profile, replaces
only its backend with the already accepted corrected binary, rewrites only the
private observer output path, retains the 90000 ms offset, verifies that the
launcher and backend are the only changed runtime members, checks every retained
dependency pin, and freezes `staging.json`. It never launches the emulator.

Do not run the stager while another owner holds Oryx or before a separately
selected run. Any drift or existing target profile is terminal and must be
reported rather than repinned or repaired in place.
