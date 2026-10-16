"""Regression checks for root-level modules required by the Docker image."""
import unittest
from pathlib import Path


class DockerPackagingTests(unittest.TestCase):
    def test_acquisition_import_service_is_copied_into_image(self):
        root = Path(__file__).resolve().parents[1]
        dockerfile = (root / "Dockerfile").read_text(encoding="utf-8")
        copied_sources = set()
        for line in dockerfile.splitlines():
            if not line.startswith("COPY ") or not line.rstrip().endswith(" ./"):
                continue
            parts = line.split()
            source_start = 2 if parts[1].startswith("--") else 1
            copied_sources.update(parts[source_start:-1])

        self.assertIn(
            "acquisition_import_service.py",
            copied_sources,
            "The lazy import-completion adapter dependency must be copied into the image.",
        )


if __name__ == "__main__":
    unittest.main()
