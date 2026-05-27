.PHONY: test test-live build clean bump-patch bump-minor bump-major set-token-pypi set-token-testpypi release-test release verify-release-test verify-release

test:
	uv run --extra dev pytest

test-live:
	uv run --extra dev pytest -m live

clean:
	rm -rf dist build *.egg-info

build: clean
	uv build

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
release-test: build
	@VERSION=$$(grep '^version' pyproject.toml | head -1 | cut -d'"' -f2) && \
	  STATUS=$$(curl -s -o /dev/null -w "%{http_code}" "https://test.pypi.org/pypi/diffbot-python/$$VERSION/json") && \
	  if [ "$$STATUS" = "200" ]; then \
	    echo "ERROR: diffbot-python $$VERSION is already on TestPyPI. Bump the version in pyproject.toml."; \
	    exit 1; \
	  fi
	@TOKEN=$$(security find-generic-password -s pypi-token-testpypi -w 2>/dev/null) && \
	  if [ -z "$$TOKEN" ]; then \
	    echo "ERROR: no Keychain entry for pypi-token-testpypi. Run 'make set-token-testpypi' first."; \
	    exit 1; \
	  fi && \
	  UV_PUBLISH_TOKEN="$$TOKEN" uv publish --publish-url https://test.pypi.org/legacy/

# Publish to real PyPI. Confirmation gate before upload (PyPI does not allow re-uploads).
release: build
	@VERSION=$$(grep '^version' pyproject.toml | head -1 | cut -d'"' -f2) && \
	  STATUS=$$(curl -s -o /dev/null -w "%{http_code}" "https://pypi.org/pypi/diffbot-python/$$VERSION/json") && \
	  if [ "$$STATUS" = "200" ]; then \
	    echo "ERROR: diffbot-python $$VERSION is already on PyPI. Bump the version in pyproject.toml."; \
	    exit 1; \
	  fi && \
	  echo "About to publish diffbot-python $$VERSION to PyPI. This cannot be undone." && \
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
	@VERSION=$$(grep '^version' pyproject.toml | head -1 | cut -d'"' -f2) && \
	  TMP=$$(mktemp -d) && \
	  uv venv --python 3.12 $$TMP/.venv >/dev/null 2>&1 && \
	  uv pip install --quiet --python $$TMP/.venv/bin/python \
	    --index-url https://test.pypi.org/simple/ \
	    --extra-index-url https://pypi.org/simple/ \
	    "diffbot-python==$$VERSION" && \
	  (cd $$TMP && $$TMP/.venv/bin/python -c "import diffbot; print('TestPyPI install OK:', diffbot.__version__)") && \
	  rm -rf $$TMP

verify-release:
	@VERSION=$$(grep '^version' pyproject.toml | head -1 | cut -d'"' -f2) && \
	  TMP=$$(mktemp -d) && \
	  uv venv --python 3.12 $$TMP/.venv >/dev/null 2>&1 && \
	  uv pip install --quiet --python $$TMP/.venv/bin/python "diffbot-python==$$VERSION" && \
	  (cd $$TMP && $$TMP/.venv/bin/python -c "import diffbot; print('PyPI install OK:', diffbot.__version__)") && \
	  rm -rf $$TMP
