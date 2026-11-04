# Wolf3D shell/demo parity regression r20

## Purpose

Qualify the current source corrections which restore the original shareware
`DemoLoop` ownership boundaries:

- `INTROSONG` continues across title, credits, and the attract high-score page;
- natural recorded-demo exhaustion restarts that attract cycle;
- local recorded-demo input enters the control panel directly; and
- victory/game-over high-score completion returns to the attract cycle rather
  than opening the main menu immediately.

## Frozen finite run

Stage the exact current Wolf3DOrig worktree into an isolated Oryx directory and
verify the modified production includes and both regression fixtures by hash.
Then run, sequentially and headlessly:

1. `src/asm/wolf3d_demo/scripts/run_demo_emulator_regression.py`;
2. `src/asm/wolf3d_shell/scripts/run_shell_emulator_regression.py`.

Use the Oryx-native project interpreter, assembler, MOS, and emulator runtime.
Do not copy a Pi virtual environment. Each subprocess has a 180-second bound;
stop on the first unexpected result. The complete tranche has a ten-minute hard
limit and owns at most one emulator process at a time.

## Exclusions and cleanup

This run authorizes no GUI, human review, hardware/SD access, firmware change,
deployment, publication, or unrelated regression. Preserve exact stdout,
target receipts, runtime identities, and hashes. Stop all owned children,
remove only the explicit temporary staging directory, obtain fresh Oryx idle
evidence, release the lease, and immediately steer the returned next owner.

## Execution record

Oryx r20 stopped before assembly or emulator launch because its default
project-local `agonport/emulator/fab-agon-emulator` dependency did not exist on
the Linux Lite checkout. No semantic result was claimed from that preparation
fault.

R21 repeated this unchanged finite test after pinning the previously qualified
direct-regression runtime explicitly:

- emulator SHA-256
  `aec5f8c266117d5bf864c6124d3c8986d042802ed5cbaaf8813e04a9fb8d0bea`;
- MOS SHA-256
  `5fbacb749ee037f0428aeac39817b5a6d465adc020f92d4020bb7dcb046d39fe`;
- stock VDP SHA-256
  `14338aaeead48cb3df5987bf7fcc1b350d9e08d4a0ee0fcfc1a4a89cf79fae97`.

The recorded-demo fixture passed 51/51 checks. The production-shell fixture
passed 764/764 checks; its 18,861-byte binary has SHA-256
`c98c0faad7a66141c50ee68ac4f96b89dae4ec41ef39441f87f27cbd99ec34a3`.
Exact logs and input receipts are retained under
`agonport/emulator/evidence/shell-demo-parity-r21/`. Generation 248 was
released with fresh whole-host idle evidence and no waiting successor.
