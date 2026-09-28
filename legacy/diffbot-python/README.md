# ⚠️ LEGACY PACKAGE — `diffbot-python` is now `diffbot` ⚠️

> ## 🛑 Do not install `diffbot-python`. Install [`diffbot`](https://pypi.org/project/diffbot/) instead:
>
> ```bash
> pip uninstall diffbot-python
> pip install diffbot
> ```
>
> **This is the final release of `diffbot-python` (0.3.0). It will never be updated again**:
> no bug fixes, no new Diffbot API features, no security fixes.

---

The Diffbot Python library and `db` CLI now live at
**[diffbot](https://pypi.org/project/diffbot/)**. The import name is unchanged
(`import diffbot`), so no code changes are needed.

This release contains the same code as `diffbot` 3.0.0 so existing installs keep
working, but it prints a warning on every import until you migrate.

## Migrating

1. Replace `diffbot-python` with `diffbot` in your `requirements.txt`, `pyproject.toml`, etc.
2. Uninstall the old package **before** installing the new one:

   ```bash
   pip uninstall diffbot-python
   pip install diffbot
   ```

   Both packages provide the same `diffbot` module, so uninstalling
   `diffbot-python` after `diffbot` is installed deletes files that `diffbot`
   needs. If that happened, run `pip install --force-reinstall diffbot`.

Source and issues: <https://github.com/diffbot/diffbot-python>.
