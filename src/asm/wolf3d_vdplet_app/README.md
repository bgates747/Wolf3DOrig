# Wolf3D production VDPlet application gate

This project packages the complete Wolf3DOrig application with the production
copied-pixel VDPlet backend. It is an integration/qualification target; the
tracked game selector remains `standalone` until the later acceptance gates.

Prepare the complete ten-floor SD payload locally:

```bash
.venv/bin/python src/asm/wolf3d_vdplet_app/scripts/prepare_package.py
```

Stage a stopped, hash-pinned Oryx profile without launching it:

```bash
.venv/bin/python src/asm/wolf3d_vdplet_app/scripts/stage_oryx.py
```

The resulting Oryx launcher is:

```bash
cd /home/smith/Agon/mystuff/Wolf3dOrig/.emulator/wolf3d-vdplet-app
./flexe-agon-emulator
```

Oryx execution still requires a current self-service lease under the shared
`agon-dev-env/cross-agent/vdplet-rollout` FIFO. Staging never launches an
emulator and does not itself reserve the machine.

The separately frozen FX-114 sender-observer cohort is documented in
`agonport/doc/wolf3d-vdplet-uart-observer-readiness.md`. Its staging command is:

```bash
.venv/bin/python src/asm/wolf3d_vdplet_app/scripts/stage_observer_oryx.py
```

That command also prepares only a stopped profile. It must not be run while
Oryx is unavailable, and it does not authorize or launch an emulator process.
