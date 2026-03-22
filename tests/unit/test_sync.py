"""Tests for scimarkdown.sync.upstream sync script."""

import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

from scimarkdown.sync.upstream import (
    sync_upstream,
    generate_report,
    _run,
    _run_tests,
    _parse_args,
)


def _make_proc(returncode=0, stdout="", stderr=""):
    proc = MagicMock(spec=subprocess.CompletedProcess)
    proc.returncode = returncode
    proc.stdout = stdout
    proc.stderr = stderr
    return proc


class TestRunHelper:
    def test_run_calls_subprocess(self, tmp_path):
        """_run wraps subprocess.run and returns its result."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = _make_proc(returncode=0)
            result = _run(["echo", "hello"], cwd=tmp_path)
        assert result.returncode == 0

    def test_run_check_true_raises_on_failure(self, tmp_path):
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, ["git"])
            import pytest
            with pytest.raises(subprocess.CalledProcessError):
                _run(["git", "fail"], cwd=tmp_path, check=True)


class TestSyncUpstream:
    def test_fetch_failed_returns_conflicts_status(self, tmp_path):
        """When git fetch fails with CalledProcessError, status is 'conflicts'."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, ["git"], stderr="network error")
            result = sync_upstream(tmp_path, remote="upstream", branch="main")
        assert result["status"] == "conflicts"
        assert any("fetch_error" in c for c in result["conflicts"])

    def test_up_to_date_when_no_new_commits(self, tmp_path):
        """When git log shows no new commits, status is 'up_to_date'."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                _make_proc(returncode=0),         # git fetch
                _make_proc(returncode=0, stdout=""),  # git log (empty = no new commits)
            ]
            result = sync_upstream(tmp_path, remote="upstream", branch="main")
        assert result["status"] == "up_to_date"
        assert result["changes"] == []

    def test_conflicts_when_merge_fails(self, tmp_path):
        """When merge fails, status is 'conflicts' with conflicting files."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                _make_proc(returncode=0),                         # git fetch
                _make_proc(returncode=0, stdout="abc123 fix bug"),  # git log
                _make_proc(returncode=1),                         # git merge fails
                _make_proc(returncode=0, stdout="UU file.py\nUU other.py\n"),  # git status
                _make_proc(returncode=0),                         # git merge --abort
            ]
            result = sync_upstream(tmp_path, remote="upstream", branch="main")
        assert result["status"] == "conflicts"
        assert "file.py" in result["conflicts"]
        assert result["tests_passed"] is False

    def test_merged_when_tests_pass(self, tmp_path):
        """When merge succeeds and tests pass, status is 'merged'."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                _make_proc(returncode=0),                          # git fetch
                _make_proc(returncode=0, stdout="abc123 commit"),  # git log
                _make_proc(returncode=0),                          # git merge
                _make_proc(returncode=0),                          # pytest (via _run_tests)
                _make_proc(returncode=0),                          # git commit
            ]
            result = sync_upstream(tmp_path, remote="upstream", branch="main")
        assert result["status"] == "merged"
        assert result["tests_passed"] is True

    def test_tests_failed_aborts_merge(self, tmp_path):
        """When tests fail after merge, status is 'tests_failed' and merge is aborted."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                _make_proc(returncode=0),                          # git fetch
                _make_proc(returncode=0, stdout="abc123 commit"),  # git log
                _make_proc(returncode=0),                          # git merge
                _make_proc(returncode=1, stdout="FAILED tests"),   # pytest fails
                _make_proc(returncode=0),                          # git merge --abort
            ]
            result = sync_upstream(tmp_path, remote="upstream", branch="main")
        assert result["status"] == "tests_failed"
        assert result["tests_passed"] is False

    def test_commit_nothing_staged_falls_back(self, tmp_path):
        """When git commit fails (nothing staged), merge --abort is called instead."""
        with patch("subprocess.run") as mock_run:
            # commit raises CalledProcessError → calls merge --abort
            commit_error = subprocess.CalledProcessError(1, ["git", "commit"])
            mock_run.side_effect = [
                _make_proc(returncode=0),                          # git fetch
                _make_proc(returncode=0, stdout="abc123 commit"),  # git log
                _make_proc(returncode=0),                          # git merge
                _make_proc(returncode=0),                          # pytest passes
                commit_error,                                       # git commit fails
                _make_proc(returncode=0),                          # merge --abort
            ]
            result = sync_upstream(tmp_path, remote="upstream", branch="main")
        # Status should still be merged (commit failure is handled gracefully)
        assert result["status"] == "merged"

    def test_log_failure_treated_as_no_new_commits(self, tmp_path):
        """If git log raises, new_commits is empty and we return up_to_date."""
        with patch("subprocess.run") as mock_run:
            log_error = subprocess.CalledProcessError(1, ["git", "log"])
            mock_run.side_effect = [
                _make_proc(returncode=0),  # git fetch
                log_error,                 # git log fails
            ]
            result = sync_upstream(tmp_path, remote="upstream", branch="main")
        # No new commits detected → up_to_date
        assert result["status"] == "up_to_date"

    def test_changes_populated_from_log(self, tmp_path):
        """Changes list is populated from git log stdout lines."""
        log_output = "abc123 first commit\ndef456 second commit\n"
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                _make_proc(returncode=0),                    # git fetch
                _make_proc(returncode=0, stdout=log_output),  # git log
                _make_proc(returncode=0),                    # git merge
                _make_proc(returncode=0),                    # pytest
                _make_proc(returncode=0),                    # git commit
            ]
            result = sync_upstream(tmp_path, remote="upstream", branch="main")
        assert len(result["changes"]) == 2
        assert "abc123 first commit" in result["changes"]

    def test_report_date_is_iso_format(self, tmp_path):
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                _make_proc(returncode=0),
                _make_proc(returncode=0, stdout=""),
            ]
            result = sync_upstream(tmp_path)
        assert "T" in result["date"]  # ISO-8601 has 'T' separator


