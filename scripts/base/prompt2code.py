import sys
from argparse import ArgumentParser
from dataclasses import dataclass
from pathlib import Path


MODE_STRING_REPLACE = "string-replace"
MODE_STRING_REMOVE = "string-remove"
MODE_FILE_CREATE = "file-create"
MODE_FILE_DELETE = "file-delete"

SUPPORTED_MODES = {
    MODE_STRING_REPLACE,
    MODE_STRING_REMOVE,
    MODE_FILE_CREATE,
    MODE_FILE_DELETE,
}

MARKER_OLD = "p2c-old"
MARKER_NEW = "p2c-new"
MARKER_NEXT_CHANGE = "p2c-next-change"
SELECTOR_POSITION_PREFIX = "p2c-position: "
SELECTOR_COUNT_PREFIX = "p2c-count: "

RESERVED_PAYLOAD_MARKERS = {
    MARKER_OLD,
    MARKER_NEW,
}


class PatchError(Exception):
    """Raised when a patch is invalid or cannot be applied safely."""


@dataclass(frozen=True, slots=True)
class Change:
    index: int
    relative_path: str
    path: Path
    mode: str
    old: str | None = None
    new: str | None = None
    content: str | None = None
    position: int | None = None
    count: int | None = None


@dataclass(slots=True)
class SimulatedFile:
    relative_path: str
    path: Path
    original_exists: bool
    original_content: str | None
    final_exists: bool
    final_content: str | None


def parse_args():
    parser = ArgumentParser(
        description=(
            "Apply deterministic Prompt2Code file and string operations."
        )
    )
    parser.add_argument(
        "--input-script",
        required=True,
        help="Path to the Prompt2Code patch script.",
    )
    parser.add_argument(
        "--target-dir",
        required=True,
        help="Root directory against which patch paths are resolved.",
    )
    return parser.parse_args()


def line_content(raw_line: str) -> str:
    if raw_line.endswith("\n"):
        return raw_line[:-1]

    return raw_line


def error(
    change_index: int,
    reason: str,
    relative_path: str | None = None,
    old: str | None = None,
) -> PatchError:
    if relative_path is None:
        message = f"change #{change_index}: {reason}"
    else:
        message = (
            f"[{relative_path}] change #{change_index}: {reason}"
        )

    if old is not None:
        message += f"\n\np2c-old:\n{old}"

    return PatchError(message)


def resolve_target_path(
    target_dir: Path,
    raw_path: str,
    change_index: int,
) -> Path:
    if raw_path == "":
        raise error(
            change_index,
            "file path must not be empty",
        )

    if raw_path != raw_path.strip():
        raise error(
            change_index,
            "file path must not have leading or trailing whitespace",
            raw_path,
        )

    relative_path = Path(raw_path)

    if relative_path.is_absolute():
        raise error(
            change_index,
            "absolute paths are not allowed",
            raw_path,
        )

    target_path = (
        target_dir
        / relative_path
    ).resolve()

    try:
        target_path.relative_to(target_dir)
    except ValueError as exc:
        raise error(
            change_index,
            "path escapes target directory",
            raw_path,
        ) from exc

    return target_path


def payload_from_lines(
    raw_lines: list[str],
    terminated_by_marker: bool,
) -> str:
    payload = "".join(raw_lines)

    # The LF immediately before a following marker separates the
    # payload from that marker. Additional blank lines remain part
    # of the payload.
    if (
        terminated_by_marker
        and payload.endswith("\n")
    ):
        payload = payload[:-1]

    return payload


def reject_reserved_markers(
    raw_lines: list[str],
    change_index: int,
    relative_path: str,
):
    for raw_line in raw_lines:
        marker = line_content(raw_line)

        if marker in RESERVED_PAYLOAD_MARKERS:
            raise error(
                change_index,
                (
                    "unexpected reserved marker "
                    f"'{marker}' in payload"
                ),
                relative_path,
            )


