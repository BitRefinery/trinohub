"""Guards on docs/manifest.json and the topic files it points at.

The manifest is load-bearing in two places: /api/help serves the in-app Docs
viewer from it, and it drives the public docs site. Both fail quietly — a topic
whose file is missing 404s only when a reader clicks it, and a topic file that
nobody listed is simply invisible. Fail here instead.
"""

import json
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS = REPO_ROOT / "docs"
MANIFEST = DOCS / "manifest.json"

# Must match HELP_SLUG_PATTERN in trinohub/api.py, which rejects anything else
# before it reaches the filesystem.
SLUG_PATTERN = re.compile(r"^[a-z0-9-]+$")

# Markdown under docs/ that is deliberately not a reader-facing topic. Anything
# else must appear in the manifest or the test fails.
UNLISTED = {"releasing.md"}


class DocsManifestTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.topics = [
            topic
            for group in self.manifest["groups"]
            for topic in group["topics"]
        ]

    def test_every_topic_has_a_markdown_file(self):
        for topic in self.topics:
            with self.subTest(slug=topic["slug"]):
                self.assertTrue(
                    (DOCS / f"{topic['slug']}.md").is_file(),
                    f"manifest lists {topic['slug']} but docs/{topic['slug']}.md is missing",
                )

    def test_every_markdown_file_is_listed(self):
        listed = {f"{topic['slug']}.md" for topic in self.topics}
        found = {path.name for path in DOCS.glob("*.md")}
        orphans = found - listed - UNLISTED
        self.assertEqual(
            set(),
            orphans,
            "docs/ has topic files no group lists, so readers can't reach them: "
            f"{sorted(orphans)}",
        )

    def test_slugs_are_unique_and_well_formed(self):
        slugs = [topic["slug"] for topic in self.topics]
        self.assertEqual(sorted(slugs), sorted(set(slugs)), "duplicate slug in manifest")
        for slug in slugs:
            with self.subTest(slug=slug):
                self.assertRegex(slug, SLUG_PATTERN)

    def test_every_topic_has_a_title(self):
        for topic in self.topics:
            with self.subTest(slug=topic["slug"]):
                self.assertTrue(topic.get("title", "").strip())

    def test_groups_declare_admin_gating(self):
        # help_admin_slugs() treats a missing "admin" key as public, so an admin
        # group that forgets the flag silently exposes its topics.
        for group in self.manifest["groups"]:
            with self.subTest(group=group.get("id")):
                self.assertIsInstance(group.get("admin"), bool)


if __name__ == "__main__":
    unittest.main()
