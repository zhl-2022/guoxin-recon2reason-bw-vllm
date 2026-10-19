"""Independent repository snapshots preserve evidence and reject unsafe inputs."""
from contextlib import redirect_stdout, redirect_stderr
import hashlib
import base64
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("task_repositories_under_test", ROOT / "scripts/prepare_task_repositories.py")
repositories = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(repositories)


def source_fixture(root):
    for folder in ("src", "scripts", "tests", "docs", "fixtures", "evidence"):
        (root / folder).mkdir(parents=True)
    (root / "pyproject.toml").write_text('[project]\nname="fixture"\nversion="0.1.0"\n', encoding="utf-8")
    (root / ".gitignore").write_text("runtime/\ndist/\n", encoding="utf-8")
    (root / "evidence/observed.json").write_text('{"actual":true}\n', encoding="utf-8")
    (root / "docs/notes.md").write_text("Actual development note.\n", encoding="utf-8")
    (root / "scripts/check.py").write_text("print('fixture check')\n", encoding="utf-8")
    for task in repositories.TASKS:
        directory = root / "tasks" / task
        directory.mkdir(parents=True)
        config = {"slug": task, "track": "T04" if "asr" in task else "T02", "model": {"id": "fixture/" + task},
                  "official": {"image_reference": None}, "evidence_files": ["evidence/observed.json"]}
        (directory / "task.json").write_text(json.dumps(config), encoding="utf-8")
        (directory / "README.md").write_text("# " + task + "\n\n[Observed](../../evidence/observed.json)\n\n```bash\n# [Keep](../../evidence/observed.json)\nbash run.sh --dry-run\n```\n\n[Notes](../../docs/notes.md)\n", encoding="utf-8")
        (directory / "run.sh").write_text("#!/usr/bin/env bash\nprintf '%s\\n' 'fixture dry run'\n", encoding="utf-8")
        (directory / "env.sh").write_text("export MODEL_ID=fixture\n", encoding="utf-8")
        community = directory / "community"
        community.mkdir()
        project_id, category = repositories.MODELZOO_PROJECTS[task]
        contents = {
            "model.properties": (f"modelCode={project_id}\nmodelName={task}\nmodelDescription=Fixture\n"
                                 f"processType=推理\nappCategory={category}\nframeType=pytorch,vllm\naccelerateType=BW\n").encode(),
            "LICENSE": b"No repository-wide license selected in this fixture.\n",
            "icon.png": base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+cGZkAAAAASUVORK5CYII="),
            "README_origin.md": b"# Original publisher fixture README\n",
            "requirements.txt": b"# Preserve the native Torch/vLLM environment; no installation targets.\n"}
        for name, raw in contents.items():
            (community / name).write_bytes(raw)
        metadata = {"schema_version": 1, "task": task, "sourcefind_project_id": project_id,
                    "model_id": config["model"]["id"], "app_category": category,
                    "observed_accelerator": "BW", "formal_ready": False, "submitted": False,
                    "promoted_files": {name: {"source": name, "bytes": len(raw),
                                               "sha256": hashlib.sha256(raw).hexdigest()} for name, raw in contents.items()},
                    "upstream_sources": [{"path": name, "url": "https://example.test/fixed/" + name,
                                          "bytes": len(contents[name]), "sha256": hashlib.sha256(contents[name]).hexdigest()}
                                         for name in ("README_origin.md", "icon.png")]}
        (community / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")


class TaskRepositoryTests(unittest.TestCase):
    def test_default_plan_has_no_filesystem_or_git_side_effects(self):
        with tempfile.TemporaryDirectory() as temporary:
            root, output = Path(temporary) / "source", Path(temporary) / "output"
            source_fixture(root)
            with patch.object(repositories, "build", side_effect=AssertionError("No build by default")), redirect_stdout(io.StringIO()) as stream:
                self.assertEqual(repositories.main(["--source-root", str(root), "--output-root", str(output)]), 0)
            report = json.loads(stream.getvalue())
            self.assertEqual(report["mode"], "plan_only")
            self.assertFalse(report["git_commands_run"])
            self.assertEqual(len(report["repositories"]), 3)
            self.assertFalse(output.exists())

    def test_build_hashes_scope_and_readme_links_without_changing_shell_fences(self):
        with tempfile.TemporaryDirectory() as temporary:
            root, output = Path(temporary) / "source", Path(temporary) / "output"
            source_fixture(root)
            sources, prepared = repositories.plan(root, output)
            results = repositories.build(output, prepared, sources.missing)
            self.assertEqual(len(results), 3)
            for task in repositories.TASKS:
                destination = output / task
                self.assertFalse((destination / ".git").exists())
                self.assertIn(b"* -text\n", (destination / ".gitattributes").read_bytes())
                state = json.loads((destination / "ROOT_TASK.json").read_text(encoding="utf-8"))
                self.assertEqual(state["primary_task"], task)
                self.assertFalse(state["formal_ready"])
                self.assertFalse(state["submitted"])
                self.assertIsNone(state["repository_url"])
                self.assertIsNone(state["image_reference"])
                text = (destination / "README.md").read_text(encoding="utf-8")
                self.assertIn("[Observed](evidence/observed.json)", text)
                self.assertIn("# [Keep](../../evidence/observed.json)", text)
                self.assertIn("bash run.sh --dry-run", text)
                report = json.loads((destination / "repository-manifest.json").read_text(encoding="utf-8"))
                for entry in report["files"]:
                    raw = (destination / entry["path"]).read_bytes()
                    self.assertEqual(len(raw), entry["bytes"])
                    self.assertEqual(hashlib.sha256(raw).hexdigest(), entry["sha256"])
                self.assertEqual((destination / "evidence/observed.json").read_bytes(), (root / "evidence/observed.json").read_bytes())
                for name in repositories.COMMUNITY_ROOT_FILES:
                    self.assertEqual((destination / name).read_bytes(), (root / "tasks" / task / "community" / name).read_bytes())

    def test_community_required_files_cannot_be_missing_empty_or_hash_mismatched(self):
        for mutation in ("missing", "empty", "sha"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                root, output = Path(temporary) / "source", Path(temporary) / "output"
                source_fixture(root)
                target = root / "tasks" / repositories.TASKS[0] / "community/LICENSE"
                if mutation == "missing":
                    target.unlink()
                elif mutation == "empty":
                    target.write_bytes(b"")
                else:
                    target.write_bytes(b"unreviewed different license scope\n")
                with self.assertRaisesRegex(ValueError, "Missing/empty|SHA mismatch"):
                    repositories.plan(root, output)
                self.assertFalse(output.exists())

    def test_community_project_id_provenance_and_promotion_allowlist_are_checked(self):
        for mutation in ("project_id", "property_id", "upstream_sha", "extra_promotion", "renamed_source", "install_torch"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                root, output = Path(temporary) / "source", Path(temporary) / "output"
                source_fixture(root)
                community = root / "tasks" / repositories.TASKS[0] / "community"
                meta_path = community / "metadata.json"
                data = json.loads(meta_path.read_text())
                if mutation == "project_id":
                    data["sourcefind_project_id"] += 1
                elif mutation == "property_id":
                    path = community / "model.properties"
                    path.write_bytes(path.read_bytes().replace(b"modelCode=15915", b"modelCode=15916"))
                    data["promoted_files"]["model.properties"].update(bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
                elif mutation == "upstream_sha":
                    data["upstream_sources"][0]["sha256"] = "0" * 64
                elif mutation == "extra_promotion":
                    data["promoted_files"]["run.sh"] = {"source": "run.sh", "bytes": 1, "sha256": "0" * 64}
                elif mutation == "renamed_source":
                    data["promoted_files"]["LICENSE"]["source"] = "../LICENSE"
                else:
                    path = community / "requirements.txt"
                    path.write_bytes(b"torch==2.9.0\n")
                    data["promoted_files"]["requirements.txt"].update(bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
                meta_path.write_text(json.dumps(data), encoding="utf-8")
                with self.assertRaises(ValueError):
                    repositories.plan(root, output)
                self.assertFalse(output.exists())

    def test_destinations_are_checked_together_and_existing_tree_is_untouched(self):
        with tempfile.TemporaryDirectory() as temporary:
            root, output = Path(temporary) / "source", Path(temporary) / "output"
            source_fixture(root)
            sources, prepared = repositories.plan(root, output)
            existing = output / repositories.TASKS[1]
            existing.mkdir(parents=True)
            (existing / "keep.txt").write_text("keep", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "already exists"):
                repositories.build(output, prepared, sources.missing)
            self.assertFalse((output / repositories.TASKS[0]).exists())
            self.assertEqual((existing / "keep.txt").read_text(), "keep")

    def test_missing_evidence_is_reported_and_cannot_build_empty_replacement(self):
        with tempfile.TemporaryDirectory() as temporary:
            root, output = Path(temporary) / "source", Path(temporary) / "output"
            source_fixture(root)
            (root / "evidence/observed.json").unlink()
            sources, prepared = repositories.plan(root, output)
            self.assertIn("evidence/observed.json", sources.missing)
            with self.assertRaisesRegex(ValueError, "Required files missing"):
                repositories.build(output, prepared, sources.missing)
            self.assertFalse(output.exists())

    def test_path_traversal_absolute_and_sensitive_suffixes_are_rejected(self):
        for name in ("../outside.json", "/outside.json", "evidence/../secret.json", "C:/secret.json", "..\\secret.json"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                repositories.relative_name(name)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "source"
            source_fixture(root)
            for name in ("scripts/credential.key", "scripts/.env.private", "scripts/weights.safetensors"):
                path = root / name
                path.write_text("sensitive", encoding="utf-8")
                with self.subTest(name=name), self.assertRaisesRegex(ValueError, "Excluded"):
                    repositories.common_sources(root)
                path.unlink()

    def test_symlink_source_and_source_root_are_rejected_without_following(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "source"
            source_fixture(root)
            external = Path(temporary) / "outside.json"
            external.write_text("{}", encoding="utf-8")
            link = root / "scripts/link.json"
            try:
                link.symlink_to(external)
            except (OSError, NotImplementedError) as error:
                self.skipTest("Symlink creation unavailable: " + str(error))
            with self.assertRaisesRegex(ValueError, "Symlink/reparse"):
                repositories.common_sources(root)
            link.unlink()
            alias = Path(temporary) / "source-alias"
            alias.symlink_to(root, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "Source root"):
                repositories.plan(alias, Path(temporary) / "output")

    def test_embedded_credentials_and_oversize_source_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "credential"):
            repositories.scan_payload("evidence/unsafe.json", b'{"api' + b'_key":"AbCdEf0123456789"}')
        with self.assertRaisesRegex(ValueError, "private key"):
            repositories.scan_payload("evidence/unsafe.txt", b"-----BEGIN " + b"PRIVATE KEY-----\n")
        with patch.object(repositories, "MAX_BYTES", 2), self.assertRaisesRegex(ValueError, "50 MiB"):
            repositories.scan_payload("evidence/large.txt", b"abc")

    def test_markdown_escaping_workspace_is_rejected_and_reference_newlines_survive(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(ValueError, "escapes"):
                repositories.local_target(root, "docs/example.md", "../../outside.json")
            payload = b"# Report\n[obs]: ../../evidence/data.json\nNext paragraph.\n"
            readme = repositories.root_readme(root, repositories.TASKS[0], payload).decode()
            self.assertIn("[obs]: evidence/data.json\nNext paragraph.", readme)

    def test_explicit_lf_normalization_records_both_hashes_without_changing_source_or_binary(self):
        with tempfile.TemporaryDirectory() as temporary:
            root, output = Path(temporary) / "source", Path(temporary) / "output"
            source_fixture(root)
            original = b"\xef\xbb\xbfOne\r\nTwo\rThree\n"
            binary = b"binary-file-even-if-valid-utf8\r\n"
            (root / "docs/notes.md").write_bytes(original)
            (root / "fixtures/sample.wav").write_bytes(binary)
            _sources, raw = repositories.plan(root, output, tasks=(repositories.TASKS[0],))
            self.assertEqual(raw[repositories.TASKS[0]]["docs/notes.md"], original)
            self.assertNotIn("repository-normalization.json", raw[repositories.TASKS[0]])
            sources, prepared = repositories.plan(root, output, tasks=(repositories.TASKS[0],), normalize_text_lf=True)
            files = prepared[repositories.TASKS[0]]
            self.assertEqual(files["docs/notes.md"], original.replace(b"\r\n", b"\n"))
            self.assertEqual(files["fixtures/sample.wav"], binary)
            self.assertEqual((root / "docs/notes.md").read_bytes(), original)
            report = json.loads(files["repository-normalization.json"])
            entries = {item["path"]: item for item in report["files"]}
            entry = entries["docs/notes.md"]
            self.assertEqual(entry["original_sha256"], hashlib.sha256(original).hexdigest())
            self.assertEqual(entry["normalized_sha256"], hashlib.sha256(files["docs/notes.md"]).hexdigest())
            self.assertEqual(entry["original_bytes"], len(original))
            self.assertEqual(entry["normalized_bytes"], len(files["docs/notes.md"]))
            self.assertTrue(entry["changed"])
            self.assertEqual(entries["fixtures/sample.wav"]["kind"], "binary_preserved")
            self.assertFalse(entries["fixtures/sample.wav"]["changed"])
            self.assertIn(b"* -text\n", files[".gitattributes"])
            repositories.build(output, prepared, sources.missing)
            destination = output / repositories.TASKS[0]
            manifest = json.loads((destination / "repository-manifest.json").read_text(encoding="utf-8"))
            for item in manifest["files"]:
                self.assertEqual(hashlib.sha256((destination / item["path"]).read_bytes()).hexdigest(), item["sha256"])

    def test_lf_normalization_rejects_invalid_utf8_and_nul_in_declared_text(self):
        for raw in (b"invalid\xff\r\n", b"text\0with\r\nNUL"):
            with self.subTest(raw=raw), self.assertRaisesRegex(ValueError, "normalization"):
                repositories.normalize_payloads_text_lf({"evidence/log.txt": raw})

    def test_real_independent_tree_runs_python_checks_and_shell_argument_preview(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "repositories"
            sources, prepared = repositories.plan(ROOT, output, tasks=(repositories.TASKS[0],))
            repositories.build(output, prepared, sources.missing)
            destination = output / repositories.TASKS[0]
            result = subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-p", "test_asr_task_prepare.py"], cwd=destination, capture_output=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace")[-3000:])
            if os.name == "nt" and shutil.which("wsl"):
                linux_path = "/mnt/" + destination.drive[0].lower() + destination.as_posix()[2:]
                command = ["wsl", "--", "bash", linux_path + "/run.sh", "--dry-run"]
            elif os.name == "posix" and shutil.which("bash"):
                command = ["bash", str(destination / "run.sh"), "--dry-run"]
            else:
                return  # CPU Python execution above is still required on every host.
            result = subprocess.run(command, cwd=destination, capture_output=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace")[-3000:])
            self.assertIn(b'"dry_run": true', result.stdout)
            self.assertIn(b'recon2reason-reasoning-4b', result.stdout)
            self.assertFalse((destination / "tasks/recon2reason-bw-vllm/runtime").exists())


if __name__ == "__main__":
    unittest.main()