def require_payload(
    payload: str,
    marker: str,
    change_index: int,
    relative_path: str,
):
    if payload == "":
        raise error(
            change_index,
            f"{marker} payload must not be empty",
            relative_path,
        )


def parse_match_selector(
    raw_lines: list[str],
    start_index: int,
    change_index: int,
    relative_path: str,
) -> tuple[int | None, int | None, int]:
    position = None
    count = None
    index = start_index

    while index < len(raw_lines):
        line = line_content(raw_lines[index])

        if line.startswith(SELECTOR_POSITION_PREFIX):
            if position is not None:
                raise error(
                    change_index,
                    "p2c-position may only be specified once",
                    relative_path,
                )

            value = line[len(SELECTOR_POSITION_PREFIX):]

            if not value.isdigit() or int(value) < 1:
                raise error(
                    change_index,
                    "p2c-position must be a positive 1-based integer",
                    relative_path,
                )

            position = int(value)
            index += 1
            continue

        if line.startswith(SELECTOR_COUNT_PREFIX):
            if count is not None:
                raise error(
                    change_index,
                    "p2c-count may only be specified once",
                    relative_path,
                )

            value = line[len(SELECTOR_COUNT_PREFIX):]

            if not value.isdigit() or int(value) < 1:
                raise error(
                    change_index,
                    "p2c-count must be a positive integer",
                    relative_path,
                )

            count = int(value)
            index += 1
            continue

        break

    if position is not None and count is not None:
        raise error(
            change_index,
            "p2c-position and p2c-count are mutually exclusive",
            relative_path,
        )

    return position, count, index


def split_change_blocks(
    raw_lines: list[str],
) -> list[tuple[list[str], bool]]:
    blocks: list[
        tuple[
            list[str],
            bool,
        ]
    ] = []

    current: list[str] = []

    for raw_line in raw_lines:
        if (
            line_content(raw_line)
            == MARKER_NEXT_CHANGE
        ):
            blocks.append(
                (
                    current,
                    True,
                )
            )
            current = []
        else:
            current.append(raw_line)

    blocks.append(
        (
            current,
            False,
        )
    )

    return blocks


