"""Bind the current owner-supplied UART bootstrap; no invocation on import."""
from pathlib import Path
import hashlib
import importlib.util
import json

DONOR = Path('/Agon/mystuff/agon-extender/agents/net004/uart1-bootstrap-r01/bootstrap.py')
DONOR_SHA = 'd04f18ee229b4eca6c7134f8ba1efaa91edc5aebccc6b183b6ab4656c526ea83'
BUILD = 'net-003-r02-b2026-11-06-09-03-07Z'


def load_donor():
    assert hashlib.sha256(DONOR.read_bytes()).hexdigest() == DONOR_SHA
    spec = importlib.util.spec_from_file_location('wp004_current_uart_boot', DONOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.BUILD.decode() == BUILD
    return module


def boot_current(b, folder, label):
    assert b.kit['p4_boot_build'] == BUILD
    assert b.kit['inputs'][str(DONOR)] == DONOR_SHA
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
