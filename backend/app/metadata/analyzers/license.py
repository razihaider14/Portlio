"""
Identifies the repository's license.

Two sources, in priority order:

1. GitHub's own license detection (repo_metadata["license"]["spdx_id"]).
   GitHub runs Licensee (the same tool used by RubyGems.org) server-side on
   every repository; trusting its result outright is more reliable than
   anything a lightweight client-side scan could do, so this gets
   confidence 1.0 when present.

2. A fallback for when the GitHub API reports no license (e.g. the repo has
   a LICENSE file but it doesn't match Licensee's corpus closely enough, or
   the API response is stale): a small table of highly distinctive,
   practically unique opening phrases from the handful of most common
   OSS licenses, matched only against the downloaded LICENSE file itself
   (never the README, to avoid matching an incidental mention).
"""

from app.metadata.models import AnalysisInput, Finding
from app.metadata.tree_utils import get_content, has_filename

_LICENSE_FILENAMES = ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING", "COPYING.md")

# (spdx_id, distinctive substring), each phrase is drawn from the license's
# canonical boilerplate and not shared by any other common license.
_LICENSE_MARKERS: tuple[tuple[str, str], ...] = (
    ("MIT", "permission is hereby granted, free of charge"),
    ("Apache-2.0", "apache license, version 2.0"),
    ("GPL-3.0", "gnu general public license"),
    ("BSD-3-Clause", "redistribution and use in source and binary forms"),
    ("MPL-2.0", "mozilla public license, v. 2.0"),
    ("ISC", "permission to use, copy, modify, and/or distribute this software"),
    (
        "Unlicense",
        "this is free and unencumbered software released into the public domain",
    ),
)


def _match_license_content(content: str) -> str | None:
    lowered = content.lower()
    for spdx_id, marker in _LICENSE_MARKERS:
        if marker in lowered:
            return spdx_id
    return None


class LicenseAnalyzer:
    """Identifies the repository's license via GitHub's API, then content fallback."""

    def analyze(self, input: AnalysisInput) -> list[Finding]:
        api_license = input.repo_metadata.get("license")
        if isinstance(api_license, dict) and api_license.get("spdx_id") not in (
            None,
            "NOASSERTION",
        ):
            value = {
                "detected": True,
                "spdx_id": api_license["spdx_id"],
                "source": "github_api",
            }
            return [
                Finding(
                    "license",
                    value,
                    1.0,
                    (f'GitHub API reports license "{api_license["spdx_id"]}"',),
                )
            ]

        has_file = has_filename(input.entries, *_LICENSE_FILENAMES)
        if not has_file:
            value = {"detected": False, "spdx_id": None, "source": None}
            return [Finding("license", value, 1.0, ("no LICENSE file found",))]

        content = get_content(input.file_contents, input.entries, *_LICENSE_FILENAMES)
        if content:
            spdx_id = _match_license_content(content)
            if spdx_id:
                value = {
                    "detected": True,
                    "spdx_id": spdx_id,
                    "source": "file_content_match",
                }
                return [
                    Finding(
                        "license",
                        value,
                        0.9,
                        (f'LICENSE file text matches "{spdx_id}" boilerplate',),
                    )
                ]

        # A LICENSE file exists but we couldn't identify which license it
        # is (content wasn't downloaded, or it didn't match a known
        # template), still meaningfully different from "no license at all".
        value = {"detected": True, "spdx_id": None, "source": "file_presence_only"}
        return [
            Finding(
                "license", value, 0.5, ("found a LICENSE file; text not identified",)
            )
        ]
