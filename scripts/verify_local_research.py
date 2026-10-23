#!/usr/bin/env python3
"""One offline verification batch. No installation, network, corpus writes or authority changes."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import uuid

from research_integrity import write_private

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ["generate_workbench_pseudolocale.py", "run_rhf_suite.py",
           "run_synthetic_verification.py", "verify_workbench_slice1.py",
           "verify_workbench_slice2_adapter.py", "verify_workbench_slice2_producer.py",
           "verify_workbench_document_authority.py", "verify_workbench_slice3_events.py",
           "verify_workbench_slice4_evidence.py", "verify_workbench_slice5_firewall.py",
           "verify_workbench_research_workspaces.py", "verify_d0025_governance_reconciliation.py"]


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def code_state():
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).split(b"\0")
    h = hashlib.sha256()
    for name in sorted(n for n in tracked if n):
        p = ROOT / os.fsdecode(name)
        h.update(name + b"\0")
        h.update(p.read_bytes() if p.is_file() else b"MISSING")
    return {"head": git("rev-parse", "HEAD"), "branch": git("branch", "--show-current"),
            "status": git("status", "--porcelain"), "tracked_content_sha256": h.hexdigest()}


def execute(command, env, log, timeout, cwd=ROOT):
    with log.open("x") as output:
        child = subprocess.Popen(command, cwd=cwd, env=env, stdout=output,
                                 stderr=subprocess.STDOUT, start_new_session=True)
        try:
            return {"exit_code": child.wait(timeout=timeout), "timeout": False}
        except (subprocess.TimeoutExpired, KeyboardInterrupt) as error:
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
            return {"exit_code": child.returncode, "timeout": isinstance(error, subprocess.TimeoutExpired),
                    "interrupted": isinstance(error, KeyboardInterrupt)}


def check_passed(result):
    # Termination handlers may exit zero even when a check did not finish.
    return (result.get("exit_code") == 0 and not result.get("timeout")
            and not result.get("interrupted") and not result.get("error"))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--node", type=Path, help="Existing Node 22+ binary; no installation")
    parser.add_argument("--timeout", type=int, default=600, help="Per-check seconds")
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("timeout must be positive")
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = args.out_dir or ROOT / "build" / ("local-verification-" + stamp + "-" + uuid.uuid4().hex[:8])
    out = out.resolve()
    out.mkdir(mode=0o700, parents=True, exist_ok=False)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    env["PYTHONUNBUFFERED"] = "1"
    # Child diagnostics cannot accidentally inherit project bearer credentials.
    for key in list(env):
        if key.upper().startswith("ARS_") or any(s in key.upper() for s in (
                "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL", "API_KEY",
                "ACCESS_KEY", "PRIVATE_KEY", "AUTHORIZATION")):
            env.pop(key)
    node = args.node.resolve() if args.node else shutil.which("node")
    if node:
        env["PATH"] = str(Path(node).parent) + os.pathsep + env.get("PATH", "")
    receipt = {"contract": "ARS-OFFLINE-VERIFICATION-v1", "status": "RUNNING", "started_utc": stamp,
               "scientific_effect": "NONE", "live_drive_verification": "NOT_PERFORMED",
               "python": sys.version, "start": code_state(), "checks": []}
    env["GITHUB_SHA"] = receipt["start"]["head"] if not receipt["start"]["status"] else "LOCAL_UNCOMMITTED"
    write_private(out / "started.json", receipt)
    # Legacy verifiers use relative build/ outputs. Give them a fresh sandbox,
    # with only the required contract inputs, preserving previous receipts.
    sandbox = out / "sandbox"
    sandbox.mkdir()
    shutil.copytree(ROOT / "contracts", sandbox / "contracts")
    preflight = sys.version_info[:2] == (3, 13) and bool(node)
    commands = [[sys.executable, "-m", "pip", "check"]]
    if node:
        commands.append([str(node), "-e", "if(Number(process.versions.node.split('.')[0])<22)process.exit(2);console.log(process.version)"])
    if preflight:
        commands.append([sys.executable, "-m", "pytest", "-q"])
        for script in SCRIPTS:
            cmd = [sys.executable, str(ROOT / "scripts" / script)]
            if script == "generate_workbench_pseudolocale.py":
                cmd += ["--check"]
            elif script == "run_rhf_suite.py":
                cmd += ["--out", str(out / "rhf.json")]
            elif script == "run_synthetic_verification.py":
                cmd += ["--out-dir", str(out / "synthetic")]
            commands.append(cmd)
    for i, command in enumerate(commands):
        label = command[2] if command[1] == "-m" else Path(command[1]).name
        log = out / f"{i:02d}-{label}.log"
        try:
            result = execute(command, env, log, args.timeout,
                             cwd=sandbox if command[1].endswith(".py") else ROOT)
        except OSError as error:
            result = {"exit_code": None, "error": type(error).__name__}
        receipt["checks"].append({"command": command, "log": log.name, **result})
        print(f"{label}: {'PASS' if check_passed(result) else 'HELD'}", flush=True)
        write_private(out / f"check-{i:02d}.json", receipt["checks"][-1])
        if not check_passed(result):
            break
    receipt["finish"] = code_state()
    receipt["code_unchanged"] = receipt["start"] == receipt["finish"]
    receipt["status"] = "PASS" if preflight and len(receipt["checks"]) == len(commands) and all(check_passed(c) for c in receipt["checks"]) and receipt["code_unchanged"] else "HELD"
    receipt["finished_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
    receipt["limits"] = "Offline executable checks only. No source admission, media observation, rights grant, live pin refresh or deployment. started.json without receipt.json means interrupted, never PASS."
    write_private(out / "receipt.json", receipt)
    print(str(out / "receipt.json"))
    return 0 if receipt["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
