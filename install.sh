#!/bin/sh
#
# install.sh — Install (or update) the standalone Diffbot `db` CLI binary.
#
# Detects your platform, downloads the matching binary from the latest GitHub
# release, verifies its SHA256 checksum, and installs it to a bin directory on
# your PATH. Re-running upgrades an existing install in place.
#
# Quick start:
#   curl -fsSL https://raw.githubusercontent.com/diffbot/diffbot-python/main/install.sh | sh
#
# Options (also settable via env var):
#   --version <tag>   DB_VERSION       Release tag to install (default: latest).
#   --bin-dir <dir>   DB_INSTALL_DIR   Install location (default: ~/.local/bin).
#   --repo <owner/repo> DB_REPO        Source repo (default: diffbot/diffbot-python).
#   -h, --help
#
# Supported platforms: linux/darwin on x86_64 (x64/amd64) and aarch64 (arm64).
set -eu

REPO="${DB_REPO:-diffbot/diffbot-python}"
VERSION="${DB_VERSION:-latest}"
BIN_DIR="${DB_INSTALL_DIR:-${HOME}/.local/bin}"
BIN_NAME="db"

err() { printf 'error: %s\n' "$*" >&2; exit 1; }
info() { printf '%s\n' "$*" >&2; }

# True if $1 is a Python console-script shim (pip / uv tool / pipx / venv),
# i.e. a text shebang wrapper pointing at python. Our standalone binary is an
# ELF/Mach-O file and never starts with "#!", so this never matches it.
is_python_console_script() {
  [ -f "$1" ] || return 1
  [ "$(dd if="$1" bs=2 count=1 2>/dev/null)" = "#!" ] || return 1
  head -n1 "$1" 2>/dev/null | grep -q 'python'
}

while [ $# -gt 0 ]; do
  case "$1" in
    --version)   VERSION="$2"; shift 2 ;;
    --version=*) VERSION="${1#*=}"; shift ;;
    --bin-dir)   BIN_DIR="$2"; shift 2 ;;
    --bin-dir=*) BIN_DIR="${1#*=}"; shift ;;
    --repo)      REPO="$2"; shift 2 ;;
    --repo=*)    REPO="${1#*=}"; shift ;;
    -h | --help) sed -n '2,/^[^#]/p' "$0" | sed 's/^# \{0,1\}//;$d'; exit 0 ;;
    *) err "unknown argument: $1 (try --help)" ;;
  esac
done

# --- Detect platform -------------------------------------------------------
os="$(uname -s)"
case "$os" in
  Linux)  os="linux" ;;
  Darwin) os="darwin" ;;
  *) err "unsupported OS: $os (this installer supports Linux and macOS)" ;;
esac

arch="$(uname -m)"
case "$arch" in
  x86_64 | x64 | amd64) arch="x86_64" ;;
  aarch64 | arm64)      arch="aarch64" ;;
  *) err "unsupported architecture: $arch" ;;
esac

asset="${BIN_NAME}-${os}-${arch}"

# --- Pick a download tool --------------------------------------------------
if command -v curl >/dev/null 2>&1; then
  download() { curl -fsSL "$1" -o "$2"; }
  fetch() { curl -fsSL "$1"; }
elif command -v wget >/dev/null 2>&1; then
  download() { wget -qO "$2" "$1"; }
  fetch() { wget -qO - "$1"; }
else
  err "need curl or wget to download the binary"
fi

# --- Resolve the release tag ----------------------------------------------
if [ "$VERSION" = "latest" ]; then
  info "Resolving latest release of ${REPO}..."
  api="https://api.github.com/repos/${REPO}/releases/latest"
  VERSION="$(fetch "$api" | grep -m1 '"tag_name"' \
    | sed -E 's/.*"tag_name"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/')"
  [ -n "$VERSION" ] || err "could not determine the latest release tag from ${api}"
fi

base="https://github.com/${REPO}/releases/download/${VERSION}"
info "Installing ${asset} from ${REPO} ${VERSION}"

# --- Download binary + checksum into a temp dir ----------------------------
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT INT TERM

info "Downloading binary..."
download "${base}/${asset}" "${tmp}/${asset}" \
  || err "failed to download ${base}/${asset} (no build for ${os}/${arch} in ${VERSION}?)"

info "Downloading checksum..."
download "${base}/${asset}.sha256" "${tmp}/${asset}.sha256" \
  || err "failed to download checksum ${base}/${asset}.sha256"

# --- Verify checksum -------------------------------------------------------
info "Verifying SHA256 checksum..."
(
  cd "$tmp"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum -c "${asset}.sha256"
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 -c "${asset}.sha256"
  else
    err "need sha256sum or shasum to verify the download"
  fi
) >/dev/null 2>&1 || err "checksum verification failed — refusing to install"
info "Checksum OK."

# --- Install (atomically), updating any existing install -------------------
mkdir -p "$BIN_DIR"
target="${BIN_DIR}/${BIN_NAME}"

if [ -e "$target" ]; then
  old="$("$target" --version 2>/dev/null || echo "unknown")"
  if is_python_console_script "$target"; then
    info ""
    info "Warning: ${target} looks like a pip/uv-managed 'db' entry point (${old}),"
    info "not a binary installed by this script. Overwriting it replaces that launcher,"
    info "but your Python package manager still treats the file as its own — a later"
    info "'pip install --upgrade' / 'uv tool upgrade' could clobber it again, and an"
    info "uninstall would delete it. To avoid the conflict, remove the managed copy first:"
    info "  pip uninstall diffbot-python    # or: uv tool uninstall diffbot-python"
    info ""
    info "Proceeding to overwrite ${target}..."
  else
    info "Updating existing install at ${target} (${old})"
  fi
else
  info "Installing to ${target}"
fi

chmod +x "${tmp}/${asset}"
# mv within the same filesystem is atomic; fall back to cp for cross-device.
mv -f "${tmp}/${asset}" "$target" 2>/dev/null || cp -f "${tmp}/${asset}" "$target"

new="$("$target" --version 2>/dev/null || echo "$VERSION")"
info ""
info "Installed ${new} -> ${target}"

# --- PATH guidance ---------------------------------------------------------
case ":${PATH}:" in
  *":${BIN_DIR}:"*) ;;
  *)
    info ""
    info "Note: ${BIN_DIR} is not on your PATH. Add it, e.g.:"
    info "  export PATH=\"${BIN_DIR}:\$PATH\""
    ;;
esac

# Warn if a different `db` shadows the one we just installed.
existing="$(command -v "$BIN_NAME" 2>/dev/null || true)"
if [ -n "$existing" ] && [ "$existing" != "$target" ]; then
  info ""
  info "Note: another '${BIN_NAME}' is first on your PATH and will take precedence:"
  info "  ${existing}"
  if is_python_console_script "$existing"; then
    info "  (it looks pip/uv-managed; remove it with 'pip uninstall diffbot-python'"
    info "   or 'uv tool uninstall diffbot-python', or put ${BIN_DIR} earlier on PATH.)"
  fi
fi

info ""
info "Run '${BIN_NAME} --help' to get started."
