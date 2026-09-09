import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).with_name("prompt2code.py")
TEST_DATA = Path(__file__).with_name("test-data")


def run_patch(patch_name: str, target_dir: Path):
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--input-script",
            str(TEST_DATA / patch_name),
            "--target-dir",
            str(target_dir),
        ],
        capture_output=True,
        text=True,
    )


def run_patch_text(patch: str, target_dir: Path):
    patch_file = target_dir / "inline.p2c"
    patch_file.write_text(
        patch,
        encoding="utf-8",
    )

    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--input-script",
            str(patch_file),
            "--target-dir",
            str(target_dir),
        ],
        capture_output=True,
        text=True,
    )


def test_string_replace_multiline(tmp_path):
    target = tmp_path / "app.py"
    target.write_text(
        "def foo():\n"
        "    return 1\n"
        "\n"
        "print(foo())\n",
        encoding="utf-8",
    )

    result = run_patch(
        "string-replace.p2c",
        tmp_path,
    )

    assert result.returncode == 0, result.stderr
    assert target.read_text(encoding="utf-8") == (
        "def foo():\n"
        "    return 2\n"
        "\n"
        "print(foo())\n"
    )


def test_string_remove(tmp_path):
    target = tmp_path / "app.py"
    target.write_text(
        "before\n"
        "remove me\n"
        "after\n",
        encoding="utf-8",
    )

    result = run_patch(
        "string-remove.p2c",
        tmp_path,
    )

    assert result.returncode == 0, result.stderr
    assert target.read_text(encoding="utf-8") == (
        "before\n"
        "after\n"
    )


def test_file_create_and_delete(tmp_path):
    obsolete = tmp_path / "obsolete.txt"
    obsolete.write_text(
        "old\n",
        encoding="utf-8",
    )

    result = run_patch(
        "file-create-delete.p2c",
        tmp_path,
    )

    assert result.returncode == 0, result.stderr

    created = tmp_path / "nested" / "new.txt"

    assert created.read_text(encoding="utf-8") == "hello"
    assert not obsolete.exists()

    assert "✅ Created: nested/new.txt" in result.stdout
    assert "✅ Deleted: obsolete.txt" in result.stdout


def test_multiple_changes_same_file_are_sequential(tmp_path):
    target = tmp_path / "value.txt"
    target.write_text(
        "alpha\n",
        encoding="utf-8",
    )

    result = run_patch(
        "sequential.p2c",
        tmp_path,
    )

    assert result.returncode == 0, result.stderr
    assert target.read_text(encoding="utf-8") == "gamma\n"

    assert result.stdout.count(
        "✅ Modified: value.txt"
    ) == 1


def test_later_failure_writes_nothing(tmp_path):
    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"

    first.write_text(
        "before\n",
        encoding="utf-8",
    )
    second.write_text(
        "something else\n",
        encoding="utf-8",
    )

    result = run_patch(
        "atomic-failure.p2c",
        tmp_path,
    )

    assert result.returncode == 1

    assert first.read_text(encoding="utf-8") == "before\n"
    assert second.read_text(encoding="utf-8") == "something else\n"

    assert "change #2" in result.stderr
    assert "found 0" in result.stderr
    assert "p2c-old:\nmissing value" in result.stderr


def test_path_must_not_escape_target_dir(tmp_path):
    target_dir = tmp_path / "target"
    target_dir.mkdir()

    escaped = tmp_path / "escaped.txt"

    result = run_patch(
        "sandbox-escape.p2c",
        target_dir,
    )

    assert result.returncode == 1
    assert "path escapes target directory" in result.stderr
    assert not escaped.exists()


def test_string_replace_position_selects_nth_match(tmp_path):
    target = tmp_path / "value.txt"
    target.write_text(
        "same\n"
        "same\n"
        "same\n",
        encoding="utf-8",
    )

    result = run_patch_text(
        "value.txt\n"
        "string-replace\n"
        "p2c-position: 2\n"
        "p2c-old\n"
        "same\n"
        "p2c-new\n"
        "changed",
        tmp_path,
    )

    assert result.returncode == 0, result.stderr
    assert target.read_text(encoding="utf-8") == (
        "same\n"
        "changed\n"
        "same\n"
    )


def test_string_remove_count_removes_all_expected_matches(tmp_path):
    target = tmp_path / "value.txt"
    target.write_text(
        "x\n"
        "keep\n"
        "x\n"
        "x\n",
        encoding="utf-8",
    )

    result = run_patch_text(
        "value.txt\n"
        "string-remove\n"
        "p2c-count: 3\n"
        "p2c-old\n"
        "x\n",
        tmp_path,
    )

    assert result.returncode == 0, result.stderr
    assert target.read_text(encoding="utf-8") == "keep\n"


def test_string_count_requires_exact_match_count(tmp_path):
    target = tmp_path / "value.txt"
    target.write_text(
        "x\n"
        "x\n",
        encoding="utf-8",
    )

    result = run_patch_text(
        "value.txt\n"
        "string-remove\n"
        "p2c-count: 3\n"
        "p2c-old\n"
        "x\n",
        tmp_path,
    )

    assert result.returncode == 1
    assert "expected p2c-old to occur exactly 3 time(s)" in result.stderr
    assert "found 2" in result.stderr
    assert target.read_text(encoding="utf-8") == (
        "x\n"
        "x\n"
    )


def test_position_and_count_are_mutually_exclusive(tmp_path):
    target = tmp_path / "value.txt"
    target.write_text(
        "x\n"
        "x\n",
        encoding="utf-8",
    )

    result = run_patch_text(
        "value.txt\n"
        "string-remove\n"
        "p2c-position: 1\n"
        "p2c-count: 2\n"
        "p2c-old\n"
        "x\n",
        tmp_path,
    )

    assert result.returncode == 1
    assert (
        "p2c-position and p2c-count are mutually exclusive"
        in result.stderr
    )
    assert target.read_text(encoding="utf-8") == (
        "x\n"
        "x\n"
    )


def test_default_string_match_still_requires_exactly_one(tmp_path):
    target = tmp_path / "value.txt"
    target.write_text(
        "x\n"
        "x\n",
        encoding="utf-8",
    )

    result = run_patch_text(
        "value.txt\n"
        "string-remove\n"
        "p2c-old\n"
        "x\n",
        tmp_path,
    )

    assert result.returncode == 1
    assert "expected p2c-old to occur exactly once" in result.stderr
    assert "found 2" in result.stderr
