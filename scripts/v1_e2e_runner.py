"""Compatibility entry point; mutations require explicit session commands."""

from v1_e2e_session import main

if __name__ == "__main__":
    raise SystemExit(main())