def parse_change_block(
    raw_lines: list[str],
    terminated_by_next_change: bool,
    target_dir: Path,
    change_index: int,
) -> Change:
    if not raw_lines:
        raise error(
            change_index,
            "change block must not be empty",
        )

    if len(raw_lines) < 2:
        raise error(
            change_index,
            (
                "change must contain file path on line 1 "
                "and mode on line 2"
            ),
        )

    relative_path = line_content(
        raw_lines[0]
    )

    path = resolve_target_path(
        target_dir,
        relative_path,
        change_index,
    )

    mode = line_content(
        raw_lines[1]
    )

    if mode == "":
        raise error(
            change_index,
            "mode on line 2 must not be empty",
            relative_path,
        )

    if mode not in SUPPORTED_MODES:
        supported = ", ".join(
            sorted(
                SUPPORTED_MODES
            )
        )

        raise error(
            change_index,
            (
                f"unsupported mode '{mode}'; "
                f"supported modes: {supported}"
            ),
            relative_path,
        )

    if mode == MODE_FILE_DELETE:
        if len(raw_lines) != 2:
            raise error(
                change_index,
                (
                    "file-delete does not allow "
                    "payload or additional lines"
                ),
                relative_path,
            )

        return Change(
            index=change_index,
            relative_path=relative_path,
            path=path,
            mode=mode,
        )

    if len(raw_lines) < 3:
        if mode == MODE_FILE_CREATE:
            required_marker = MARKER_NEW
        else:
            required_marker = MARKER_OLD

        raise error(
            change_index,
            (
                f"{mode} requires marker "
                f"'{required_marker}' on line 3"
            ),
            relative_path,
        )

    first_marker = line_content(
        raw_lines[2]
    )

    if mode == MODE_FILE_CREATE:
        if first_marker != MARKER_NEW:
            raise error(
                change_index,
                (
                    "file-create requires marker "
                    f"'{MARKER_NEW}' on line 3"
                ),
                relative_path,
            )

        payload_lines = raw_lines[3:]

        reject_reserved_markers(
            payload_lines,
            change_index,
            relative_path,
        )

        content = payload_from_lines(
            payload_lines,
            terminated_by_next_change,
        )

        require_payload(
            content,
            MARKER_NEW,
            change_index,
            relative_path,
        )

        return Change(
            index=change_index,
            relative_path=relative_path,
            path=path,
            mode=mode,
            content=content,
        )

    position, count, marker_index = parse_match_selector(
        raw_lines,
        2,
        change_index,
        relative_path,
    )

    if marker_index >= len(raw_lines):
        raise error(
            change_index,
            f"{mode} requires marker '{MARKER_OLD}'",
            relative_path,
        )

    first_marker = line_content(
        raw_lines[marker_index]
    )

    if first_marker != MARKER_OLD:
        raise error(
            change_index,
            (
                f"{mode} requires marker "
                f"'{MARKER_OLD}' after optional selector"
            ),
            relative_path,
        )

    payload_start_index = marker_index + 1

    if mode == MODE_STRING_REMOVE:
        payload_lines = raw_lines[payload_start_index:]

        reject_reserved_markers(
            payload_lines,
            change_index,
            relative_path,
        )

        old = payload_from_lines(
            payload_lines,
            terminated_by_next_change,
        )

        require_payload(
            old,
            MARKER_OLD,
            change_index,
            relative_path,
        )

        return Change(
            index=change_index,
            relative_path=relative_path,
            path=path,
            mode=mode,
            old=old,
            position=position,
            count=count,
        )

    new_marker_index = None

    for index in range(
        payload_start_index,
        len(raw_lines),
    ):
        marker = line_content(
            raw_lines[index]
        )

        if marker == MARKER_NEW:
            new_marker_index = index
            break

        if marker == MARKER_OLD:
            raise error(
                change_index,
                (
                    "unexpected reserved marker "
                    f"'{MARKER_OLD}' "
                    "in p2c-old payload"
                ),
                relative_path,
            )

    if new_marker_index is None:
        raise error(
            change_index,
            (
                "string-replace requires marker "
                f"'{MARKER_NEW}'"
            ),
            relative_path,
        )

    old = payload_from_lines(
        raw_lines[
            payload_start_index:new_marker_index
        ],
        terminated_by_marker=True,
    )

    require_payload(
        old,
        MARKER_OLD,
        change_index,
        relative_path,
    )

    new_lines = raw_lines[
        new_marker_index + 1:
    ]

    reject_reserved_markers(
        new_lines,
        change_index,
        relative_path,
    )

    new = payload_from_lines(
        new_lines,
        terminated_by_next_change,
    )

    require_payload(
        new,
        MARKER_NEW,
        change_index,
        relative_path,
    )

    return Change(
        index=change_index,
        relative_path=relative_path,
        path=path,
        mode=mode,
        old=old,
        new=new,
        position=position,
        count=count,
    )


