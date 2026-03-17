"""Upstream sync script for keeping SciMarkdown up-to-date with microsoft/markitdown."""

import argparse
import logging
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def _run(cmd: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    """Run a subprocess command and return the result."""
    logger.debug("Running: %s (cwd=%s)", " ".join(cmd), cwd)
    return subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=check,
    )


def sync_upstream(
    repo_dir: Path,
    remote: str = "upstream",
    branch: str = "main",
) -> dict:
    """Synchronise the local fork with the upstream remote.

    Steps:
    1. Fetch the upstream remote.
    2. Check whether new commits exist on upstream/<branch>.
    3. Attempt a merge (--no-commit --no-ff) of upstream/<branch>.
    4. Run the test suite.
    5. Commit the merge on success, or abort and revert on failure.

    Args:
        repo_dir: Absolute path to the repository root.
        remote: Name of the upstream git remote (default: "upstream").
        branch: Branch to merge from (default: "main").

    Returns:
        A dict with keys:
            date       – ISO-8601 timestamp (UTC) of the sync run.
            status     – "up_to_date" | "merged" | "conflicts" | "tests_failed".
            changes    – list of commit subject lines pulled from upstream.
            conflicts  – list of conflicting file paths (if any).
            tests_passed – bool, True if tests passed (or were not needed).
    """
    repo_dir = Path(repo_dir)
    report: dict = {
        "date": datetime.now(timezone.utc).isoformat(),
        "status": "up_to_date",
        "changes": [],
        "conflicts": [],
        "tests_passed": True,
    }

    # 1. Fetch upstream
    try:
        _run(["git", "fetch", remote], cwd=repo_dir)
    except subprocess.CalledProcessError as exc:
        logger.error("git fetch failed: %s", exc.stderr)
        report["status"] = "conflicts"
        report["conflicts"] = [f"fetch_error: {exc.stderr.strip()}"]
        return report

    # 2. Identify new commits
    ref = f"{remote}/{branch}"
    try:
        log_result = _run(
            ["git", "log", "HEAD.." + ref, "--oneline", "--no-decorate"],
            cwd=repo_dir,
        )
        new_commits = [line.strip() for line in log_result.stdout.splitlines() if line.strip()]
    except subprocess.CalledProcessError as exc:
        logger.error("git log failed: %s", exc.stderr)
        new_commits = []

    report["changes"] = new_commits

    if not new_commits:
        logger.info("Already up-to-date with %s.", ref)
        return report

    # 3. Attempt merge (no commit so we can run tests first)
    merge_result = _run(
        ["git", "merge", "--no-commit", "--no-ff", ref],
        cwd=repo_dir,
        check=False,
    )

    if merge_result.returncode != 0:
        # Detect conflicting files
        status_result = _run(["git", "status", "--porcelain"], cwd=repo_dir, check=False)
        conflicts = [
            line[3:].strip()
            for line in status_result.stdout.splitlines()
            if line.startswith("UU") or line.startswith("AA") or line.startswith("DD")
        ]
        report["status"] = "conflicts"
        report["conflicts"] = conflicts
        report["tests_passed"] = False

        # Abort the merge
        _run(["git", "merge", "--abort"], cwd=repo_dir, check=False)
        return report

    # 4. Run tests
    tests_passed = _run_tests(repo_dir)
    report["tests_passed"] = tests_passed

    if tests_passed:
        # 5a. Commit the successful merge
        try:
            _run(
                [
                    "git",
                    "commit",
                    "--no-edit",
                    "-m",
                    f"chore: merge upstream {remote}/{branch} ({datetime.now(timezone.utc).date()})",
                ],
                cwd=repo_dir,
            )
        except subprocess.CalledProcessError:
            # Nothing staged (already up-to-date at merge level)
            _run(["git", "merge", "--abort"], cwd=repo_dir, check=False)

        report["status"] = "merged"
    else:
        # 5b. Revert – abort the staged merge
        report["status"] = "tests_failed"
        _run(["git", "merge", "--abort"], cwd=repo_dir, check=False)

    return report


def _run_tests(repo_dir: Path) -> bool:
    """Run the project test suite and return True if all tests pass."""
    python = repo_dir / ".venv" / "bin" / "python"
    if not python.exists():
        python = Path(sys.executable)

    result = subprocess.run(
        [str(python), "-m", "pytest", "packages/scimarkdown/tests", "-q", "--tb=short"],
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        logger.warning("Tests failed:\n%s", result.stdout[-2000:])
    return result.returncode == 0


def generate_report(report: dict, output_dir: Path) -> Path:
    """Write a Markdown sync report and return its path.

    Args:
        report: The dict returned by :func:`sync_upstream`.
        output_dir: Directory in which to write the report file.

    Returns:
        Path to the written Markdown file.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    date_slug = report["date"][:10]
    out_path = output_dir / f"sync-report-{date_slug}.md"

    status_icon = {
        "up_to_date": "green_circle",
        "merged": "large_green_circle",
        "conflicts": "red_circle",
        "tests_failed": "orange_circle",
    }.get(report["status"], "white_circle")

    lines = [
        f"# Upstream Sync Report — {date_slug}",
        "",
        f"**Status:** :{status_icon}: `{report['status']}`  ",
        f"**Date:** {report['date']}  ",
        f"**Tests passed:** {'yes' if report['tests_passed'] else 'no'}",
        "",
    ]

    if report["changes"]:
        lines += ["## New upstream commits", ""]
        for commit in report["changes"]:
            lines.append(f"- {commit}")
        lines.append("")

    if report["conflicts"]:
        lines += ["## Conflicts / Errors", ""]
        for conflict in report["conflicts"]:
            lines.append(f"- `{conflict}`")
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Report written to %s", out_path)
    return out_path


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m scimarkdown.sync.upstream",
        description="Sync the SciMarkdown fork with the upstream microsoft/markitdown repo.",
    )
    parser.add_argument(
        "repo_dir",
        nargs="?",
        default=".",
        help="Path to the repository root (default: current directory).",
    )
    parser.add_argument(
        "--remote",
        default="upstream",
        help="Name of the upstream git remote (default: upstream).",
    )
    parser.add_argument(
        "--branch",
        default="main",
        help="Upstream branch to merge (default: main).",
    )
    parser.add_argument(
        "--report-dir",
        default="sync-reports",
        help="Directory for Markdown reports (default: sync-reports).",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    report = sync_upstream(
        repo_dir=Path(args.repo_dir),
        remote=args.remote,
        branch=args.branch,
    )

    report_path = generate_report(report, output_dir=Path(args.report_dir))

    print(f"Status  : {report['status']}")
    print(f"Changes : {len(report['changes'])} new upstream commit(s)")
    print(f"Report  : {report_path}")

    if report["status"] in ("conflicts", "tests_failed"):
        sys.exit(1)
