#!/usr/bin/env python3
"""Repo validation gate (root AGENTS.md law). Run from the repo root before every commit:

    python3 lab/scripts/validate_repo.py

Exit 0 = green (safe to commit). Non-zero = fix before pushing. Checks are integrity-focused and
fast; they enforce the anti-bloat laws, they don't measure quality.
"""

from __future__ import annotations

import json
import py_compile
import re
import sys
from pathlib import Path

FAILS: list[str] = []
WARNS: list[str] = []


def fail(msg: str) -> None:
    FAILS.append(msg)
    print(f"  FAIL  {msg}")


def ok(msg: str) -> None:
    print(f"  ok    {msg}")


def warn(msg: str) -> None:
    WARNS.append(msg)
    print(f"  warn  {msg}")



# Test cadence (owner SD-20): the full gate runs before each push, so it is built to be fast
# without checking less.
# - Owner test suites start together and the application suite is split into balanced shards.
# - Suites that take the exclusive authority lock on the real checkout run alone, after every
#   parallel suite has finished. A parallel suite that fails is run again alone and that result
#   counts, so lock contention between suites can never turn the gate red or hide a real failure.
# - Every child process gets a closed stdin and a timeout, so nothing can hang the gate.
# - The scale benchmark is reused while everything it reads is byte-identical to its last passing
#   run in this checkout; CPCS_GATE_FULL=1 forces it to run.
import hashlib
import os
import platform
import subprocess as _subprocess
import tempfile
import time

SUITE_TIMEOUT_S = 1800
APPLICATION_SHARDS = 4
PARALLEL_SUITES = ("second_brain", "compiler", "runtime", "verification")
SERIAL_SUITES = ("release",)
SERIAL_APPLICATION_MODULES = ("test_facade",)
# Measured seconds per application module (2026-10-04, after the read caches); unknown modules count 3 s.
APPLICATION_WEIGHTS = {
    "test_directing_pipeline": 84, "test_product_mcp_golden": 65, "test_closed_directing": 63,
    "test_action_coverage": 56, "test_bootstrap_surface": 54, "test_kinematic_directing": 31,
    "test_universal_acceptance": 17, "test_directing_invariants": 14, "test_render_evidence_workflow": 10,
    "test_video_comparison_workflow": 9, "test_directing_surface": 9,
}
SCALE_INPUTS = ("lab/concepts.jsonl", "lab/second_brain/scale_benchmark.yaml",
                "lab/second_brain/analysis_profiles.yaml", "lab/second_brain/src", "lab/second_brain/schemas",
                "lab/second_brain/templates", "lab/second_brain/curated", "lab/second_brain/immutable")
SECTIONS: list[tuple[str, float]] = []


def _section(title: str) -> None:
    SECTIONS.append((title, time.monotonic()))
    print(title, flush=True)


def _run(args, **kwargs):
    kwargs.setdefault("stdin", _subprocess.DEVNULL)
    return _subprocess.run(args, **kwargs)