def parse_input_script(
    input_script: Path,
    target_dir: Path,
) -> list[Change]:
    if not input_script.exists():
        raise PatchError(
            f"input script not found: '{input_script}'"
        )

    if not input_script.is_file():
        raise PatchError(
            f"input script is not a file: '{input_script}'"
        )

    try:
        document = (
            input_script
            .read_bytes()
            .decode("utf-8")
        )
    except UnicodeDecodeError as exc:
        raise PatchError(
            (
                "input script is not valid UTF-8: "
                f"'{input_script}'"
            )
        ) from exc

    if document == "":
        raise PatchError(
            "input script is empty"
        )

    if "\r" in document:
        raise PatchError(
            (
                "input script must use "
                "LF ('\\n') line endings only"
            )
        )

    raw_lines = document.splitlines(
        keepends=True
    )

    blocks = split_change_blocks(
        raw_lines
    )

    if not blocks[0][0]:
        raise error(
            1,
            (
                "patch must not start with "
                "p2c-next-change"
            ),
        )

    if not blocks[-1][0]:
        raise error(
            len(blocks),
            (
                "patch must not end with "
                "p2c-next-change"
            ),
        )

    changes: list[Change] = []

    for (
        change_index,
        (
            raw_block,
            terminated,
        ),
    ) in enumerate(
        blocks,
        start=1,
    ):
        if not raw_block:
            raise error(
                change_index,
                (
                    "empty change block between "
                    "p2c-next-change markers"
                ),
            )

        changes.append(
            parse_change_block(
                raw_lines=raw_block,
                terminated_by_next_change=terminated,
                target_dir=target_dir,
                change_index=change_index,
            )
        )

    return changes


def read_utf8_file(
    path: Path,
) -> str:
    return (
        path
        .read_bytes()
        .decode("utf-8")
    )


def apply_string_change(
    content: str,
    change: Change,
    replacement: str,
) -> str:
    assert change.old is not None

    match_count = content.count(
        change.old
    )

    if change.position is not None:
        if match_count < change.position:
            raise error(
                change.index,
                (
                    f"{change.mode} expected p2c-old "
                    f"position {change.position} to exist, "
                    f"found {match_count} match(es)"
                ),
                change.relative_path,
                old=change.old,
            )

        start = 0

        for _ in range(change.position):
            start = content.find(
                change.old,
                start,
            )

            assert start >= 0

            if _ + 1 < change.position:
                start += len(change.old)

        end = start + len(change.old)

        return (
            content[:start]
            + replacement
            + content[end:]
        )

    if change.count is not None:
        if match_count != change.count:
            raise error(
                change.index,
                (
                    f"{change.mode} expected p2c-old "
                    f"to occur exactly {change.count} time(s), "
                    f"found {match_count}"
                ),
                change.relative_path,
                old=change.old,
            )

        return content.replace(
            change.old,
            replacement,
            change.count,
        )

    if match_count != 1:
        raise error(
            change.index,
            (
                f"{change.mode} expected p2c-old "
                "to occur exactly once, "
                f"found {match_count}"
            ),
            change.relative_path,
            old=change.old,
        )

    return content.replace(
        change.old,
        replacement,
        1,
    )


def load_simulated_file(
    change: Change,
) -> SimulatedFile:
    path = change.path
    original_exists = path.exists()

    if original_exists:
        if not path.is_file():
            raise error(
                change.index,
                (
                    "target exists but is "
                    "not a regular file"
                ),
                change.relative_path,
            )

        try:
            original_content = (
                read_utf8_file(
                    path
                )
            )
        except UnicodeDecodeError as exc:
            raise error(
                change.index,
                (
                    "target file is "
                    "not valid UTF-8"
                ),
                change.relative_path,
            ) from exc

        final_content = (
            original_content
        )

    else:
        original_content = None
        final_content = None

    return SimulatedFile(
        relative_path=change.relative_path,
        path=path,
        original_exists=original_exists,
        original_content=original_content,
        final_exists=original_exists,
        final_content=final_content,
    )


