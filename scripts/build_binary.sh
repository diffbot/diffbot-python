#!/usr/bin/env bash
#
# build_binary.sh — Build a self-contained `db` CLI binary with PyInstaller and
# emit a matching SHA256 checksum.
#
# Usage:
#   scripts/build_binary.sh [--arch <arch>] [--name <name>] [--output-dir <dir>]
#
# Accepted --arch aliases (normalized for the asset name):
#   x86_64 | x64 | amd64  ->  x86_64
#   aarch64 | arm64       ->  aarch64
#
# PyInstaller does not cross-compile, so --arch must match the host
# architecture; the flag exists only so callers can pass any accepted alias.
# Build on a matching machine (or CI runner) to target a different arch.
#
# Produces, in the output dir (default: ./dist):
#   <name>-<os>-<arch>          the executable
#   <name>-<os>-<arch>.sha256   `sha256sum -c`-compatible checksum
#
# Environment overrides:
#   BUILD_PYTHON   Python version for the isolated build venv (default 3.12).
set -euo pipefail

BIN_NAME="db"
OUTPUT_DIR=""
REQUESTED_ARCH=""
BUILD_PYTHON="${BUILD_PYTHON:-3.12}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENTRY_SCRIPT="${REPO_ROOT}/scripts/db_entry.py"

err() { printf 'error: %s\n' "$*" >&2; exit 1; }
log() { printf '==> %s\n' "$*" >&2; }

normalize_arch() {
  case "$1" in
    x86_64 | x64 | amd64) echo "x86_64" ;;
    aarch64 | arm64)      echo "aarch64" ;;
    *) err "unsupported architecture: $1 (expected x86_64|x64|amd64|aarch64|arm64)" ;;
  esac
}

detect_os() {
  case "$(uname -s)" in
    Linux)  echo "linux" ;;
    Darwin) echo "darwin" ;;
    *) err "unsupported OS: $(uname -s) (expected Linux or Darwin)" ;;
  esac
}

while [ $# -gt 0 ]; do
  case "$1" in
    --arch)         REQUESTED_ARCH="$2"; shift 2 ;;
    --arch=*)       REQUESTED_ARCH="${1#*=}"; shift ;;
    --name)         BIN_NAME="$2"; shift 2 ;;
    --name=*)       BIN_NAME="${1#*=}"; shift ;;
    --output-dir)   OUTPUT_DIR="$2"; shift 2 ;;
    --output-dir=*) OUTPUT_DIR="${1#*=}"; shift ;;
    -h | --help)    sed -n '2,/^[^#]/p' "$0" | sed 's/^# \{0,1\}//;$d'; exit 0 ;;
    *) err "unknown argument: $1 (try --help)" ;;
  esac
done

OS="$(detect_os)"
HOST_ARCH="$(normalize_arch "$(uname -m)")"
if [ -n "$REQUESTED_ARCH" ]; then
  ARCH="$(normalize_arch "$REQUESTED_ARCH")"
else
  ARCH="$HOST_ARCH"
fi

if [ "$ARCH" != "$HOST_ARCH" ]; then
  err "cannot build a '$ARCH' binary on a '$HOST_ARCH' host: PyInstaller does not
     cross-compile. Run this on a '$ARCH' machine or a matching CI runner."
fi

OUTPUT_DIR="${OUTPUT_DIR:-${REPO_ROOT}/dist}"
WORK_DIR="${REPO_ROOT}/build/pyinstaller"
VENV_DIR="${REPO_ROOT}/build/venv"
ASSET="${BIN_NAME}-${OS}-${ARCH}"

mkdir -p "$OUTPUT_DIR" "$WORK_DIR"
log "Building ${ASSET} (os=${OS} arch=${ARCH}, python=${BUILD_PYTHON})"

# --- Isolated build environment --------------------------------------------
# Prefer uv (the project's standard); fall back to stdlib venv + pip.
if command -v uv >/dev/null 2>&1; then
  log "Creating build venv with uv"
  uv venv --python "$BUILD_PYTHON" "$VENV_DIR" >&2
  VENV_PY="${VENV_DIR}/bin/python"
  uv pip install --python "$VENV_PY" pyinstaller "$REPO_ROOT" >&2
else
  log "uv not found; creating build venv with python -m venv"
  python3 -m venv "$VENV_DIR"
  VENV_PY="${VENV_DIR}/bin/python"
  "$VENV_PY" -m pip install --upgrade pip >&2
  "$VENV_PY" -m pip install pyinstaller "$REPO_ROOT" >&2
fi

# --- Freeze the binary -----------------------------------------------------
# --collect-submodules grabs the dynamically-imported cli subcommands; the
# library reads its own version via importlib.metadata, so bundle that too.
log "Running PyInstaller"
"$VENV_PY" -m PyInstaller \
  --onefile \
  --clean \
  --noconfirm \
  --name "$ASSET" \
  --distpath "$OUTPUT_DIR" \
  --workpath "$WORK_DIR" \
  --specpath "$WORK_DIR" \
  --collect-submodules diffbot \
  --copy-metadata diffbot-python \
  "$ENTRY_SCRIPT" >&2

BINARY="${OUTPUT_DIR}/${ASSET}"
[ -f "$BINARY" ] || err "expected binary not found at ${BINARY}"
chmod +x "$BINARY"

# --- Smoke test ------------------------------------------------------------
log "Smoke-testing binary (--version)"
"$BINARY" --version >&2 || err "binary failed to run"

# --- Checksum --------------------------------------------------------------
# Written with a bare filename (no path) so `sha256sum -c` works from the dir.
log "Generating SHA256 checksum"
(
  cd "$OUTPUT_DIR"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$ASSET" > "${ASSET}.sha256"
  else
    shasum -a 256 "$ASSET" > "${ASSET}.sha256"
  fi
)

log "Done"
log "  binary:   ${BINARY}"
log "  checksum: ${BINARY}.sha256"
cat "${BINARY}.sha256" >&2
