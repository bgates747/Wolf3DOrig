#!/usr/bin/env python3
"""Compile and package a standalone C/C++ VDPlet for classic ESP32 hardware."""
from pathlib import Path
import argparse
import hashlib
import json
import struct
import subprocess
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
POLICY_PATH = ROOT / "src/vdplet_policy.h"
POLICY = {name: int(value) for name, value in re.findall(r"^#define VDPL_(\w+) (\d+)u$", POLICY_PATH.read_text(), re.M)}

TEXT_PROFILES = ("standard", "text96")

def text_ceiling(text_profile):
    if text_profile not in TEXT_PROFILES:
        raise ValueError(f"unknown text profile: {text_profile}")
    return POLICY['TEXT96_MAX_TEXT'] if text_profile == 'text96' else POLICY['MAX_TEXT']

def run(args, **kwargs):
    return subprocess.run([str(x) for x in args], check=True, **kwargs)

def allocation_layout(data):
    """Check allocation constraints shared with vdplet_image.h, not relocations."""
    if len(data) < 52 or data[:7] != b"\x7fELF\x01\x01\x01":
        raise ValueError("module must contain a complete little-endian ELF32 image")
    shoff = struct.unpack_from("<I", data, 32)[0]
    shsize, shcount, names_index = struct.unpack_from("<HHH", data, 46)
    if shsize != 40 or not 0 < shcount <= 32 or names_index >= shcount or shoff + shcount*40 > len(data):
        raise ValueError("invalid module ELF section table")
    names_header = struct.unpack_from("<10I", data, shoff + names_index*40)
    names_offset, names_bytes = names_header[4:6]
    if names_header[1] != 3 or names_offset + names_bytes > len(data):
        raise ValueError("invalid module ELF section-name table")
    names = data[names_offset:names_offset+names_bytes]
    expected = {".text": (1, 6), ".rodata": (1, 2), ".data": (1, 3),
                ".bss": (8, 3), ".data.rel.ro": (1, 3)}
    metadata = {".hash": 5, ".dynsym": 11, ".dynstr": 3, ".rela.dyn": 4}
    sections, admitted = {}, {}
    for index in range(shcount):
        fields = struct.unpack_from("<10I", data, shoff + index*40)
        name_at, kind, flags, address, offset, count = fields[:6]
        alignment = fields[8]
        if name_at >= len(names) or names.find(b"\0", name_at) < 0:
            raise ValueError("invalid module ELF section name")
        name = bytes(names[name_at:names.index(0, name_at)]).decode("ascii")
        if kind != 8 and offset + count > len(data):
            raise ValueError(f"{name}: section extends outside the ELF")
        sections[name] = {"virtual_address": address, "bytes": count, "type": kind}
        if not flags & 2 or not count:
            continue
        if name not in expected:
            if metadata.get(name) == kind:
                continue
            raise ValueError(f"{name}: allocated section is unsupported by the runtime")
        if (kind, flags) != expected[name]:
            raise ValueError(f"{name}: unsupported section type/flags {kind}/{flags}")
        if alignment > 4 or alignment and alignment & (alignment-1):
            raise ValueError(f"{name}: ELF alignment {alignment} is unsupported; runtime maximum is 4")
        if address & 3 or address + count > 0xFFFFFFFF:
            raise ValueError(f"{name}: virtual span must be word-aligned and fit in 32 bits")
        if name in admitted:
            raise ValueError(f"{name}: duplicate allocated section")
        for other, (start, size) in admitted.items():
            if address < start+size and start < address+count:
                raise ValueError(f"{name}: virtual span overlaps {other}")
        admitted[name] = (address, count)
    if ".text" not in admitted:
        raise ValueError("module has no admitted nonempty .text section")
    start, count = admitted[".text"]
    entry = struct.unpack_from("<I", data, 24)[0]
    if not start <= entry < start+count:
        raise ValueError("module entry is outside .text")
    return sections