def apply_change_in_memory(
    file: SimulatedFile,
    change: Change,
):
    if change.mode == MODE_FILE_CREATE:
        if file.final_exists:
            raise error(
                change.index,
                (
                    "file-create failed: "
                    "file already exists"
                ),
                change.relative_path,
            )

        assert change.content is not None

        file.final_exists = True
        file.final_content = (
            change.content
        )

        return

    if change.mode == MODE_FILE_DELETE:
        if not file.final_exists:
            raise error(
                change.index,
                (
                    "file-delete failed: "
                    "file does not exist"
                ),
                change.relative_path,
            )

        file.final_exists = False
        file.final_content = None

        return

    if (
        not file.final_exists
        or file.final_content is None
    ):
        raise error(
            change.index,
            (
                f"{change.mode} failed: "
                "file does not exist"
            ),
            change.relative_path,
        )

    if change.mode == MODE_STRING_REPLACE:
        assert change.old is not None
        assert change.new is not None

        file.final_content = apply_string_change(
            file.final_content,
            change,
            change.new,
        )

        return

    if change.mode == MODE_STRING_REMOVE:
        assert change.old is not None

        file.final_content = apply_string_change(
            file.final_content,
            change,
            "",
        )

        return

    raise error(
        change.index,
        f"unhandled mode '{change.mode}'",
        change.relative_path,
    )


def simulate_patch(
    changes: list[Change],
) -> list[SimulatedFile]:
    files_by_path: dict[
        Path,
        SimulatedFile,
    ] = {}

    file_order: list[Path] = []

    for change in changes:
        file = files_by_path.get(
            change.path
        )

        if file is None:
            file = load_simulated_file(
                change
            )

            files_by_path[
                change.path
            ] = file

            file_order.append(
                change.path
            )

        apply_change_in_memory(
            file,
            change,
        )

    return [
        files_by_path[path]
        for path in file_order
    ]


def write_simulated_files(
    files: list[SimulatedFile],
):
    # Reached only after the complete patch was
    # simulated successfully.
    #
    # There is deliberately no rollback if an
    # I/O error occurs during this phase.

    for file in files:
        if file.final_exists:
            if file.final_content is None:
                raise PatchError(
                    (
                        f"[{file.relative_path}] "
                        "internal error: "
                        "no final content for "
                        "existing file"
                    )
                )

            file.path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            file.path.write_bytes(
                file.final_content.encode(
                    "utf-8"
                )
            )

        elif file.path.exists():
            file.path.unlink()


def describe_result(
    file: SimulatedFile,
) -> str:
    path = file.relative_path

    if (
        not file.original_exists
        and file.final_exists
    ):
        return (
            f"✅ Created: {path}"
        )

    if (
        file.original_exists
        and not file.final_exists
    ):
        return (
            f"✅ Deleted: {path}"
        )

    if (
        file.original_exists
        and file.final_exists
    ):
        if (
            file.original_content
            == file.final_content
        ):
            return (
                f"➖ Unchanged: {path}"
            )

        return (
            f"✅ Modified: {path}"
        )

    return (
        f"➖ No file created: {path}"
    )


def main():
    args = parse_args()

    input_script = (
        Path(
            args.input_script
        )
        .expanduser()
        .resolve()
    )

    target_dir = (
        Path(
            args.target_dir
        )
        .expanduser()
        .resolve()
    )

    if not target_dir.exists():
        print(
            (
                "❌ Error: target directory "
                "does not exist: "
                f"'{target_dir}'"
            ),
            file=sys.stderr,
        )
        return 1

    if not target_dir.is_dir():
        print(
            (
                "❌ Error: target directory "
                "is not a directory: "
                f"'{target_dir}'"
            ),
            file=sys.stderr,
        )
        return 1

    try:
        changes = parse_input_script(
            input_script,
            target_dir,
        )

        # Phase 1:
        # Parse, validate and simulate the
        # complete patch in memory.
        simulated_files = (
            simulate_patch(
                changes
            )
        )

        # Phase 2:
        # Write each affected file at most once.
        write_simulated_files(
            simulated_files
        )

    except (
        PatchError,
        OSError,
        UnicodeError,
    ) as exc:
        print(
            f"❌ Patch aborted: {exc}",
            file=sys.stderr,
        )
        return 1

    for file in simulated_files:
        print(
            describe_result(
                file
            )
        )

    print(
        (
            "\n🎉 Done! "
            f"{len(simulated_files)} "
            "file(s) processed successfully."
        )
    )

    return 0


if __name__ == "__main__":
    sys.exit(
        main()
    )