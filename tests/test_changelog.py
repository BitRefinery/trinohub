"""Guards on CHANGELOG.md and the release-notes extraction.

The release workflow publishes the extracted section as the GitHub Release
body and checks the CloudFormation GitRef default against the package version,
so both are worth failing on here — before a tag exists — rather than at tag
time, when the tag can no longer be moved.
"""

import re
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from changelog_section import extract  # noqa: E402

from trinohub import __version__  # noqa: E402

CHANGELOG = REPO_ROOT / "CHANGELOG.md"
CLOUDFORMATION = REPO_ROOT / "deploy" / "aws" / "cloudformation.yaml"

SAMPLE = """# Changelog

## [Unreleased]

## [0.3.0] - 2026-07-29

### Added

- A thing.

## [0.2.0] - 2026-07-20

### Added

- An older thing.

[0.3.0]: https://example.com/compare/v0.2.0...v0.3.0
[0.2.0]: https://example.com/releases/tag/v0.2.0
"""


class ChangelogExtractionTests(unittest.TestCase):
    def test_extracts_named_section(self):
        self.assertEqual(extract(SAMPLE, "0.3.0"), "### Added\n\n- A thing.")

    def test_leading_v_is_accepted(self):
        self.assertEqual(extract(SAMPLE, "v0.3.0"), extract(SAMPLE, "0.3.0"))

    def test_last_section_drops_trailing_link_block(self):
        body = extract(SAMPLE, "0.2.0")
        self.assertEqual(body, "### Added\n\n- An older thing.")
        self.assertNotIn("https://example.com", body)

    def test_missing_version_fails(self):
        with self.assertRaises(SystemExit):
            extract(SAMPLE, "9.9.9")

    def test_empty_section_fails(self):
        with self.assertRaises(SystemExit):
            extract("# Changelog\n\n## [Unreleased]\n\n## [0.1.0]\n", "0.1.0")


class ChangelogContentTests(unittest.TestCase):
    def test_changelog_has_section_for_current_version(self):
        body = extract(CHANGELOG.read_text(encoding="utf-8"), __version__)
        self.assertTrue(body.strip(), f"Changelog section for {__version__} is empty.")

    def test_cloudformation_gitref_matches_package_version(self):
        # The release workflow only verifies the *tag* against __version__; a
        # stale GitRef would publish clean and silently deploy the old release.
        text = CLOUDFORMATION.read_text(encoding="utf-8")
        match = re.search(r"GitRef:\s*\n\s*Type:\s*String\s*\n\s*Default:\s*(\S+)", text)
        self.assertIsNotNone(match, "Could not find the GitRef default in cloudformation.yaml.")
        self.assertEqual(
            match.group(1),
            f"v{__version__}",
            "cloudformation.yaml GitRef default must match the package version.",
        )


if __name__ == "__main__":
    unittest.main()
