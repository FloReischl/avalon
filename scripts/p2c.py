import sys
# import os
from pathlib import Path
import subprocess
# from base.prompt2code import parse_input_script, simulate_patch, write_simulated_files, describe_result, PatchError

# # Gesamten Inhalt aus stdin lesen
content = sys.stdin.read()

patch_file = Path("~/dev/avalo/data/patch.p2c").expanduser()
patch_file.write_text(content)

result = subprocess.run(
            [
                "python3", str(Path("~/dev/avalo/scripts/base/prompt2code.py").expanduser()), 
                "--input-script", str(patch_file),
                "--target-dir", "~/dev/avalo",
            ],
capture_output=True,
text=True
)

err = result.stderr
print(err)
out = result.stdout
print(out)

# def main(input_script: Path, target_dir: Path):
#     try:
#         changes = parse_input_script(
#             input_script,
#             target_dir,
#         )

#         # Phase 1:
#         # Parse, validate and simulate the
#         # complete patch in memory.
#         simulated_files = (
#             simulate_patch(
#                 changes
#             )
#         )

#         # Phase 2:
#         # Write each affected file at most once.
#         write_simulated_files(
#             simulated_files
#         )

#     except (
#         PatchError,
#         OSError,
#         UnicodeError,
#     ) as exc:
#         print(
#             f"❌ Patch aborted: {exc}",
#             file=sys.stderr,
#         )
#         return 1

#     for file in simulated_files:
#         print(
#             describe_result(
#                 file
#             )
#         )

#     print(
#         (
#             "\n🎉 Done! "
#             f"{len(simulated_files)} "
#             "file(s) processed successfully."
#         )
#     )
