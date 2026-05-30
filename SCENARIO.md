# Palette Prompt Fragments

This scenario describes a palette system for reusable prompt fragments. The goal
is to let users insert and replace named fragments such as character or style
descriptions, while keeping fragment metadata out of the final model-provider
prompt.

## User Stories

### Select Palette Fragments

As a user, I want to select prompt fragments from predefined palettes so that I
can quickly enrich a prompt with reusable character, style, or other prompt
material.

Acceptance notes:

- Palettes are shown near the prompt editor.
- Palette names are singular, for example `character` and `style`.
- Each palette presents its fragment entries in alphabetical order.
- Fragment names are stored with underscores but displayed with spaces.
  For example, `comic_lawrence.txt` is shown as `comic lawrence`.
- Selecting a fragment inserts that fragment into the prompt at the cursor.
- The inserted prompt text includes the fragment content from storage.
- The palette system supports multiple palette categories, such as `character`
  and `style`.

Example:

```text
data/fragments/
|-- character
|   |-- aoife.txt
|   |-- diane.txt
|   |-- marie.txt
|   |-- valeria.txt
|   `-- zoe.txt
`-- style
    |-- comic_lawrence.txt
    |-- comic_raymond.txt
    |-- loish.txt
    |-- model.txt
    `-- photo.txt
