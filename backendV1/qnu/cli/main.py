"""Minimal backendV1 CLI."""

from __future__ import annotations

import argparse


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="qnu-v1")
    parser.add_argument("command", choices=["preflight", "reconcile", "migrate"])
    args = parser.parse_args(argv)
    print(f"backendV1: '{args.command}' chưa triển khai trong Phase 0.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
