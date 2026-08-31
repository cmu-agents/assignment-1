---
name: submit-task
description: When the task is complete, take the required steps to submit the solution. DO NOT submit without invoking this skill.
---

When you have finished, you must submit your changes as a git patch, in three separate steps.

# Step 1: Create the patch file
Run `git diff -- path/to/file1 path/to/file2 > patch.txt`, listing only the
source files you modified. Do not commit your changes.

> [!IMPORTANT]
> The patch must contain only the changes to the source files you edited to fix
> the issue. Do not include:
>  - test and reproduction files
> - helper scripts, tests, or tools that you created
> - installation, build, packaging, configuration, or setup scripts, unless they are directly part of the issue you were fixing
> - binary or compiled files

# Step 2: Verify the patch
Read `patch.txt` and confirm it contains only your intended changes, and that its
headers show `--- a/` and `+++ b/` paths.

# Step 3: Submit
Call `send_message` with the message content being a summary of the work.

> [!IMPORTANT]
> - Creating the patch, verifying it, and submitting must be separate steps.
> - If you change patch.txt after verifying it, verify it again before submitting.
> - You cannot continue working on this task in any way after submitting.
