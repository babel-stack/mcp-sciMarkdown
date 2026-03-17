"""SciMarkdown CLI entry point.

Usage examples::

    python -m scimarkdown document.pdf
    python -m scimarkdown document.pdf -o output.md
    python -m scimarkdown https://example.com/paper.pdf --latex-style github
    python -m scimarkdown document.pdf -c scimarkdown.yaml --output-dir ./figures
"""

import argparse
import sys
from pathlib import Path
from typing import Optional


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scimarkdown",
        description=(
            "Convert documents to enriched Markdown with LaTeX formulas "
            "and image references using SciMarkdown."
        ),
    )
    parser.add_argument(
        "input",
        help="File path or URL to convert.",
    )
    parser.add_argument(
        "-o", "--output",
        metavar="FILE",
        default=None,
        help="Output file path. Defaults to stdout.",
    )
    parser.add_argument(
        "-c", "--config",
        metavar="FILE",
        default=None,
        help="Path to a scimarkdown.yaml configuration file.",
    )
    parser.add_argument(
        "--latex-style",
        choices=["standard", "github"],
        default=None,
        help="Override the LaTeX rendering style (standard or github).",
    )
    parser.add_argument(
        "--output-dir",
        metavar="DIR",
        default=None,
        help="Override the output directory for extracted images.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    """Run the SciMarkdown CLI.

    Returns:
        Exit code (0 on success, non-zero on error).
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    # Import here so import errors are reported clearly at runtime.
    try:
        from scimarkdown.config import load_config
        from scimarkdown._enhanced_markitdown import EnhancedMarkItDown
    except ImportError as exc:
        print(f"scimarkdown: import error — {exc}", file=sys.stderr)
        return 2

    # Load base config (from file if given, otherwise defaults).
    config_path = Path(args.config) if args.config else None
    sci_config = load_config(config_path)

    # Apply CLI overrides.
    overrides: dict = {}
    if args.latex_style is not None:
        overrides.setdefault("latex", {})["style"] = args.latex_style
    if args.output_dir is not None:
        overrides.setdefault("images", {})["output_dir"] = args.output_dir
    if overrides:
        sci_config = sci_config.with_overrides(overrides)

    # Determine output directory for EnhancedMarkItDown.
    output_dir = Path(args.output_dir) if args.output_dir else Path(".")

    converter = EnhancedMarkItDown(sci_config=sci_config, output_dir=output_dir)

    try:
        result = converter.convert(args.input)
    except Exception as exc:
        print(f"scimarkdown: conversion failed — {exc}", file=sys.stderr)
        return 1

    markdown = result.markdown or ""

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(markdown, encoding="utf-8")
    else:
        sys.stdout.write(markdown)
        if markdown and not markdown.endswith("\n"):
            sys.stdout.write("\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
