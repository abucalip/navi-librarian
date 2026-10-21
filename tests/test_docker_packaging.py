"""Regression checks for root-level modules required by the Docker image."""
import ast
import unittest
from pathlib import Path


class DockerPackagingTests(unittest.TestCase):
    def test_legacy_server_imports_are_copied_into_image(self):
        root = Path(__file__).resolve().parents[1]
        dockerfile = (root / "Dockerfile").read_text(encoding="utf-8")
        copied_sources = set()
        for line in dockerfile.splitlines():
            if not line.startswith("COPY ") or not line.rstrip().endswith(" ./"):
                continue
            parts = line.split()
            source_start = 2 if parts[1].startswith("--") else 1
            copied_sources.update(parts[source_start:-1])

        root_modules = {path.stem for path in root.glob("*.py")}
        server = ast.parse(
            (root / "navidrome_server.py").read_text(encoding="utf-8"),
            filename="navidrome_server.py",
        )
        imported_root_modules = set()
        for node in ast.walk(server):
            if isinstance(node, ast.Import):
                imported_root_modules.update(
                    alias.name.split(".")[0]
                    for alias in node.names
                    if alias.name.split(".")[0] in root_modules
                )
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                module = node.module.split(".")[0]
                if module in root_modules:
                    imported_root_modules.add(module)

        missing = sorted(
            f"{module}.py"
            for module in imported_root_modules
            if f"{module}.py" not in copied_sources
        )
        self.assertEqual(
            missing,
            [],
            "Root-level modules imported by navidrome_server.py must be copied into the image.",
        )

    def test_slskd_integration_package_is_copied_into_image(self):
        root = Path(__file__).resolve().parents[1]
        dockerfile = (root / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("COPY --chown=librarian:librarian integrations/ ./integrations/", dockerfile)
        for module in ("client.py", "quality.py", "search.py", "search_polling.py", "transfers.py"):
            with self.subTest(module=module):
                self.assertTrue((root / "integrations" / "slskd" / module).is_file())

    def test_lastfm_integration_package_is_copied_into_image(self):
        root = Path(__file__).resolve().parents[1]
        dockerfile = (root / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("COPY --chown=librarian:librarian integrations/ ./integrations/", dockerfile)
        self.assertTrue((root / "integrations" / "lastfm" / "client.py").is_file())
        self.assertFalse((root / "lastfm_client.py").exists())

    def test_listenbrainz_integration_package_is_copied_into_image(self):
        root = Path(__file__).resolve().parents[1]
        dockerfile = (root / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("COPY --chown=librarian:librarian integrations/ ./integrations/", dockerfile)
        for module in ("client.py", "popularity.py"):
            with self.subTest(module=module):
                self.assertTrue((root / "integrations" / "listenbrainz" / module).is_file())
        self.assertNotIn("listenbrainz_client.py", dockerfile)
        self.assertFalse((root / "listenbrainz_client.py").exists())
        self.assertFalse((root / "listenbrainz_popularity.py").exists())

    def test_recommendation_package_is_copied_into_image(self):
        root = Path(__file__).resolve().parents[1]
        dockerfile = (root / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("COPY --chown=librarian:librarian recommendation/ ./recommendation/", dockerfile)
        for module in ("replay", "diagnostics", "mmr_evaluate", "profile_comparison"):
            with self.subTest(module=module):
                self.assertTrue((root / "recommendation" / f"{module}.py").is_file())
                self.assertFalse((root / f"recommendation_{module}.py").exists())
                self.assertNotIn(f"recommendation_{module}.py", dockerfile)

    def test_settings_package_is_copied_into_image(self):
        root = Path(__file__).resolve().parents[1]
        dockerfile = (root / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("COPY --chown=librarian:librarian settings/ ./settings/", dockerfile)
        for module, old in (("service", "service_settings"), ("persistence", "settings_persistence"),
                            ("music_paths", "music_paths"), ("data_directory", "data_directory")):
            with self.subTest(module=module):
                self.assertTrue((root / "settings" / f"{module}.py").is_file())
                self.assertFalse((root / f"{old}.py").exists())
                self.assertNotIn(f"{old}.py", dockerfile)

    def test_listening_profile_lives_in_recommendation_package(self):
        root = Path(__file__).resolve().parents[1]
        dockerfile = (root / "Dockerfile").read_text(encoding="utf-8")
        self.assertTrue((root / "recommendation" / "listening_profile.py").is_file())
        self.assertFalse((root / "listening_profile.py").exists())
        self.assertNotIn("listening_profile.py", dockerfile)

    def test_acquisition_request_modules_live_in_acquisition_package(self):
        root = Path(__file__).resolve().parents[1]
        dockerfile = (root / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("acquisition/ ./acquisition/", dockerfile)
        self.assertTrue((root / "acquisition" / "__init__.py").is_file())
        for name in (
            "candidate_queue", "candidate_start", "orchestration", "request_coordinator",
            "source_switch", "search_diagnostics", "lifecycle", "state",
        ):
            with self.subTest(module=name):
                self.assertTrue((root / "acquisition" / f"{name}.py").is_file())
                self.assertFalse((root / f"acquisition_{name}.py").exists())
                self.assertNotIn(f"acquisition_{name}.py", dockerfile)


if __name__ == "__main__":
    unittest.main()
