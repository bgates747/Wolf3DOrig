"""Bind the current owner-supplied UART bootstrap; no invocation on import."""
from pathlib import Path
import hashlib
import importlib.util
import json

DONOR = Path('/Agon/mystuff/agon-extender/agents/net004/uart1-bootstrap-r01/bootstrap.py')
DONOR_SHA = 'd04f18ee229b4eca6c7134f8ba1efaa91edc5aebccc6b183b6ab4656c526ea83'
BUILD = 'net-003-r02-b2026-11-06-09-03-07Z'
E = Path('/Agon/mystuff/agon-extender')
# Explicit dynamic-import/subprocess closure, independently identical to actual95.
# sys.modules cannot discover scripts/configs that have not been loaded yet.
REQUIRED = {
    DONOR: DONOR_SHA,
    E / 'scripts/reset_agon_usb.py': '19fd4577cdca0e1dc8000ba3a1904f21f544cc597becd96e2592671c7f72406f',
    E / 'agents/bench-reset/usb-reset.local.json': '9917c14b8ea439e5db10c747ea53017b3041afe14af582b042e040e25b8aa5ca',
    E / 'scripts/reset_agon.py': 'a34a104a8f0cc06f381b243c57f70715631ab2edb63f879b6f5da0faa5685a77',
    E / 'scripts/passive_serial.py': 'b665826da471b786582bb4dd24214f7c4bc925fe7018d07106e661fc5e4a3543',
    E / 'scripts/p4_boot_guard.py': '8c8efb4c825029adb64758b35f6424b04b952af46233cf888dab5cc2fe3e90a5',
}


def verify_closure(kit):
    """Read files only; never import or invoke the device/bootstrap helpers."""
    assert kit['p4_boot_build'] == BUILD, 'Bootstrap marker mismatch'
    for path, expected in REQUIRED.items():
        name = str(path)
        assert kit['inputs'].get(name) == expected, 'Missing/wrong bootstrap pin: ' + name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, 'Changed bootstrap file: ' + name
    return {str(p): digest for p, digest in REQUIRED.items()}


def load_donor():
    assert hashlib.sha256(DONOR.read_bytes()).hexdigest() == DONOR_SHA
    spec = importlib.util.spec_from_file_location('wp004_current_uart_boot', DONOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.BUILD.decode() == BUILD
    return module


def boot_current(b, folder, label):
    verify_closure(b.kit)
    startup = b.out / 'entry/startup.bin'
    assert hashlib.sha256(startup.read_bytes()).hexdigest() == b.components['startup_sha256']
    for line in startup.read_text().splitlines():
        assert not line.strip().upper().startswith(('RUN', 'EXEC', 'LOAD')), 'Startup must not invoke a test'
    # The sole owner has never written startup since its fresh full-file read.
    # Esptool only writes the selected native app span; this remains the latest
    # verified unchanged setup-only startup, not an invented new device read.
    with (folder / 'pre-bootstrap.json').open('x') as stream:
        json.dump(dict(label=label, startup_sha256=b.components['startup_sha256'],
                       verified_by=str(startup), unchanged_since_entry=True,
                       boot_source_sha256=DONOR_SHA, p4_build=BUILD), stream, indent=2)
        stream.write('\n')
    load_donor().clean_bootstrap(b, folder)