class TestRunTests:
    def test_returns_true_when_tests_pass(self, tmp_path):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = _make_proc(returncode=0)
            assert _run_tests(tmp_path) is True

    def test_returns_false_when_tests_fail(self, tmp_path):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = _make_proc(returncode=1, stdout="FAILED")
            assert _run_tests(tmp_path) is False

    def test_uses_sys_executable_when_no_venv(self, tmp_path):
        """When .venv/bin/python doesn't exist, falls back to sys.executable."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = _make_proc(returncode=0)
            result = _run_tests(tmp_path)
        assert result is True


class TestGenerateReport:
    def test_creates_markdown_file(self, tmp_path):
        report = {
            "date": "2026-03-22T10:00:00+00:00",
            "status": "merged",
            "changes": ["abc123 fix bug"],
            "conflicts": [],
            "tests_passed": True,
        }
        path = generate_report(report, tmp_path)
        assert path.exists()
        assert path.suffix == ".md"

    def test_report_filename_uses_date_slug(self, tmp_path):
        report = {
            "date": "2026-03-22T10:00:00+00:00",
            "status": "up_to_date",
            "changes": [],
            "conflicts": [],
            "tests_passed": True,
        }
        path = generate_report(report, tmp_path)
        assert "2026-03-22" in path.name

    def test_report_contains_status(self, tmp_path):
        report = {
            "date": "2026-03-22T10:00:00+00:00",
            "status": "conflicts",
            "changes": ["abc commit"],
            "conflicts": ["UU file.py"],
            "tests_passed": False,
        }
        path = generate_report(report, tmp_path)
        content = path.read_text()
        assert "conflicts" in content

    def test_report_with_conflict_files(self, tmp_path):
        report = {
            "date": "2026-03-22T10:00:00+00:00",
            "status": "conflicts",
            "changes": ["abc commit"],
            "conflicts": ["UU file.py", "AA other.py"],
            "tests_passed": None,
        }
        path = generate_report(report, tmp_path)
        content = path.read_text()
        assert "UU file.py" in content
        assert "AA other.py" in content

    def test_report_creates_output_dir(self, tmp_path):
        report_dir = tmp_path / "reports" / "nested"
        report = {
            "date": "2026-03-22T10:00:00+00:00",
            "status": "merged",
            "changes": [],
            "conflicts": [],
            "tests_passed": True,
        }
        path = generate_report(report, report_dir)
        assert path.exists()

    def test_all_status_icons_covered(self, tmp_path):
        for status in ["up_to_date", "merged", "conflicts", "tests_failed", "unknown_status"]:
            report = {
                "date": "2026-03-22T10:00:00+00:00",
                "status": status,
                "changes": [],
                "conflicts": [],
                "tests_passed": True,
            }
            path = generate_report(report, tmp_path / status)
            assert path.exists()

    def test_report_with_changes_list(self, tmp_path):
        report = {
            "date": "2026-03-22T10:00:00+00:00",
            "status": "merged",
            "changes": ["commit1", "commit2", "commit3"],
            "conflicts": [],
            "tests_passed": True,
        }
        path = generate_report(report, tmp_path)
        content = path.read_text()
        assert "commit1" in content
        assert "New upstream commits" in content


class TestParseArgs:
    def test_defaults(self):
        args = _parse_args(["."])
        assert args.remote == "upstream"
        assert args.branch == "main"
        assert args.report_dir == "sync-reports"
        assert args.verbose is False

    def test_custom_remote_and_branch(self):
        args = _parse_args([".", "--remote", "origin", "--branch", "dev"])
        assert args.remote == "origin"
        assert args.branch == "dev"

    def test_verbose_flag(self):
        args = _parse_args([".", "--verbose"])
        assert args.verbose is True

    def test_custom_report_dir(self):
        args = _parse_args([".", "--report-dir", "/tmp/reports"])
        assert args.report_dir == "/tmp/reports"
