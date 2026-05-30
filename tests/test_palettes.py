import pytest

from imagegen.palettes import (
    MAX_FRAGMENT_BYTES,
    PaletteError,
    PaletteRepository,
    normalize_fragment_name,
    read_fragment_content,
    validate_fragment_content,
    validate_name,
)


def test_list_palettes_returns_sorted_valid_fragments(tmp_path):
    root = tmp_path / "fragments"
    character = root / "character"
    style = root / "style"
    character.mkdir(parents=True)
    style.mkdir()
    (character / "zoe.txt").write_text("Zoe description", encoding="utf-8")
    (character / "aoife.txt").write_text("Aoife description", encoding="utf-8")
    (character / "ignore.md").write_text("ignored", encoding="utf-8")
    (style / "comic_lawrence.txt").write_text("ink and flat color", encoding="utf-8")
    (style / "photo.txt").write_text("documentary photo", encoding="utf-8")

    palettes = PaletteRepository(root).list_palettes()

    assert [palette.name for palette in palettes] == ["character", "style"]
    assert [fragment.name for fragment in palettes[0].fragments] == ["aoife", "zoe"]
    assert [fragment.display_name for fragment in palettes[1].fragments] == [
        "comic lawrence",
        "photo",
    ]
    assert palettes[0].fragments[0].content == "Aoife description"


def test_list_palettes_returns_empty_for_missing_fragment_root(tmp_path):
    palettes = PaletteRepository(tmp_path / "missing").list_palettes()

    assert palettes == ()


def test_list_palettes_ignores_invalid_palette_and_fragment_names(tmp_path):
    root = tmp_path / "fragments"
    (root / "1invalid").mkdir(parents=True)
    valid = root / "character"
    valid.mkdir()
    (valid / "bad name.txt").write_text("bad", encoding="utf-8")
    (valid / "good-name.txt").write_text("good", encoding="utf-8")

    palettes = PaletteRepository(root).list_palettes()

    assert [palette.name for palette in palettes] == ["character"]
    assert [fragment.name for fragment in palettes[0].fragments] == ["good-name"]


def test_list_palettes_excludes_invalid_fragment_content(tmp_path):
    root = tmp_path / "fragments"
    style = root / "style"
    style.mkdir(parents=True)
    (style / "valid.txt").write_text("valid content", encoding="utf-8")
    (style / "paren.txt").write_text("bad (content", encoding="utf-8")
    (style / "oversized.txt").write_text(
        "x" * (MAX_FRAGMENT_BYTES + 1),
        encoding="utf-8",
    )

    palettes = PaletteRepository(root).list_palettes()

    assert [fragment.name for fragment in palettes[0].fragments] == ["valid"]


def test_normalize_fragment_name_accepts_ui_spaces():
    assert normalize_fragment_name("comic lawrence") == "comic_lawrence"
    assert normalize_fragment_name(" comic lawrence ") == "comic_lawrence"


@pytest.mark.parametrize(
    "name",
    ["../sample", "1sample", "bad name", "bad.name", "", "_bad"],
)
def test_validate_name_rejects_invalid_names(name):
    with pytest.raises(PaletteError, match="Invalid fragment name"):
        validate_name(name, label="fragment")


def test_validate_fragment_content_rejects_disallowed_characters():
    with pytest.raises(PaletteError, match="may not contain"):
        validate_fragment_content("bad: content")


def test_validate_fragment_content_rejects_oversized_content():
    with pytest.raises(PaletteError, match="exceeds"):
        validate_fragment_content("x" * (MAX_FRAGMENT_BYTES + 1))


def test_read_fragment_rejects_path_traversal_before_filesystem_access(tmp_path):
    repository = PaletteRepository(tmp_path / "fragments")

    with pytest.raises(PaletteError, match="Invalid palette name"):
        repository.read_fragment("../outside", "fragment")


def test_read_fragment_returns_named_fragment(tmp_path):
    root = tmp_path / "fragments"
    (root / "character").mkdir(parents=True)
    (root / "character" / "zoe.txt").write_text("Zoe description", encoding="utf-8")

    fragment = PaletteRepository(root).read_fragment("character", "zoe")

    assert fragment.name == "zoe"
    assert fragment.display_name == "zoe"
    assert fragment.content == "Zoe description"


def test_read_fragment_content_rejects_non_utf8(tmp_path):
    fragment = tmp_path / "bad.txt"
    fragment.write_bytes(b"\xff")

    with pytest.raises(PaletteError, match="UTF-8"):
        read_fragment_content(fragment)


def test_create_fragment_requires_existing_palette(tmp_path):
    repository = PaletteRepository(tmp_path / "fragments")

    with pytest.raises(PaletteError, match="Palette not found"):
        repository.create_fragment("character", "zoe", "Zoe description")


def test_create_fragment_writes_normalized_name(tmp_path):
    root = tmp_path / "fragments"
    (root / "style").mkdir(parents=True)
    repository = PaletteRepository(root)

    fragment = repository.create_fragment(
        "style",
        "comic lawrence",
        "ink style",
    )

    assert fragment.name == "comic_lawrence"
    assert (root / "style" / "comic_lawrence.txt").read_text(
        encoding="utf-8"
    ) == "ink style"


def test_create_fragment_rejects_conflict(tmp_path):
    root = tmp_path / "fragments"
    (root / "style").mkdir(parents=True)
    (root / "style" / "photo.txt").write_text("photo", encoding="utf-8")

    with pytest.raises(PaletteError, match="already exists"):
        PaletteRepository(root).create_fragment("style", "photo", "new")


def test_update_fragment_overwrites_existing_content(tmp_path):
    root = tmp_path / "fragments"
    (root / "style").mkdir(parents=True)
    (root / "style" / "photo.txt").write_text("old", encoding="utf-8")

    fragment = PaletteRepository(root).update_fragment("style", "photo", "new")

    assert fragment.content == "new"
    assert (root / "style" / "photo.txt").read_text(encoding="utf-8") == "new"


def test_delete_fragment_removes_existing_file(tmp_path):
    root = tmp_path / "fragments"
    (root / "style").mkdir(parents=True)
    fragment_path = root / "style" / "photo.txt"
    fragment_path.write_text("photo", encoding="utf-8")

    PaletteRepository(root).delete_fragment("style", "photo")

    assert not fragment_path.exists()
