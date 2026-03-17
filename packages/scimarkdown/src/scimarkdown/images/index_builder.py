"""Figure index builder — generates a markdown table from extracted images."""

from __future__ import annotations

from scimarkdown.models import ImageRef


class IndexBuilder:
    """Builds a Markdown figure-index table from a list of ``ImageRef`` objects.

    The table has the header ``## Figure Index`` and four columns:
    ``#``, ``Figure``, ``Description``, and ``File``.

    Images without a ``reference_label`` show ``(no reference)`` in the
    *Figure* column.  The *Description* column is populated from
    ``ImageRef.caption`` when available, otherwise it is blank.

    An empty *images* list returns an empty string.
    """

    def build(self, images: list[ImageRef]) -> str:
        """Return a Markdown figure-index table, or ``""`` if *images* is empty."""
        if not images:
            return ""

        lines: list[str] = [
            "## Figure Index",
            "",
            "| # | Figure | Description | File |",
            "| --- | --- | --- | --- |",
        ]

        for idx, img in enumerate(images, start=1):
            figure_label = img.reference_label if img.reference_label else "(no reference)"
            description = img.caption if img.caption else ""
            filename = img.file_path.split("/")[-1] if img.file_path else ""
            lines.append(f"| {idx} | {figure_label} | {description} | {filename} |")

        return "\n".join(lines)