```

This creates a `character` palette with `aoife`, `diane`, `marie`, `valeria`,
and `zoe`, and a `style` palette with `comic lawrence`, `comic raymond`,
`loish`, `model`, and `photo`.

### Replace Existing Fragment Annotation

As a user, I want selecting a fragment from a palette to replace the current
fragment of that same palette type when my cursor is inside an existing
annotation, so that I can swap a character or style without manually deleting
old text.

Acceptance notes:

- If the cursor is inside a `character` annotation, selecting another character
  replaces the entire current `character` annotation.
- If the cursor is not inside any annotation, selecting a fragment inserts a new
  annotation at the cursor position.
- If the cursor is inside an annotation of a different palette type, selecting a
  fragment is rejected with a clear error signal and message.
- Replacement preserves the rest of the prompt outside the annotation.
- Replacement is based on annotation structure, not a simple text search for a
  fragment name.
- As a UI refinement, palettes that cannot currently be used may be locked or
  disabled while the cursor is inside another annotation type.

Example replacement:

```text
(character: marie <content of marie.txt>)
```

Selecting `zoe` from the `character` palette while the cursor is inside that
annotation replaces the whole block with:

```text
(character: zoe <content of zoe.txt>)
```

Example insertion outside any annotation:

```text
(character: zoe <content of zoe.txt>)
```

Example rejected insertion:

```text
(style: loish <content of loish.txt>)
```

If the cursor is inside this `style` annotation, selecting a `character`
fragment is rejected.

### Send Clean Prompts To Model Providers

As a user, I want palette annotations to help with editing without being sent to
the model provider, so that the final provider prompt contains only meaningful
generation text.

Acceptance notes:

- Annotation delimiters and metadata are stripped immediately before a prompt is
  sent to a model provider.
- The browser does not strip annotations.
- The app stores annotated prompts in logs and embedded image metadata.
- The fragment content remains in the provider prompt.
- The user can still see and edit annotations in the prompt editor.

Example editor text:

```text
(character: zoe A young woman of mixed French / Japanese heritage with light skin,
with a dark chin-length black bob with muted blue-colored accents, brown eyes,
makeup, small stud earrings.)
```

Provider prompt text:

```text
A young woman of mixed French / Japanese heritage with light skin, with a dark
chin-length black bob with muted blue-colored accents, brown eyes, makeup, small
stud earrings.
```

### Manage Palette Entries In The UI

As a user, I want a simple editor for palette entries so that I can create,
read, update, and delete reusable prompt fragments without leaving the app.

Acceptance notes:

- The editor supports creating new entries inside an existing palette.
- The editor supports reading and updating existing entries.
- The editor supports deleting entries.
- The editor does not support creating or deleting whole palettes.
- Entries are always displayed in alphabetical order.
- The editor is accessible from the GUI.
- The editor is hidden by default because it is expected to be used rarely.
- Palette edits use CSRF-protected API routes.
- The editor is a single-page client-side interface; no server-rendered edit
  forms are required.

## Developer Stories

### Load Palettes From Files

As a developer, I want palette fragments to be stored as plain text files under
`data/fragments/<palette>/<fragment>.txt` so that fragments can also be edited
with external tools.

Acceptance notes:

- Each directory under `data/fragments/` is a palette.
- Palette names are singular and used directly in annotations.
- Each `.txt` file under a palette directory is a fragment entry.
- The fragment name is derived from the filename without the `.txt` suffix.
- Fragment filenames store spaces as underscores.
- Palette names and normalized fragment names may contain only `A-Z`, `a-z`,
  `0-9`, `_`, and `-`, and must start with a letter.
- UI-entered fragment names may contain spaces; spaces are normalized to
  underscores for storage.
- Palette names and fragment names are sorted alphabetically for display.
- Non-`.txt` files are ignored.
- Missing `data/fragments/` is treated as no palettes, not as an error.
- External file changes are picked up on page refresh only.
- The app does not live-reload palettes or check for stale palette menus.

Example:

```text
data/fragments/character/zoe.txt
```

This creates fragment `zoe` in palette `character`.

### Validate Fragment File Content

As a developer, I want fragment files to be validated before use so that
externally edited files cannot break annotation parsing.

Acceptance notes:

- Fragment content may not contain `(`, `)`, or `:`.
- Fragment content is limited to at most 256 bytes.
- Invalid fragment files are rejected or excluded with clear error reporting.
- The same validation is applied to fragments created or updated through the UI.

### Represent Editable Prompt Annotations

As a developer, I want a prompt annotation format that identifies palette
fragments by palette type and fragment name so that the app can insert, replace,
and strip annotations deterministically.

Annotation shape:

```text
(character: zoe <fragment content>)
```

Acceptance notes:

- The annotation contains a palette type, a fragment name, and fragment content.
- The palette type is singular and matches the palette directory name.
- The annotation metadata is not sent to the model provider.
- The parser can determine whether the cursor is inside a specific annotation.
- The parser can determine whether the cursor is inside a different annotation
  type and reject invalid insertion.
- The parser can replace the full annotation block when needed.
- Malformed annotations fail safely and do not corrupt the prompt.

### Build Provider Prompt From Editor Prompt

As a developer, I want server-side prompt processing to strip palette annotation
syntax immediately before calling model providers so that provider prompts do
not include app-specific markup.

Acceptance notes:

- The server does not require the browser to strip annotations correctly.
- The browser submits annotated prompt text.
- `/api/generate` processes the submitted prompt into provider-ready prompt text.
- Generation logs and embedded image metadata preserve the annotated prompt.
- The provider-ready prompt is not stored separately in SQLite for this scenario.
- Tests cover plain prompts, annotated prompts, multiple annotations, and
  malformed annotation input.

### Expose Palette Data To The Browser

As a developer, I want the backend to expose available palettes and fragments to
the browser so that the prompt editor can render palette controls.

Acceptance notes:

- The browser receives palette names, display names, fragment names, and
  fragment content.
- API responses do not expose files outside `data/fragments/`.
- Palette and fragment names are validated before file access.
- Invalid or oversized fragment files are handled with clear errors or excluded
  from the exposed palette data.

### Persist Palette Edits

As a developer, I want CRUD operations in the palette editor to read and write
the same `data/fragments/<palette>/<fragment>.txt` files so that UI edits and
external file edits use one source of truth.

Acceptance notes:

- Creating an entry writes a new `.txt` file in an existing palette directory.
- Updating an entry overwrites the corresponding `.txt` file.
- Deleting an entry removes the corresponding `.txt` file.
- Creating and deleting palette directories remains a manual filesystem task.
- Palette and fragment names are validated to prevent path traversal.
- Fragment content is validated before writing.
- Conflicting names and missing entries return clear errors.
- All write APIs are CSRF-protected.

## UI Notes

- If the prompt editor supports inline formatting, normal prompt text should be
  shown in the standard text color and annotation metadata should be shown in a
  lighter but still readable color.
- If the prompt editor remains a plain textarea, annotations are shown as plain
  text.

## Open Questions

- Is rich inline formatting inside the prompt editor in scope for the first
  implementation, or should the first implementation use plain textarea
  annotations only?
