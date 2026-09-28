.PHONY: test test-live build build-legacy release-legacy release-test-legacy clean bump-patch bump-minor bump-major set-token-pypi set-token-testpypi release-test release _release-test _release verify-release-test verify-release

test:
	uv run --extra dev pytest

test-live:
	uv run --extra dev pytest -m live

clean:
	rm -rf dist build *.egg-info

# Distribution to publish/verify. The legacy targets override this with
# PKG=diffbot-python to ship the final diffbot-python release.
PKG ?= diffbot
PYPROJECT ?= pyproject.toml

build: clean
	uv build

# Build the final diffbot-python release into dist/: today's src/diffbot under
# the old name (see legacy/diffbot-python). Staged in build/ because the package
# code lives outside that directory.
build-legacy: clean
	mkdir -p build
	cp -R legacy/diffbot-python build/legacy
	cp -R src build/legacy/src
	find build/legacy -name __pycache__ -prune -exec rm -rf {} +
	uv build build/legacy --out-dir dist

# Version bumps: edits pyproject.toml in place and prints old => new.
bump-patch:
	uv version --bump patch

bump-minor:
	uv version --bump minor

bump-major:
	uv version --bump major

# Store a PyPI / TestPyPI token in macOS Keychain. Prompts with hidden input
# (bash `read -rsp`), so the token never appears on screen, in shell history,
# or in `make` output. Re-running overwrites the existing entry.
set-token-pypi:
	@bash -c 'read -rsp "Paste PyPI token: " TOKEN && echo && \
	  security delete-generic-password -s pypi-token-pypi >/dev/null 2>&1; \
	  security add-generic-password -a "$$USER" -s pypi-token-pypi -w "$$TOKEN" && \
	  echo "stored in Keychain under service: pypi-token-pypi"'

set-token-testpypi:
	@bash -c 'read -rsp "Paste TestPyPI token: " TOKEN && echo && \
	  security delete-generic-password -s pypi-token-testpypi >/dev/null 2>&1; \
	  security add-generic-password -a "$$USER" -s pypi-token-testpypi -w "$$TOKEN" && \
	  echo "stored in Keychain under service: pypi-token-testpypi"'

# Publish to TestPyPI. Token comes from macOS Keychain (service: pypi-token-testpypi).
# The `@` on the recipe lines hides the actual command so the token never appears in output.
release-test: build _release-test

_release-test:
	@VERSION=$$(grep '^version' $(PYPROJECT) | head -1 | cut -d'"' -f2) && \
	  STATUS=$$(curl -s -o /dev/null -w "%{http_code}" "https://test.pypi.org/pypi/$(PKG)/$$VERSION/json") && \
	  if [ "$$STATUS" = "200" ]; then \
	    echo "ERROR: $(PKG) $$VERSION is already on TestPyPI. Bump the version in pyproject.toml."; \
	    exit 1; \
	  fi
	@TOKEN=$$(security find-generic-password -s pypi-token-testpypi -w 2>/dev/null) && \
	  if [ -z "$$TOKEN" ]; then \
	    echo "ERROR: no Keychain entry for pypi-token-testpypi. Run 'make set-token-testpypi' first."; \
	    exit 1; \
	  fi && \
	  UV_PUBLISH_TOKEN="$$TOKEN" uv publish --publish-url https://test.pypi.org/legacy/

# Publish to real PyPI. Confirmation gate before upload (PyPI does not allow re-uploads).
release: build _release

_release:
	@VERSION=$$(grep '^version' $(PYPROJECT) | head -1 | cut -d'"' -f2) && \
	  STATUS=$$(curl -s -o /dev/null -w "%{http_code}" "https://pypi.org/pypi/$(PKG)/$$VERSION/json") && \
	  if [ "$$STATUS" = "200" ]; then \
	    echo "ERROR: $(PKG) $$VERSION is already on PyPI. Bump the version in pyproject.toml."; \
	    exit 1; \
	  fi && \
	  echo "About to publish $(PKG) $$VERSION to PyPI. This cannot be undone." && \
	  read -p "Type the version to confirm: " CONFIRM && \
	  [ "$$CONFIRM" = "$$VERSION" ] || { echo "Aborted."; exit 1; }
	@TOKEN=$$(security find-generic-password -s pypi-token-pypi -w 2>/dev/null) && \
	  if [ -z "$$TOKEN" ]; then \
	    echo "ERROR: no Keychain entry for pypi-token-pypi. Run 'make set-token-pypi' first."; \
	    exit 1; \
	  fi && \
	  UV_PUBLISH_TOKEN="$$TOKEN" uv publish

# Smoke-test installs from each index in a throwaway venv.
# `cd $$TMP` before running python so CWD doesn't shadow the venv install with this repo's source.
# Deps live on prod PyPI, so TestPyPI install needs --extra-index-url.
verify-release-test:
	@VERSION=$$(grep '^version' $(PYPROJECT) | head -1 | cut -d'"' -f2) && \
	  TMP=$$(mktemp -d) && \
	  uv venv --python 3.12 $$TMP/.venv >/dev/null 2>&1 && \
	  uv pip install --quiet --python $$TMP/.venv/bin/python \
	    --index-url https://test.pypi.org/simple/ \
	    --extra-index-url https://pypi.org/simple/ \
	    "$(PKG)==$$VERSION" && \
	  (cd $$TMP && $$TMP/.venv/bin/python -c "import diffbot; print('TestPyPI install OK:', diffbot.__version__)") && \
	  rm -rf $$TMP

verify-release:
	@VERSION=$$(grep '^version' $(PYPROJECT) | head -1 | cut -d'"' -f2) && \
	  TMP=$$(mktemp -d) && \
	  uv venv --python 3.12 $$TMP/.venv >/dev/null 2>&1 && \
	  uv pip install --quiet --python $$TMP/.venv/bin/python "$(PKG)==$$VERSION" && \
	  (cd $$TMP && $$TMP/.venv/bin/python -c "import diffbot; print('PyPI install OK:', diffbot.__version__)") && \
	  rm -rf $$TMP

# Publish the final diffbot-python release. Reuses the targets above with the
# legacy package's name/pyproject; `make build` is swapped for build-legacy.
release-test-legacy: build-legacy
	@$(MAKE) --no-print-directory _release-test PKG=diffbot-python PYPROJECT=legacy/diffbot-python/pyproject.toml

release-legacy: build-legacy
	@$(MAKE) --no-print-directory _release PKG=diffbot-python PYPROJECT=legacy/diffbot-python/pyproject.toml
