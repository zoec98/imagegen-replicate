"""Filesystem-backed prompt palette fragments."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


FRAGMENT_EXTENSION = ".txt"
MAX_FRAGMENT_BYTES = 256
NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")
DISALLOWED_CONTENT = {"(", ")", ":"}


@dataclass(frozen=True)
class PaletteFragment:
    name: str
    display_name: str
    content: str


@dataclass(frozen=True)
class Palette:
    name: str
    display_name: str
    fragments: tuple[PaletteFragment, ...]


class PaletteError(ValueError):
    pass


@dataclass(frozen=True)
class PaletteRepository:
    root: Path

    def list_palettes(self) -> tuple[Palette, ...]:
        root = self.root
        if not root.exists():
            return ()
        if not root.is_dir():
            msg = f"Fragment root is not a directory: {root}."
            raise PaletteError(msg)

        palettes = [
            self._palette_from_dir(path)
            for path in sorted(root.iterdir(), key=lambda item: item.name)
            if path.is_dir() and is_valid_name(path.name)
        ]
        return tuple(palettes)

    def read_fragment(self, palette_name: str, fragment_name: str) -> PaletteFragment:
        palette_name = validate_name(palette_name, label="palette")
        fragment_name = validate_name(fragment_name, label="fragment")
        path = self._fragment_path(palette_name, fragment_name)
        if not path.is_file():
            msg = f"Fragment not found: {palette_name}/{fragment_name}."
            raise PaletteError(msg)
        return PaletteFragment(
            name=fragment_name,
            display_name=display_name(fragment_name),
            content=read_fragment_content(path),
        )

    def _palette_from_dir(self, palette_dir: Path) -> Palette:
        fragments = [
            PaletteFragment(
                name=fragment_path.stem,
                display_name=display_name(fragment_path.stem),
                content=content,
            )
            for fragment_path, content in _valid_fragment_files(palette_dir)
        ]
        return Palette(
            name=palette_dir.name,
            display_name=display_name(palette_dir.name),
            fragments=tuple(fragments),
        )

    def _fragment_path(self, palette_name: str, fragment_name: str) -> Path:
        root = self.root.resolve()
        path = (root / palette_name / f"{fragment_name}{FRAGMENT_EXTENSION}").resolve()
        if not path.is_relative_to(root):
            msg = "Fragment path is outside the configured fragment root."
            raise PaletteError(msg)
        return path


def normalize_fragment_name(value: str) -> str:
    normalized = value.strip().replace(" ", "_")
    return validate_name(normalized, label="fragment")


def validate_name(value: str, *, label: str) -> str:
    if not isinstance(value, str) or not is_valid_name(value):
        msg = (
            f"Invalid {label} name: {value}. Names must start with a letter and "
            "contain only letters, numbers, underscores, or hyphens."
        )
        raise PaletteError(msg)
    return value


def is_valid_name(value: object) -> bool:
    return isinstance(value, str) and bool(NAME_PATTERN.fullmatch(value))


def display_name(name: str) -> str:
    return name.replace("_", " ")


def read_fragment_content(path: Path) -> str:
    content_bytes = path.read_bytes()
    if len(content_bytes) > MAX_FRAGMENT_BYTES:
        msg = f"Fragment content exceeds {MAX_FRAGMENT_BYTES} bytes: {path.name}."
        raise PaletteError(msg)
    try:
        content = content_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        msg = f"Fragment content must be UTF-8 text: {path.name}."
        raise PaletteError(msg) from error
    validate_fragment_content(content)
    return content


def validate_fragment_content(content: str) -> str:
    content_bytes = content.encode("utf-8")
    if len(content_bytes) > MAX_FRAGMENT_BYTES:
        msg = f"Fragment content exceeds {MAX_FRAGMENT_BYTES} bytes."
        raise PaletteError(msg)
    invalid = sorted(
        character for character in DISALLOWED_CONTENT if character in content
    )
    if invalid:
        characters = ", ".join(invalid)
        msg = f"Fragment content may not contain: {characters}."
        raise PaletteError(msg)
    return content


def _valid_fragment_files(palette_dir: Path) -> tuple[tuple[Path, str], ...]:
    fragments: list[tuple[Path, str]] = []
    for path in sorted(palette_dir.iterdir(), key=lambda item: item.stem):
        if not path.is_file() or path.suffix != FRAGMENT_EXTENSION:
            continue
        if not is_valid_name(path.stem):
            continue
        try:
            content = read_fragment_content(path)
        except PaletteError:
            continue
        fragments.append((path, content))
    return tuple(fragments)