class _Suites:
    """Owner test suites: parallel where they can share the checkout, alone where they cannot."""

    def __init__(self, root: Path) -> None:
        self.root = root
        modules = sorted(path.stem for path in (root / "lab/application/tests").glob("test_*.py"))
        shards, loads = [[] for _ in range(APPLICATION_SHARDS)], [0] * APPLICATION_SHARDS
        for module in sorted(modules, key=lambda m: (-APPLICATION_WEIGHTS.get(m, 3), m)):
            if module in SERIAL_APPLICATION_MODULES:
                continue
            index = loads.index(min(loads))
            shards[index].append("lab.application.tests." + module)
            loads[index] += APPLICATION_WEIGHTS.get(module, 3)
        unit = [sys.executable, "-m", "unittest"]
        self.parallel = {name: [[*unit, "discover", "-s", f"lab/{name}/tests", "-v"]] for name in PARALLEL_SUITES}
        self.parallel["application"] = [[*unit, "-v", *shard] for shard in shards if shard]
        self.serial = {name: [[*unit, "discover", "-s", f"lab/{name}/tests", "-v"]] for name in SERIAL_SUITES}
        alone = ["lab.application.tests." + m for m in SERIAL_APPLICATION_MODULES if m in modules]
        if alone:
            self.serial["application"] = [[*unit, "-v", *alone]]
        self.running = {name: [(args, *self._launch(args)) for args in commands]
                        for name, commands in self.parallel.items()}
        self.finished: dict[str, list] = {}

    def _launch(self, args):
        out, err = tempfile.TemporaryFile("w+"), tempfile.TemporaryFile("w+")
        return _subprocess.Popen(args, cwd=self.root, stdin=_subprocess.DEVNULL, stdout=out, stderr=err, text=True), out, err

    def _wait(self, name, args, process, out, err):
        note = ""
        try:
            process.wait(timeout=SUITE_TIMEOUT_S)
        except _subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            note = f"\n{name} suite exceeded {SUITE_TIMEOUT_S} s and was stopped\n"
        texts = []
        for handle in (out, err):
            handle.seek(0)
            texts.append(handle.read())
            handle.close()
        return args, (1 if note else process.returncode), texts[0], texts[1] + note

    def _collect(self, name) -> None:
        if name in self.running:
            self.finished[name] = [self._wait(name, *entry) for entry in self.running.pop(name)]

    def _alone(self, name, args):
        for other in list(self.running):
            self._collect(other)
        return self._wait(name, args, *self._launch(args))

    def result(self, name: str):
        self._collect(name)
        rows, rerun = [], 0
        for args, code, out, err in self.finished.pop(name, []):
            if code != 0:
                rerun += 1
                args, code, out, err = self._alone(name, args)
            rows.append((code, out, err))
        for args in self.serial.get(name, []):
            rows.append(self._alone(name, args)[1:])
        ran, slowest = 0, 0.0
        for _, _, err in rows:
            match = re.search(r"^Ran (\d+) tests? in ([\d.]+)s", err, re.M)
            if match:
                ran += int(match.group(1))
                slowest = max(slowest, float(match.group(2)))
        summary = f"\nRan {ran} tests in {slowest:.3f}s ({len(rows)} process(es)"
        summary += f"; {rerun} re-run alone after failing beside other suites)\n" if rerun else ")\n"
        return _subprocess.CompletedProcess(name, max((code for code, _, _ in rows), default=1),
                                            "".join(out for _, out, _ in rows), "".join(err for _, _, err in rows) + summary)


def _scale_inputs_hash(root: Path) -> str:
    digest = hashlib.sha256((platform.python_version() + platform.platform()).encode())
    for relative in SCALE_INPUTS:
        target = root / relative
        for path in ([target] if target.is_file() else sorted(target.rglob("*"))):
            if path.is_file() and "__pycache__" not in path.parts:
                digest.update(str(path.relative_to(root)).encode() + b"\0" + path.read_bytes() + b"\0")
    return "sha256:" + digest.hexdigest()


def _scale_benchmark(root: Path):
    """Run the scale benchmark, or reuse its last passing report when nothing it reads has changed."""
    record = root / "work" / "scale" / "last_pass.json"
    inputs = _scale_inputs_hash(root)
    if not os.environ.get("CPCS_GATE_FULL") and record.exists():
        try:
            saved = json.loads(record.read_text())
        except (OSError, json.JSONDecodeError):
            saved = {}
        if saved.get("inputs") == inputs and isinstance(saved.get("report"), dict):
            return _subprocess.CompletedProcess("scale", 0, json.dumps(saved["report"]), ""), True
    r = _run([sys.executable, "-m", "lab.second_brain.src.scale_eval"], capture_output=True, text=True, cwd=root)
    if r.returncode == 0 and _scale_inputs_hash(root) == inputs:
        try:
            record.parent.mkdir(parents=True, exist_ok=True)
            record.write_text(json.dumps({"inputs": inputs, "report": json.loads(r.stdout)}))
        except (OSError, json.JSONDecodeError):
            pass
    return r, False


def find_root() -> Path:
    here = Path.cwd()
    for cand in [here, *here.parents]:
        if (cand / "lab" / "registry.yaml").exists():
            return cand
    sys.exit("error: run from inside the repo (lab/registry.yaml not found)")


