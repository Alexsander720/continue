"""Graveyard Keeper 2 needs no name table: the card shows only numbers read from the .info sidecar.

Kept for the contribution layout. If a future version displays named places or items, generate
data/graveyard_keeper_2.<lang>.json from the game's own localisation here.
"""
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("game_files", type=Path, nargs="?")
    parser.add_argument("--language", choices=("en", "ru", "uk"), default="en")
    parser.parse_args()
    print("graveyard_keeper_2: no name table required (numeric facts only)")


if __name__ == "__main__":
    main()
