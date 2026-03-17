# Test Fixtures

This directory contains sample documents used by SciMarkdown's integration and
unit tests. All fixtures are small, self-contained files that can be created or
modified without any external tools.

## Files

| File | Description |
|------|-------------|
| `html_mathml.html` | HTML document containing MathML `<math>` tags (quadratic formula and a simple fraction). Used to test MathML detection and pipeline composition. |
| `html_mathjax.html` | HTML document using MathJax-style `\(...\)` and `\[...\]` delimiters inside `<span>` elements. Used to test MathJax heuristic detection. |
| `simple_text_with_math.txt` | Plain-text file containing a variety of Unicode mathematical symbols (∑, ∫, ∈, ℝ, superscripts, subscripts, etc.). Used to test Unicode math detection and the text-format integration pipeline. |

## Subdirectories

| Directory | Description |
|-----------|-------------|
| `expected/` | Reserved for expected output files used in snapshot/golden-file tests. Currently empty. Add `.md` or `.txt` files here when snapshot tests are introduced. |

## Adding new fixtures

- Keep fixtures small (< 100 KB).
- Prefer programmatically generated test data in unit tests (via `io.BytesIO`,
  `PIL.Image.new`, etc.) over binary fixture files.
- Use this directory only for fixtures that represent realistic document samples
  needed across multiple test modules, or for formats that are hard to generate
  in code (e.g., real EPUB structures).