def main() -> None:
    root = find_root()
    lab = root / "lab"
    try:
        import yaml
    except ImportError:
        sys.exit("error: PyYAML required (python3 -m pip install pyyaml)")

    # 1. YAML sources parse
    _section("[1] YAML parses")
    docs = {}
    yaml_sources = sorted((lab / "experiments").glob("*.yaml"))
    yaml_sources += sorted((lab / "profiles").rglob("*.yaml"))
    for rel in [
        "lab/registry.yaml",
        "lab/blocks.yaml",
        *[str(p.relative_to(root)) for p in yaml_sources],
    ]:
        p = root / rel
        try:
            docs[rel] = yaml.safe_load(p.read_text())
            ok(rel)
        except Exception as e:  # noqa: BLE001 — report any parse failure
            fail(f"{rel}: {e}")
    reg = docs.get("lab/registry.yaml") or {}
    blocks = docs.get("lab/blocks.yaml") or {}

    # 2. results.csv integrity
    _section("[2] runs ledger")
    import csv
    vids = {v["id"] for v in reg.get("variants", [])}
    run_ids, exp_ids = set(), {e["id"] for e in reg.get("experiments", [])}
    csv_path = lab / "runs" / "results.csv"
    try:
        rows = list(csv.DictReader(csv_path.open()))
        for row in rows:
            run_ids.add(row["run_id"])
            if row["variant_id"] not in vids:
                fail(f"results.csv {row['run_id']}: unknown variant {row['variant_id']}")
            for dim in ("realism", "skin", "motion", "adherence"):
                val = (row.get(dim) or "").strip()
                if val and not (val.isdigit() and 1 <= int(val) <= 5):
                    fail(f"results.csv {row['run_id']}: {dim}={val!r} not 1-5/blank")
        if len({r["run_id"] for r in rows}) != len(rows):
            fail("results.csv: duplicate run_id")
        ok(f"{len(rows)} runs, all variant refs resolve")
    except FileNotFoundError:
        fail("lab/runs/results.csv missing")

    # 3. pattern + block evidence ids resolve
    _section("[3] evidence ids")
    known = vids | run_ids | exp_ids | {p["id"] for p in reg.get("patterns", [])}
    short = {i.split("_")[0] for i in known} | known  # allow short forms like e002, r001, p001
    bad = 0
    for coll, items in [("pattern", reg.get("patterns", [])), ("block", blocks.get("blocks", []))]:
        for it in items:
            for ev in it.get("evidence", []) or []:
                if ev not in known and ev not in short and not any(k.startswith(ev) for k in known):
                    bad += 1
                    fail(f"{coll} {it['id']}: evidence id '{ev}' resolves to nothing")
    if not bad:
        ok("all pattern/block evidence ids resolve")

    # 4. variants: registry <-> disk, both directions
    _section("[4] variants on disk")
    disk = {p.name for p in (lab / "variants").iterdir() if p.is_file()}
    for v in reg.get("variants", []):
        for key in ("prompt_file", "authoring_artifact"):
            if key in v and not (lab / v[key]).exists():
                fail(f"registry {v['id']}: {key} {v[key]} missing on disk")
    referenced = {Path(v[k]).name for v in reg.get("variants", []) for k in ("prompt_file", "authoring_artifact") if k in v}
    for orphan in sorted(disk - referenced):
        warn(f"lab/variants/{orphan} not referenced by any registry variant")
    ok(f"{len(referenced)} referenced files present")

    # 5. registry pointers exist (runbooks, scripts, docs)
    _section("[5] registry pointers")
    for section in ("runbooks", "scripts"):
        for name, rel in (reg.get(section) or {}).items():
            (ok if (lab / rel).exists() else fail)(f"{section}.{name} -> lab/{rel}" if (lab / rel).exists()
                                                   else f"{section}.{name}: lab/{rel} missing")
    for key in (
        "control_surface",
        "block_library",
        "concept_index",
        "format_control_map",
        "universal_motion_skeleton",
        "second_brain_requirements",
        "runtime_requirements",
        "verification",
        "application",
        "release",
        "repo_control",
        "repository_map",
        "repo_control_skill",
        "intent_profile_policy",
        "compiler",
        "control_translations",
        "provider_capabilities_dir",
        "universal_profile",
        "domain_profiles_dir",
    ):
        if reg.get(key) and not (lab / reg[key]).exists():
            fail(f"registry.{key}: lab/{reg[key]} missing")

    # 6. lab scripts compile
    _section("[6] scripts compile")
    scripts = list((lab / "scripts").glob("*.py"))
    scripts += list((lab / "second_brain" / "src").glob("*.py"))
    scripts += list((lab / "compiler").glob("*.py"))
    scripts += list((lab / "runtime").rglob("*.py"))
    scripts += list((lab / "verification").rglob("*.py"))
    scripts += list((lab / "application").rglob("*.py"))
    scripts += list((lab / "release").rglob("*.py"))
    scripts += list((lab / "repo_control").rglob("*.py"))
    for script in sorted(scripts):
        try:
            py_compile.compile(str(script), doraise=True)
            ok(script.name)
        except py_compile.PyCompileError as e:
            fail(f"{script.name}: {e.msg}")

    # 7. runbook embedded records validate against the package schema (when jsonschema available)
    _section("[7] runbook examples vs package schema")
    schema_path = root / "research/CPCS_FACS_Laban_AI_Video_Research_Package_v1.2/schemas/CPCS_Video_Observation_Record_Schema.json"
    try:
        import jsonschema
        schema = json.loads(schema_path.read_text())
        n = 0
        for rb in sorted(lab.glob("RUNBOOK_*.md")):
            for m in re.finditer(r"```json\n(.*?)```", rb.read_text(), re.S):
                try:
                    rec = json.loads(m.group(1))
                except json.JSONDecodeError:
                    continue  # non-record JSON snippets are allowed
                if isinstance(rec, dict) and "record_id" in rec:
                    n += 1
                    try:
                        jsonschema.validate(rec, schema)
                    except jsonschema.ValidationError as e:
                        fail(f"{rb.name}: record {rec.get('record_id')} schema-invalid: {e.message}")
        ok(f"{n} embedded record example(s) checked")
    except ImportError:
        warn("jsonschema not installed — skipped record-example validation")
    except FileNotFoundError:
        warn("package schema not found — skipped record-example validation")

    # 8. char budgets: assets that claim < 2000 chars
    _section("[8] char budgets")
    for asset in sorted((root / "assets").glob("*")):
        text = asset.read_text(errors="ignore")
        if "2000" in text or "2,000" in text:
            n = len(text)
            # templates include comments; budget applies to the paste payload — warn only past 2400
            (warn if n > 2400 else ok)(f"{asset.name}: {n} chars" + (" — over template allowance" if n > 2400 else ""))

    # 9. concept corpus integrity (delegates to concepts.py validate)
    _section("[9] concept corpus")
    import subprocess
    r = _run([sys.executable, str(lab / "scripts" / "concepts.py"), "validate"],
                       capture_output=True, text=True, cwd=root)
    if r.returncode == 0:
        ok(r.stdout.strip().splitlines()[-1])
    else:
        fail(f"concepts.jsonl: {r.stdout.strip() or r.stderr.strip()}")

    # 10. control plane: E2E sync (graph freshness, research coverage, removals, routing)
    _section("[10] control plane sync")
    r = _run([sys.executable, str(lab / "scripts" / "sync_repo.py")],
                       capture_output=True, text=True, cwd=root)
    if r.returncode == 0:
        ok(r.stdout.strip().splitlines()[-1])
    else:
        fail("sync_repo drift — run: python3 lab/scripts/sync_repo.py (see REQUIRED ACTIONS)")
        for line in r.stdout.strip().splitlines():
            if "FAIL" in line or line.strip().startswith(tuple("123456789")):
                print("        " + line.strip())
    r = _run(
        [sys.executable, "-m", "unittest", "discover", "-s", "lab/repo_control/tests"],
        capture_output=True,
        text=True,
        cwd=root,
    )
    if r.returncode == 0:
        result_line = next(
            (line.strip() for line in r.stderr.splitlines() if line.startswith("Ran ")),
            "repository-control tests passed",
        )
        ok(result_line)
    else:
        fail(f"repository-control tests: {r.stderr.strip() or r.stdout.strip()}")

    # 11. second-brain schemas, stores, and deterministic rebuild
    _section("[11] second-brain control plane")
    r = _run(
        [sys.executable, "-m", "lab.second_brain.src.validate", "control-plane"],
        capture_output=True,
        text=True,
        cwd=root,
    )
    if r.returncode == 0:
        ok(r.stdout.strip().splitlines()[0])
    else:
        fail(f"second-brain validation: {r.stderr.strip() or r.stdout.strip()}")
    r = _run(
        [sys.executable, "-m", "lab.second_brain.src.retrieval_eval"],
        capture_output=True,
        text=True,
        cwd=root,
    )
    if r.returncode == 0:
        try:
            benchmark = json.loads(r.stdout)
            summary = benchmark["summary"]
            ok(
                "retrieval benchmark "
                f"{summary['cases_passed']}/{summary['cases']} cases, "
                f"required_recall={summary['required_recall']:.3f}, "
                f"forbidden_clean_rate={summary['forbidden_clean_rate']:.3f}"
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            fail(f"retrieval benchmark emitted an invalid report: {error}")
    else:
        fail(f"retrieval benchmark: {r.stderr.strip() or r.stdout.strip()}")
    r, reused = _scale_benchmark(root)
    if r.returncode == 0:
        try:
            benchmark = json.loads(r.stdout)
            summary = benchmark["summary"]
            largest = max(
                benchmark["scale_results"],
                key=lambda row: row["factor"],
            )
            ok(
                "scale benchmark "
                f"{summary['scales_passed']}/{summary['scales']} scales, "
                f"{summary['query_cases_passed']}/{summary['query_cases']} query replays, "
                f"largest={summary['largest_concept_count']} concepts, "
                f"p95={largest['query_p95_seconds']:.3f}s"
                + (" (reused: its inputs are unchanged since this passing run)" if reused else "")
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            fail(f"scale benchmark emitted an invalid report: {error}")
    else:
        fail(f"scale benchmark: {r.stderr.strip() or r.stdout.strip()}")

    suites = _Suites(root)  # parallel owner suites start here; exclusive-lock suites run alone later
    # 12. second-brain behavioral tests
    _section("[12] second-brain tests")
    r = suites.result("second_brain")
    if r.returncode == 0:
        summary = next(
            (
                line
                for line in reversed(r.stderr.strip().splitlines())
                if line.startswith("Ran ")
            ),
            "behavioral tests passed",
        )
        ok(summary)
    else:
        fail(f"second-brain tests: {r.stderr.strip() or r.stdout.strip()}")

    # 13. universal score, translation, and non-submitting provider build
    _section("[13] universal score, control translation, and provider build")
    r = _run(
        [sys.executable, "-m", "lab.compiler.score", "validate"],
        capture_output=True,
        text=True,
        cwd=root,
    )
    if r.returncode == 0:
        ok(f"compiler configuration {r.stdout.strip()}")
    else:
        fail(f"universal-score configuration: {r.stderr.strip() or r.stdout.strip()}")
    r = _run(
        [sys.executable, "-m", "lab.compiler.build", "validate"],
        capture_output=True,
        text=True,
        cwd=root,
    )
    if r.returncode == 0:
        ok(f"build configuration {r.stdout.strip()}")
    else:
        fail(f"provider-build configuration: {r.stderr.strip() or r.stdout.strip()}")
    r = suites.result("compiler")
    if r.returncode == 0:
        summary = next(
            (
                line
                for line in reversed(r.stderr.strip().splitlines())
                if line.startswith("Ran ")
            ),
            "compiler tests passed",
        )
        ok(summary)
    else:
        fail(f"compiler tests: {r.stderr.strip() or r.stdout.strip()}")

    # 14. journaled render runtime and generation adapters
    _section("[14] render runtime and generation adapters")
    r = _run(
        [sys.executable, "-m", "lab.runtime.runner", "validate"],
        capture_output=True,
        text=True,
        cwd=root,
    )
    if r.returncode == 0:
        ok(f"runtime configuration {r.stdout.strip()}")
    else:
        fail(f"render-runtime configuration: {r.stderr.strip() or r.stdout.strip()}")
    r = suites.result("runtime")
    if r.returncode == 0:
        summary = next(
            (
                line
                for line in reversed(r.stderr.strip().splitlines())
                if line.startswith("Ran ")
            ),
            "runtime tests passed",
        )
        ok(summary)
    else:
        fail(f"render-runtime tests: {r.stderr.strip() or r.stdout.strip()}")

    # 15. provider-neutral render verification and bounded repair
    _section("[15] render verification and bounded repair")
    r = _run(
        [sys.executable, "-m", "lab.verification.verify", "validate"],
        capture_output=True,
        text=True,
        cwd=root,
    )
    if r.returncode == 0:
        ok(f"verification configuration {r.stdout.strip()}")
    else:
        fail(f"render-verification configuration: {r.stderr.strip() or r.stdout.strip()}")
    r = suites.result("verification")
    if r.returncode == 0:
        summary = next(
            (
                line
                for line in reversed(r.stderr.strip().splitlines())
                if line.startswith("Ran ")
            ),
            "verification tests passed",
        )
        ok(summary)
    else:
        fail(f"render-verification tests: {r.stderr.strip() or r.stdout.strip()}")

    # 16. stable application facade and transport parity
    _section("[16] application facade and client adapters")
    r = _run(
        [sys.executable, "-m", "lab.application.contracts"],
        capture_output=True,
        text=True,
        cwd=root,
    )
    if r.returncode == 0:
        ok(f"application configuration {r.stdout.strip()}")
    else:
        fail(f"application configuration: {r.stderr.strip() or r.stdout.strip()}")
    r = suites.result("application")
    if r.returncode == 0:
        summary = next(
            (
                line
                for line in reversed(r.stderr.strip().splitlines())
                if line.startswith("Ran ")
            ),
            "application tests passed",
        )
        ok(summary)
    else:
        fail(f"application tests: {r.stderr.strip() or r.stdout.strip()}")

    # 17. bounded local-release hardening and qualification contracts
    _section("[17] local-release hardening and qualification")
    r = _run(
        [sys.executable, "-m", "lab.release.contracts"],
        capture_output=True,
        text=True,
        cwd=root,
    )
    if r.returncode == 0:
        ok(f"release configuration {r.stdout.strip()}")
    else:
        fail(f"release configuration: {r.stderr.strip() or r.stdout.strip()}")
    r = _run(
        [sys.executable, "-m", "lab.release.security"],
        capture_output=True,
        text=True,
        cwd=root,
    )
    if r.returncode == 0:
        security = json.loads(r.stdout)
        ok(
            "release security "
            + json.dumps(
                {
                    "core_locked_dependencies": security["core_locked_dependencies"],
                    "provider_locked_dependencies": security["provider_locked_dependencies"],
                    "status": security["status"],
                },
                sort_keys=True,
            )
        )
    else:
        fail(f"release security: {r.stderr.strip() or r.stdout.strip()}")
    r = suites.result("release")
    if r.returncode == 0:
        summary = next(
            (
                line
                for line in reversed(r.stderr.strip().splitlines())
                if line.startswith("Ran ")
            ),
            "release tests passed",
        )
        ok(summary)
    else:
        fail(f"release tests: {r.stderr.strip() or r.stdout.strip()}")

    # 18. forbidden fork-names anywhere tracked
    _section("[18] anti-fork naming")
    # profiles/ is a versioned-asset zone (profile://.../_v2, _v3 are semantic versions, not forks)
    offenders = [str(p.relative_to(root)) for p in root.rglob("*")
                 if p.is_file() and re.search(r"_(v2|final|new|copy)\.", p.name, re.I)
                 and ".git" not in p.parts and "work" not in p.parts
                 and "research" not in p.parts and "profiles" not in p.parts]
    if offenders:
        for o in offenders:
            fail(f"forbidden fork-name: {o}")
    else:
        ok("no *_v2/_final/_new/_copy files")

    print()
    ended = time.monotonic()
    marks = [*SECTIONS, ("", ended)]
    slow = sorted(((marks[i + 1][1] - start, title) for i, (title, start) in enumerate(SECTIONS)), reverse=True)[:5]
    print(f"gate time {ended - SECTIONS[0][1]:.0f} s; slowest: " + "; ".join(f"{title} {seconds:.0f} s" for seconds, title in slow))
    if FAILS:
        print(f"GATE RED: {len(FAILS)} failure(s), {len(WARNS)} warning(s). Do not commit.")
        sys.exit(1)
    print(f"GATE GREEN ({len(WARNS)} warning(s)). Safe to commit.")


if __name__ == "__main__":
    main()
