"""PyInstaller entry point for the standalone ``db`` CLI.

PyInstaller freezes a *script*, not a ``console_scripts`` entry point, so this
thin wrapper mirrors :mod:`diffbot.cli.__main__` but with an absolute import
that resolves correctly inside the frozen bundle.
"""

from diffbot.cli import main

if __name__ == "__main__":
    main()
