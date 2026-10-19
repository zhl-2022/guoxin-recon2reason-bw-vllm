"""Managed snapshot updates leave Git metadata and unrelated working files intact."""
from contextlib import redirect_stdout, redirect_stderr
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


update = load("update_repositories_under_test", ROOT / "scripts/update_task_repositories.py")
fixtures = load("repository_update_fixtures", ROOT / "tests/test_task_repositories.py")
TASK = update.preparation.TASKS[0]


def hashes(folder):
    return {path.relative_to(folder).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in folder.rglob("*") if path.is_file()}


class RepositoryUpdateTests(unittest.TestCase):
    def setup_repository(self, parent):
        root, output = parent / "source", parent / "repositories"
        fixtures.source_fixture(root)
        (root / "src/old.py").write_text("old = 1\n", encoding="utf-8")
        sources, prepared = update.preparation.plan(root, output, tasks=(TASK,))
        update.preparation.build(output, prepared, sources.missing)
        destination = output / TASK
        if not shutil.which("git"):
            self.skipTest("git not available for temporary repository test")
        result = subprocess.run(["git", "-C", str(destination), "init", "-b", "main"], capture_output=True)
        self.assertEqual(result.returncode, 0)
        return root, output, destination

    def test_default_plan_does_not_modify_existing_working_files_or_git(self):
        with tempfile.TemporaryDirectory() as temporary:
            root, output, destination = self.setup_repository(Path(temporary))
            before = hashes(destination)
            (root / "docs/notes.md").write_text("new note\n", encoding="utf-8")
            with patch.object(update, "apply_updates", side_effect=AssertionError("No writes in plan")), redirect_stdout(io.StringIO()) as stream:
                result = update.main(["--source-root", str(root), "--repository-root", str(output), "--task", TASK])
            self.assertEqual(result, 0)
            self.assertEqual(json.loads(stream.getvalue())["mode"], "plan_only")
            self.assertEqual(hashes(destination), before)

    def test_apply_add_replace_remove_rehash_and_keep_git_and_unrelated_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root, output, destination = self.setup_repository(Path(temporary))
            git_before = hashes(destination / ".git")
            (destination / "unmanaged.txt").write_text("keep this\n", encoding="utf-8")
            (root / "docs/notes.md").write_text("new note\n", encoding="utf-8")
            (root / "src/old.py").unlink()
            (root / "src/new.py").write_text("new = 2\n", encoding="utf-8")
            planned = update.prepare_update(root, output, (TASK,))
            self.assertEqual({item["operation"] for item in planned[0]["operations"]}, {"add", "replace", "remove"})
            update.apply_updates(planned)
            self.assertEqual(hashes(destination / ".git"), git_before)
            self.assertEqual((destination / "unmanaged.txt").read_text(), "keep this\n")
            self.assertFalse((destination / "src/old.py").exists())
            self.assertEqual((destination / "src/new.py").read_bytes(), (root / "src/new.py").read_bytes())
            manifest = json.loads((destination / "repository-manifest.json").read_text(encoding="utf-8"))
            self.assertFalse(manifest["formal_ready"])
            self.assertFalse(manifest["submitted"])
            self.assertNotIn("unmanaged.txt", {item["path"] for item in manifest["files"]})
            for item in manifest["files"]:
                raw = (destination / item["path"]).read_bytes()
                self.assertEqual(len(raw), item["bytes"])
                self.assertEqual(hashlib.sha256(raw).hexdigest(), item["sha256"])
            self.assertEqual(update.prepare_update(root, output, (TASK,))[0]["operations"], [])

    def test_local_edits_and_unmanaged_target_collisions_are_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root, output, destination = self.setup_repository(Path(temporary))
            (destination / "docs/notes.md").write_text("manual local edit\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "changed outside"):
                update.prepare_update(root, output, (TASK,))
            (destination / "docs/notes.md").write_bytes((root / "docs/notes.md").read_bytes())
            (root / "src/new.py").write_text("new = 1\n", encoding="utf-8")
            (destination / "src/new.py").write_text("unrelated existing file\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                update.prepare_update(root, output, (TASK,))

    def test_concurrent_working_change_is_detected_before_any_update(self):
        with tempfile.TemporaryDirectory() as temporary:
            root, output, destination = self.setup_repository(Path(temporary))
            (root / "docs/notes.md").write_text("new note\n", encoding="utf-8")
            planned = update.prepare_update(root, output, (TASK,))
            (destination / "src/old.py").write_text("edited after plan\n", encoding="utf-8")
            before = hashes(destination)
            with self.assertRaisesRegex(ValueError, "changed since plan"):
                update.apply_updates(planned)
            self.assertEqual(hashes(destination), before)

    def test_extra_evidence_is_explicit_missing_sensitive_and_large_log_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root, output, destination = self.setup_repository(Path(temporary))
            with self.assertRaisesRegex(ValueError, "Missing required"):
                update.prepare_update(root, output, (TASK,), ("evidence/not-there.json",))
            for name in ("../secret.json", "evidence/private.key", ".git/config"):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    update.prepare_update(root, output, (TASK,), (name,))
            (root / "evidence/new.log").write_bytes(b"12345")
            with patch.object(update, "MAX_LOG_BYTES", 4), self.assertRaisesRegex(ValueError, "Log exceeds"):
                update.prepare_update(root, output, (TASK,), ("evidence/new.log",))
            planned = update.prepare_update(root, output, (TASK,), ("evidence/new.log",))
            self.assertIn("evidence/new.log", planned[0]["payloads"])
            self.assertFalse((destination / "evidence/new.log").exists())

    def test_malicious_manifest_git_path_and_symlink_target_are_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root, output, destination = self.setup_repository(Path(temporary))
            manifest_path = destination / "repository-manifest.json"
            original = manifest_path.read_bytes()
            manifest = json.loads(original)
            manifest["files"].append({"path": ".git/config", "bytes": 0, "sha256": "0" * 64})
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Managed path"):
                update.prepare_update(root, output, (TASK,))
            manifest_path.write_bytes(original)
            target = destination / "src/old.py"
            target.unlink()
            try:
                target.symlink_to(root / "src/old.py")
            except (OSError, NotImplementedError) as error:
                self.skipTest("Symlink creation unavailable: " + str(error))
            with self.assertRaisesRegex(ValueError, "Symlink/reparse"):
                update.prepare_update(root, output, (TASK,))

    def test_explicit_real_repository_metadata_is_retained(self):
        with tempfile.TemporaryDirectory() as temporary:
            root, output, destination = self.setup_repository(Path(temporary))
            state_path = destination / "ROOT_TASK.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["repository_url"] = "https://github.com/example/explicit-existing-repository"
            state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            manifest_path = destination / "repository-manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for item in manifest["files"]:
                if item["path"] == "ROOT_TASK.json":
                    raw = state_path.read_bytes()
                    item.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            planned = update.prepare_update(root, output, (TASK,))
            expected = json.loads(planned[0]["payloads"]["ROOT_TASK.json"])
            self.assertEqual(expected["repository_url"], state["repository_url"])

    def test_explicit_lf_update_safely_migrates_old_manifest_and_preserves_binary_and_git(self):
        with tempfile.TemporaryDirectory() as temporary:
            root, output, destination = self.setup_repository(Path(temporary))
            original = (root / "docs/notes.md").read_bytes()
            # The original fixture is host dependent; force an explicit CRLF source.
            original = b"Original\r\nSecond\r\n"
            (root / "docs/notes.md").write_bytes(original)
            first = update.prepare_update(root, output, (TASK,))
            update.apply_updates(first)
            binary = b"binary-even-if-utf8\r\n"
            (root / "fixtures/source.wav").write_bytes(binary)
            git_before = hashes(destination / ".git")
            planned = update.prepare_update(root, output, (TASK,), normalize_text_lf=True)
            files = planned[0]["payloads"]
            self.assertEqual(files["docs/notes.md"], b"Original\nSecond\n")
            self.assertEqual(files["fixtures/source.wav"], binary)
            update.apply_updates(planned)
            self.assertEqual(hashes(destination / ".git"), git_before)
            self.assertEqual((root / "docs/notes.md").read_bytes(), original)
            report = json.loads((destination / "repository-normalization.json").read_text(encoding="utf-8"))
            entry = next(item for item in report["files"] if item["path"] == "docs/notes.md")
            self.assertEqual(entry["original_sha256"], hashlib.sha256(original).hexdigest())
            self.assertEqual(entry["normalized_sha256"], hashlib.sha256(b"Original\nSecond\n").hexdigest())
            self.assertEqual(update.prepare_update(root, output, (TASK,), normalize_text_lf=True)[0]["operations"], [])
            (destination / "docs/notes.md").write_bytes(b"unreviewed manual edit\n")
            with self.assertRaisesRegex(ValueError, "changed outside"):
                update.prepare_update(root, output, (TASK,), normalize_text_lf=True)


if __name__ == "__main__":
    unittest.main()
