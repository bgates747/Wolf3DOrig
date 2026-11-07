# Hardware controller qualification build

Serial Pi compiler only, ordinary bounded qualification. Existing ownership,
finite-case dispatch/cleanup reserve, entry/namespace, failure-stop and supported
listener replacement lifecycle tests exercise the actual adapted controller.
Per-arm producer verification is retained from the completed first build; this
tranche does not reassemble, rebuild or replay previous tests without a reason.
New controller and source-context wiring justify these focused checks.

At most180s total,80C/512MiB guards and owned-child cleanup. No device access,
emulator, service restart or firmware build. Source-only Extender interpreter/
import preflight precedes all physical admission. Final kit pins bind these
receipts and exact host dependencies; current grant and handoff remain separate.
