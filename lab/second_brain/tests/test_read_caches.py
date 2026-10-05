"""Read caches must only save time: same answers, no stale data, no shared mutable results."""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from lab.compiler import profiles
from lab.second_brain.src import directing_session as direct
from lab.second_brain.src import validate
from lab.second_brain.src.validate import REPO_ROOT, ValidationFailure, load_schema, validate_instance

SCHEMA = {"type": "object", "required": ["id", "tags"], "additionalProperties": False,
          "properties": {"id": {"type": "string"}, "tags": {"type": "array", "items": {"type": "string"}}}}


def later(path: Path) -> None:
    """Move a rewritten file's timestamp forward so the test never depends on clock resolution."""
    stat = path.stat()
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000_000))


class ValidationCacheTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "repo"
        self.schema_path = self.root / "lab/second_brain/schemas" / validate.SCHEMA_FILES["concept"]
        self.schema_path.parent.mkdir(parents=True)
        self.schema_path.write_text(json.dumps(SCHEMA))

    def test_a_cached_pass_never_lets_a_different_value_through(self):
        good = {"id": "a", "tags": ["x"]}
        validate_instance("concept", good, self.root)
        validate_instance("concept", dict(good), self.root)                      # served from the cache
        for bad in ({"id": "a", "tags": [1]}, {"id": 1, "tags": ["x"]}, {"id": "a", "tags": ["x"], "extra": 1},
                    {"id": "a", "tags": ("x",)}):                                 # a tuple is not a JSON array
            with self.assertRaises(ValidationFailure):
                validate_instance("concept", bad, self.root)
        with self.assertRaises(ValidationFailure):                               # failures are not cached either
            validate_instance("concept", {"id": "a", "tags": [1]}, self.root)

    def test_a_changed_schema_is_read_again(self):
        good = {"id": "a", "tags": ["x"]}
        validate_instance("concept", good, self.root)
        self.schema_path.write_text(json.dumps({**SCHEMA, "required": ["id", "tags", "owner"]}))
        later(self.schema_path)
        with self.assertRaises(ValidationFailure):
            validate_instance("concept", good, self.root)
        self.assertIn("owner", load_schema("concept", self.root)["required"])

    def test_identical_schemas_in_two_checkouts_agree_and_stay_separate(self):
        other = self.root.parent / "other"
        shutil.copytree(self.root, other)
        good = {"id": "a", "tags": ["x"]}
        validate_instance("concept", good, self.root)
        validate_instance("concept", good, other)
        (other / self.schema_path.relative_to(self.root)).write_text(json.dumps({**SCHEMA, "required": ["id", "tags", "owner"]}))
        later(other / self.schema_path.relative_to(self.root))
        validate_instance("concept", good, self.root)                            # the first checkout is unchanged
        with self.assertRaises(ValidationFailure):
            validate_instance("concept", good, other)

    def test_loaded_schemas_are_private_copies(self):
        load_schema("concept", self.root)["required"].append("poison")
        self.assertEqual(load_schema("concept", self.root)["required"], ["id", "tags"])
        validate_instance("concept", {"id": "a", "tags": []}, self.root)


class RegistryCacheTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "repo"
        for relative in ("lab/second_brain/directing_passes.yaml", "lab/second_brain/curated/ontology_registry.json"):
            (self.root / relative).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO_ROOT / relative, self.root / relative)

    def test_pass_registry_matches_the_real_one_and_is_a_private_copy(self):
        first = direct.load_pass_registry(self.root)
        self.assertEqual(first, direct.load_pass_registry(REPO_ROOT))
        first["passes"].clear()
        self.assertTrue(direct.load_pass_registry(self.root)["passes"])

    def test_pass_registry_edits_are_seen(self):
        direct.load_pass_registry(self.root)
        path = self.root / "lab/second_brain/directing_passes.yaml"
        path.write_text(path.read_text().replace("cpcs.directing_passes/1.0", "cpcs.directing_passes/9.9"))
        later(path)
        with self.assertRaises(ValidationFailure):
            direct.load_pass_registry(self.root)
        ontology = self.root / "lab/second_brain/curated/ontology_registry.json"
        path.write_text(path.read_text().replace("cpcs.directing_passes/9.9", "cpcs.directing_passes/1.0"))
        later(path)
        direct.load_pass_registry(self.root)
        value = json.loads(ontology.read_text())
        value["layers"] = {}
        ontology.write_text(json.dumps(value))
        later(ontology)
        with self.assertRaises(ValidationFailure):                               # the second input file is watched too
            direct.load_pass_registry(self.root)

    def test_profile_files_are_private_copies_and_edits_are_seen(self):
        path = self.root / "profile.yaml"
        path.write_text("name: one\nitems: [a]\n")
        profiles._read_yaml(path)["items"].append("poison")
        self.assertEqual(profiles._read_yaml(path), {"name": "one", "items": ["a"]})
        path.write_text("name: two\nitems: [a]\n")
        later(path)
        self.assertEqual(profiles._read_yaml(path)["name"], "two")
        path.write_text("- not an object\n")
        later(path)
        with self.assertRaises(ValueError):
            profiles._read_yaml(path)


if __name__ == "__main__":
    unittest.main()
