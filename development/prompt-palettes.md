# Prompt Palettes

Style, character, and other palettes are reusable prompt fragments.

Store fragments as plain text files under the fragment root derived from
`IMAGEGEN_DATA_DIR`, which defaults to:

```text
data/fragments
```

Committed sample fragments live under `data-example/fragments`. Keep local
runtime data under ignored `data/` or another private `IMAGEGEN_DATA_DIR` value.

Every directory under the fragment root is one singular palette, for example:

```text
data/fragments/
|-- character
|   |-- aoife.txt
|   `-- zoe.txt
`-- style
    |-- comic_lawrence.txt
    `-- photo.txt
```

Every `.txt` file under a palette directory is one fragment entry. Ignore
non-`.txt` files. Missing fragment roots are valid and mean there are no
palettes.

## Names

Palette and fragment names:

- Use singular palette directory names, such as `character` and `style`.
- Must start with a letter.
- May contain only `A-Z`, `a-z`, `0-9`, `_`, and `-`.
- Store spaces in fragment filenames as underscores.
- Display underscores as spaces in the UI.
- Normalize UI-entered fragment names by replacing spaces with underscores
  before validation.

## Content

Fragment content:

- Must be UTF-8 text.
- Must be at most 1024 bytes.
- May not contain `(`, `)`, or `:`.
- Must be validated before exposure to the browser or writes from the UI.

Palette entries exposed to the browser should include:

- Palette name.
- Palette display name.
- Fragment name.
- Fragment display name.
- Fragment content.

When inserting palette content, keep the user's original prompt visible and
editable. Do not silently replace user-entered text.

## Prompt Annotations

Prompt annotations use this plain textarea syntax:

```text
(character: zoe fragment content)
```

The browser owns cursor-aware annotation insertion and replacement. If the
cursor is inside an annotation of the same palette, selecting a new fragment
replaces the full annotation. If the cursor is inside a different palette
annotation, the browser must reject the edit and leave the prompt unchanged.

The server is authoritative for generation submission. It accepts either a
plain prompt or a valid non-nested annotated prompt. Invalid or nested
annotations must be rejected before request state, SQLite rows, or worker jobs
are created.

Provider prompt stripping happens server-side immediately before constructing
the model-provider request. The provider receives annotation content without
app-specific syntax. The app must preserve annotated prompts in request status,
SQLite history, and embedded image metadata. `request_sent_json` stores the
provider-ready payload for reproducibility.

Palette routes and UI code must use `PaletteRepository`; do not read or write
fragment files directly from templates or ad hoc route code. Palette write
routes require CSRF. Palette read routes may be non-mutating JSON routes, but
still validate names before filesystem access and must not expose files outside
the configured fragment root.

External filesystem edits are picked up on page refresh. Do not add live reload
or stale palette menu checks unless explicitly requested. The UI may create,
update, and delete entries inside existing palette directories, but creating or
deleting whole palette directories remains a manual filesystem task.
