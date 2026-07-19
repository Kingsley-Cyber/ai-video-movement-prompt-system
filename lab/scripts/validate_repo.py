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
    print("[1] YAML parses")
    docs = {}
    for rel in ["lab/registry.yaml", "lab/blocks.yaml", *[str(p.relative_to(root)) for p in sorted((lab / "experiments").glob("*.yaml"))]]:
        p = root / rel
        try:
            docs[rel] = yaml.safe_load(p.read_text())
            ok(rel)
        except Exception as e:  # noqa: BLE001 — report any parse failure
            fail(f"{rel}: {e}")
    reg = docs.get("lab/registry.yaml") or {}
    blocks = docs.get("lab/blocks.yaml") or {}

    # 2. results.csv integrity
    print("[2] runs ledger")
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
    print("[3] evidence ids")
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
    print("[4] variants on disk")
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
    print("[5] registry pointers")
    for section in ("runbooks", "scripts"):
        for name, rel in (reg.get(section) or {}).items():
            (ok if (lab / rel).exists() else fail)(f"{section}.{name} -> lab/{rel}" if (lab / rel).exists()
                                                   else f"{section}.{name}: lab/{rel} missing")
    for key in ("control_surface", "block_library", "concept_index"):
        if reg.get(key) and not (lab / reg[key]).exists():
            fail(f"registry.{key}: lab/{reg[key]} missing")

    # 6. lab scripts compile
    print("[6] scripts compile")
    for script in sorted((lab / "scripts").glob("*.py")):
        try:
            py_compile.compile(str(script), doraise=True)
            ok(script.name)
        except py_compile.PyCompileError as e:
            fail(f"{script.name}: {e.msg}")

    # 7. runbook embedded records validate against the package schema (when jsonschema available)
    print("[7] runbook examples vs package schema")
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
    print("[8] char budgets")
    for asset in sorted((root / "assets").glob("*")):
        text = asset.read_text(errors="ignore")
        if "2000" in text or "2,000" in text:
            n = len(text)
            # templates include comments; budget applies to the paste payload — warn only past 2400
            (warn if n > 2400 else ok)(f"{asset.name}: {n} chars" + (" — over template allowance" if n > 2400 else ""))

    # 9. concept corpus integrity (delegates to concepts.py validate)
    print("[9] concept corpus")
    import subprocess
    r = subprocess.run([sys.executable, str(lab / "scripts" / "concepts.py"), "validate"],
                       capture_output=True, text=True, cwd=root)
    if r.returncode == 0:
        ok(r.stdout.strip().splitlines()[-1])
    else:
        fail(f"concepts.jsonl: {r.stdout.strip() or r.stderr.strip()}")

    # 10. forbidden fork-names anywhere tracked
    print("[10] anti-fork naming")
    offenders = [str(p.relative_to(root)) for p in root.rglob("*")
                 if p.is_file() and re.search(r"_(v2|final|new|copy)\.", p.name, re.I)
                 and ".git" not in p.parts and "research" not in p.parts]
    if offenders:
        for o in offenders:
            fail(f"forbidden fork-name: {o}")
    else:
        ok("no *_v2/_final/_new/_copy files")

    print()
    if FAILS:
        print(f"GATE RED: {len(FAILS)} failure(s), {len(WARNS)} warning(s). Do not commit.")
        sys.exit(1)
    print(f"GATE GREEN ({len(WARNS)} warning(s)). Safe to commit.")


if __name__ == "__main__":
    main()