def build_one(source, output, compiler, name, variant, build_id, capabilities,
              text_limit=POLICY['DEFAULT_TEXT'], data_limit=POLICY['DEFAULT_DATA'],
              stack_limit=POLICY['DEFAULT_STACK'], image_limit=POLICY['DEFAULT_IMAGE'], math=False, abi_minor=None,
              linker_script=None, psram_workaround=True, text_profile="standard"):
    maximum_text = text_ceiling(text_profile)
    if type(psram_workaround) is not bool:
        raise ValueError("psram_workaround must be True or False")
    target_flags = ["-mfix-esp32-psram-cache-issue" if psram_workaround else "-mno-fix-esp32-psram-cache-issue"]
    source, output, compiler = Path(source).resolve(), Path(output).resolve(), Path(compiler).resolve()
    output.mkdir(parents=True, exist_ok=True)
    for key, value in (("TEXT", text_limit), ("DATA", data_limit), ("STACK", stack_limit), ("IMAGE", image_limit)):
        maximum = maximum_text if key == 'TEXT' else POLICY['MAX_' + key]
        if not 0 < value <= maximum:
            raise ValueError(f"invalid {key.lower()} allowance: {value}")
    if source.suffix not in (".c", ".cpp"):
        raise ValueError("module source must be .c or .cpp")
    if not name or Path(name).name != name or name in (".", ".."):
        raise ValueError("module name must be a filename without a directory")
    if not 0 <= build_id <= 0xFFFFFFFF or not 0 <= capabilities <= 511:
        raise ValueError("invalid build ID or unsupported capability mask")
    if linker_script is not None:
        linker_script = Path(linker_script).resolve()
        if not linker_script.is_file():
            raise ValueError(f"linker script is not a file: {linker_script}")
        linker_sha256 = hashlib.sha256(linker_script.read_bytes()).hexdigest()
    if abi_minor is None:
        abi_minor = 6 if capabilities & 256 else 5 if capabilities & 128 else 4 if capabilities & 64 else 3 if capabilities & 48 else 2 if capabilities & 8 else 1 if capabilities & 4 else 0
    if abi_minor not in (0, 1, 2, 3, 4, 5, 6) or (capabilities & 4 and abi_minor < 1) or (capabilities & 8 and abi_minor < 2) or (capabilities & 48 and abi_minor < 3) or (capabilities & 64 and abi_minor < 4) or (capabilities & 128 and abi_minor < 5) or (capabilities & 256 and abi_minor < 6):
        raise ValueError("Service capabilities require ABI1.1/1.2/1.3/1.4/1.5/1.6; supported minor versions are 0/1/2/3/4/5/6")
    version = subprocess.check_output([str(compiler), "--version"], text=True).splitlines()[0]
    if "esp-2021r2-patch5" not in version or "8.4.0" not in version:
        raise ValueError(f"wrong compiler: {version}")
    obj = output / f"{name}.o"
    elf = output / f"{name}.elf"
    stripped = output / f"{name}.upload.elf"
    prefix = str(compiler).removesuffix("gcc")
    flags = ["-I", str(ROOT / "include"), "-O2", "-fPIC", "-mlongcalls", "-mtext-section-literals",
             "-fvisibility=hidden", "-ffunction-sections", "-fdata-sections",
             "-fno-builtin", "-ffp-contract=off", "-fstack-usage", "-fno-common"]
    if source.suffix == ".cpp":
        flags += ["-std=c++17", "-fno-exceptions", "-fno-rtti", "-fno-threadsafe-statics"]
    run([compiler, *target_flags, *flags, f"-DVDPL_VARIANT={variant}", "-c", source, "-o", obj])
    link_flags=[]
    if source.suffix==".cpp" or math:
        link_flags=[f"-Wl,--version-script={HERE/'module.exports'}"]
    if linker_script is not None:
        link_flags += ["-Xlinker", "-T", "-Xlinker", linker_script]
    run([compiler, *target_flags, "-nostdlib", "-nostartfiles", "-shared", "-Wl,--gc-sections",
         "-Wl,-e,vdplet_entry", "-Wl,--no-undefined", "-Xlinker", "-Map", "-Xlinker", output/f"{name}.map", *link_flags, obj,
         *(["-lm", "-lgcc"] if math else []), "-o", elf])
    run([prefix + "strip", "--strip-unneeded", "--remove-section=.got.loc",
         "--remove-section=.got", "--remove-section=.dynamic", "--remove-section=.comment",
         "--remove-section=.xt.lit", "--remove-section=.xt.prop", "--remove-section=.xtensa.info",
         "-o", stripped, elf])
    data = bytearray(stripped.read_bytes())
    # Stripping .dynamic leaves an unused PT_DYNAMIC descriptor. Null it so
    # ordinary ELF inspection has no dangling dynamic-segment warning.
    phoff = struct.unpack_from("<I", data, 28)[0]
    phsize, phcount = struct.unpack_from("<HH", data, 42)
    for index in range(phcount):
        at = phoff + index * phsize
        if struct.unpack_from("<I", data, at)[0] == 2:
            struct.pack_into("<I", data, at, 0)
    stripped.write_bytes(data)
    for suffix, command in [("readelf.txt", [prefix + "readelf", "-hSWr", stripped]),
                            ("disassembly.txt", [prefix + "objdump", "-drs", elf])]:
        with (output / f"{name}.{suffix}").open("w") as log:
            run(command, stdout=log)
    sections = allocation_layout(data)
    text_bytes = (sections[".text"]["bytes"]+3)&~3
    resident_data_bytes = sum((sections.get(name, {}).get("bytes", 0)+3)&~3
                              for name in (".rodata", ".data", ".bss", ".data.rel.ro"))
    if text_bytes > text_limit or resident_data_bytes > data_limit:
        raise ValueError(f"module exceeds declared text/data envelope: text {text_bytes}/{text_limit}, data {resident_data_bytes}/{data_limit}")
    envelope = struct.pack("<4sHHIIHHIIIIIIIIIII", b"VDPL", 1, 64, 64+len(data),
                           0x32505345, 1, abi_minor, capabilities, text_limit, data_limit, stack_limit,
                           build_id, 64, len(data), 80400, 0, 0, 0)
    assert len(envelope) == 64
    payload = envelope + bytes(data)
    if len(payload) > image_limit:
        raise ValueError(f"module image exceeds selected image limit: {len(payload)}/{image_limit}")
    if linker_script is not None and hashlib.sha256(linker_script.read_bytes()).hexdigest() != linker_sha256:
        raise ValueError("linker script changed during the build")
    package = output / f"{name}.vdpl"
    package.write_bytes(payload)
    result = {"compiler_target": {"psram_cache_workaround": psram_workaround, "flags": target_flags},
            "link_map": str(output/f"{name}.map"),
            "name": name, "source": str(source), "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "policy_sha256": hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
            "declared_limits": {"text": text_limit, "data": data_limit, "stack": stack_limit, "image": image_limit},
            "text_policy": {"profile": text_profile, "maximum": maximum_text},
            "build_id": f"0x{build_id:08x}", "capabilities": capabilities,
            "abi_major": 1, "abi_minor": abi_minor, "envelope_bytes": 64, "elf_bytes": len(data), "package_bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(), "package": str(package),
            "elf": str(elf), "entry_virtual": struct.unpack_from("<I", data, 24)[0],
            "resident_text_bytes": text_bytes, "resident_data_bytes": resident_data_bytes,
            "relative_relocations": sections.get(".rela.dyn", {}).get("bytes", 0)//12,
            "allocated_sections": {name: sections[name] for name in
                                   (".text", ".rodata", ".data", ".bss", ".data.rel.ro") if name in sections}}
    if linker_script is not None:
        result["linker_script"] = {"path": str(linker_script), "sha256": linker_sha256}
    if math:
        result["linked_libraries"] = []
        for library in ("libm.a", "libgcc.a"):
            path = Path(subprocess.check_output([str(compiler), *target_flags, "-print-file-name=" + library], text=True).strip()).resolve()
            result["linked_libraries"].append({"name": library, "path": str(path),
                                                "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="standalone .c or .cpp module")
    parser.add_argument("--compiler", type=Path,
                        default=Path.home()/".platformio/packages/toolchain-xtensa-esp32/bin/xtensa-esp32-elf-gcc")
    parser.add_argument("--output", type=Path, default=ROOT/"build/modules")
    parser.add_argument("--name", help="output basename; defaults to the source stem")
    parser.add_argument("--variant", type=int, default=1)
    parser.add_argument("--math", action="store_true", help="link pinned libm/libgcc; export only vdplet_entry")
    parser.add_argument("--text-profile", choices=TEXT_PROFILES, default="standard",
                        help="experimental text96 permits --text-limit up to98304; requires matching runtime; default allowance stays32768")
    parser.add_argument("--psram-cache-workaround", action=argparse.BooleanOptionalAction, default=True,
                        help="classic ESP32 external-RAM compiler workaround (default: enabled); --no-psram-cache-workaround is legacy reproduction only")
    parser.add_argument("--linker-script", type=Path,
                        help="explicit consumer linker script/fragment; runtime layout constraints still apply")
    parser.add_argument("--build-id", type=lambda value: int(value, 0), default=1)
    parser.add_argument("--capabilities", type=lambda value: int(value, 0), default=1,
                        help="required service bits: buffers=1, packed framebuffer=2, VDU PLOT=4, line batches=8")
    parser.add_argument("--abi-minor", type=int, choices=(0,1,2,3,4,5,6), help="defaults to6 with colour rows,5 with PCM sink,4 with audio queues,3 with pixels/PCM,2 with lines,1 with VDU, otherwise0")
    for key in ('text', 'data', 'stack', 'image'):
        parser.add_argument('--' + key + '-limit', type=int, default=POLICY['DEFAULT_' + key.upper()])
    args = parser.parse_args()
    entry = build_one(args.source, args.output, args.compiler, args.name or args.source.stem,
                      args.variant, args.build_id, args.capabilities,
                      args.text_limit, args.data_limit, args.stack_limit, args.image_limit, math=args.math, abi_minor=args.abi_minor,
                      linker_script=args.linker_script, psram_workaround=args.psram_cache_workaround, text_profile=args.text_profile)
    manifest = {
        "compiler": subprocess.check_output([str(args.compiler), "--version"], text=True).splitlines()[0],
        "abi_header_sha256": hashlib.sha256((ROOT/"include/vdplet.h").read_bytes()).hexdigest(),
        "protocol_header_sha256": hashlib.sha256((ROOT/"include/vdplet_protocol.h").read_bytes()).hexdigest(),
        "services_header_sha256": hashlib.sha256((ROOT/"include/vdplet_services.h").read_bytes()).hexdigest(),
        "pcm_sink_header_sha256": hashlib.sha256((ROOT/"include/vdplet_pcm_sink.h").read_bytes()).hexdigest(),
        "module": entry,
    }
    (args.output/f"{entry['name']}.json").write_text(json.dumps(manifest, indent=2)+"\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
