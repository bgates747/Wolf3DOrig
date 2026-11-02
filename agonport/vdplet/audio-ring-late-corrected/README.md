# Corrected late host-ring preparation

This directory contains a Pi-only, device-free selection for a possible future
corrected SETUP+90..100-second host-ring observation. It combines the accepted
corrected backend pin from the startup preparation with the exact accepted
original late-window runner and oracle. No target profile has been staged and
no emulator, audio device, Oryx session, build, reservation, hardware action,
or publication occurred.

The immutable scope and differences are in [PLAN.md](PLAN.md). The selected
pins and one-invocation proposal are in [preparation.json](preparation.json).
Run `verify_preparation.py` and the device-free test suite locally; do not stage
or execute a target without a later explicit central selection.
