#!/usr/bin/env python3
"""Deploy this project's declared Agon software bundles."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "tools"))
from wolf_firmware import DEFAULT_PAYLOAD, verify_payload
ENGINE_ROOT = Path.home() / "Agon/mystuff/agon-dev-env/scripts"
if not (ENGINE_ROOT / "agon_deploy.py").is_file():
    raise SystemExit(
        "Canonical deployment engine is missing: "
        f"{ENGINE_ROOT / 'agon_deploy.py'}"
    )
sys.path.insert(0, str(ENGINE_ROOT))
from agon_deploy import DeploymentError, main  # noqa: E402

try:
    if len(sys.argv) > 1 and sys.argv[1] in ("plan", "deploy") and not any(a in ("-h", "--help") for a in sys.argv):
        verify_payload(DEFAULT_PAYLOAD)
    raise SystemExit(main(project_root=PROJECT_ROOT))
except (DeploymentError, ValueError, FileNotFoundError, KeyError) as error:
    print(f"deployment refused: {error}", file=sys.stderr)
    raise SystemExit(2)
