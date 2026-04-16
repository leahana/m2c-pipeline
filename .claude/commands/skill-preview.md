---
name: "Skill Preview: Install"
description: Build a timestamped preview skill package and install it locally for testing
---

Build and install a local preview of the m2c-pipeline skill for testing.

Run the following command from the repo root:

```bash
./scripts/dev/preview_install.sh
```

This script will:
1. Run the unit test suite and abort if any test fails
2. Build a timestamped ZIP via `scripts/dev/package_preview.py`
3. Extract the ZIP to `~/.cc-switch/skills/`
4. Create a symlink at `~/.claude/skills/m2c-pipeline-preview-v<version>-<timestamp>`

**Output**: The installed skill name (e.g. `m2c-pipeline-preview-v0.6.1-20260416-102702`).

After installation, open a new Claude Code session and invoke the preview skill by name to test the updated SKILL.md behavior.

**To uninstall all preview builds:**
```bash
rm -rf ~/.cc-switch/skills/m2c-pipeline-preview-*
rm -f  ~/.claude/skills/m2c-pipeline-preview-*
```
