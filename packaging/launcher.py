"""PyInstaller entry point (equivalent to ``python -m nocturne``)."""

import sys

from nocturne.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
