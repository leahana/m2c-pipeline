#!/usr/bin/env bash
# Build a timestamped preview skill package and install it locally for testing.
#
# Usage: ./scripts/dev/preview_install.sh [--output-dir DIR]
#
# What it does:
#   1. Runs the test suite (unit tests only, fast)
#   2. Builds a timestamped ZIP via scripts/dev/package_preview.py
#   3. Extracts the ZIP to ~/.cc-switch/skills/
#   4. Creates a symlink at ~/.claude/skills/<preview-name>
#
# The installed skill name will be:
#   m2c-pipeline-preview-v<version>-<YYYYMMDD-HHMMSS>
#
# To uninstall a preview skill:
#   rm -rf ~/.cc-switch/skills/m2c-pipeline-preview-*
#   rm -f  ~/.claude/skills/m2c-pipeline-preview-*

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VENV_PYTHON="${REPO_ROOT}/venv/bin/python"
OUTPUT_DIR="${REPO_ROOT}/dist"

# Parse --output-dir override
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
        *) echo "Unknown argument: $1" >&2; exit 1 ;;
    esac
done

if [[ ! -x "${VENV_PYTHON}" ]]; then
    echo "ERROR: repo-local venv not found at ${VENV_PYTHON}" >&2
    echo "Run: python -m venv venv && ./venv/bin/python -m pip install -r requirements.txt" >&2
    exit 1
fi

CC_SWITCH_SKILLS="${HOME}/.cc-switch/skills"
CLAUDE_SKILLS="${HOME}/.claude/skills"

if [[ ! -d "${CC_SWITCH_SKILLS}" ]]; then
    echo "ERROR: ~/.cc-switch/skills not found — is cc-switch installed?" >&2
    exit 1
fi

echo "==> Running unit tests..."
cd "${REPO_ROOT}"
"${VENV_PYTHON}" -m unittest \
    tests.test_m2c_config \
    tests.test_m2c_cli \
    tests.test_m2c_extractor \
    tests.test_m2c_pipeline \
    tests.test_m2c_storage \
    tests.test_m2c_translator \
    tests.test_skill_spec \
    -v 2>&1 | tail -6
echo ""

echo "==> Building preview package..."
BUILD_OUTPUT="$("${VENV_PYTHON}" -m scripts.dev.package_preview --output-dir "${OUTPUT_DIR}")"
echo "${BUILD_OUTPUT}"

PREVIEW_NAME="$(echo "${BUILD_OUTPUT}" | grep '^Preview skill name:' | sed 's/Preview skill name: //')"
ARCHIVE_PATH="${OUTPUT_DIR}/${PREVIEW_NAME}.zip"

if [[ -z "${PREVIEW_NAME}" ]]; then
    echo "ERROR: Could not parse preview skill name from build output." >&2
    exit 1
fi

echo ""
echo "==> Installing to ${CC_SWITCH_SKILLS}/${PREVIEW_NAME}..."
unzip -q "${ARCHIVE_PATH}" -d "${CC_SWITCH_SKILLS}"

SYMLINK_PATH="${CLAUDE_SKILLS}/${PREVIEW_NAME}"
if [[ -L "${SYMLINK_PATH}" ]]; then
    echo "INFO: Symlink already exists, skipping: ${SYMLINK_PATH}"
else
    ln -s "${CC_SWITCH_SKILLS}/${PREVIEW_NAME}" "${SYMLINK_PATH}"
    echo "==> Symlink created: ${SYMLINK_PATH}"
fi

echo ""
echo "Done. Preview skill installed as:"
echo "  ${PREVIEW_NAME}"
echo ""
echo "To uninstall:"
echo "  rm -rf ${CC_SWITCH_SKILLS}/${PREVIEW_NAME}"
echo "  rm -f  ${SYMLINK_PATH}"
