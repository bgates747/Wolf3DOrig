# Preserve visual preparation failure

The first Fab derivative assembly failed before emulator launch: its manually
trimmed bench.inc lacked wp_create_log. The actual control donor already
contains both the page-hold helper and log helper; no appended/truncated helper
body is needed. visual01/assembly.log and compiler307 release preserve this.

New prepare_visual.py/visual02 copies the complete unchanged real control bench
body, retains qualified Arthur loading bindings, applies the same caption
transformation and activates the existing two-page proof flag. Same finite
Oryx reservation/profile and one emulator case; no prior emulator/target replay.
