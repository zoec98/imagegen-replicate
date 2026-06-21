import { csrfJsonRequest, requestJson } from "./api.js";
import { createElement, readJsonScript, setBooleanAttribute } from "./dom.js";

export function setupPalettes(root = document, services = {}) {
  const { csrfToken, showMessage = () => {} } = services;
  const form = root.querySelector(".prompt-form");
  const promptInput = form?.querySelector("#prompt");
  const controls = form?.querySelector(".palette-controls");
  const toggle = form?.querySelector(".palette-editor-toggle");
  const editor = form?.querySelector(".palette-editor");
  const editorPalette = form?.querySelector("#palette-editor-palette");
  const editorFragment = form?.querySelector("#palette-editor-fragment");
  const editorName = form?.querySelector("#palette-editor-name");
  const editorContent = form?.querySelector("#palette-editor-content");
  const createButton = form?.querySelector(".palette-editor-create");
  const updateButton = form?.querySelector(".palette-editor-update");
  const deleteButton = form?.querySelector(".palette-editor-delete");
  let paletteData = readPaletteData(root);

  function fragmentForPalette(paletteName, fragmentName) {
    const palette = paletteData.find((item) => item.name === paletteName);
    if (!palette || !Array.isArray(palette.fragments)) {
      return null;
    }
    return palette.fragments.find((fragment) => fragment.name === fragmentName) || null;
  }

  function insertFragment(paletteName, fragmentName) {
    if (!promptInput) {
      return;
    }
    const fragment = fragmentForPalette(paletteName, fragmentName);
    if (!fragment) {
      showMessage("Palette fragment is unavailable.", "error");
      return;
    }

    let annotations;
    try {
      annotations = promptAnnotations(promptInput.value);
    } catch (error) {
      showMessage(error.message || "Prompt annotations are invalid.", "error");
      return;
    }

    const cursor = promptInput.selectionStart ?? promptInput.value.length;
    const activeAnnotation = annotationAtCursor(annotations, cursor);
    const nextText = annotationText(paletteName, fragment);
    if (activeAnnotation && activeAnnotation.paletteName !== paletteName) {
      showMessage(
        `Move the cursor outside the ${activeAnnotation.paletteName} annotation first.`,
        "error",
      );
      return;
    }

    promptInput.focus();
    if (activeAnnotation) {
      promptInput.setSelectionRange(activeAnnotation.start, activeAnnotation.end);
    }
    promptInput.setRangeText(
      nextText,
      promptInput.selectionStart,
      promptInput.selectionEnd,
      "end",
    );
    showMessage(`${fragment.display_name} inserted.`, "success");
  }

  function setEditorOpen(isOpen) {
    if (editor) {
      editor.hidden = !isOpen;
    }
    toggle?.classList.toggle("palette-editor-toggle-active", isOpen);
    setBooleanAttribute(toggle, "aria-pressed", isOpen);
  }

  function paletteUrl(path = "") {
    const base = form?.dataset.apiPalettesUrl || "/api/palettes";
    return `${base}${path}`;
  }

  function renderControls() {
    if (!controls) {
      return;
    }
    controls.replaceChildren();
    paletteData.forEach((palette) => {
      const select = createElement("select", {
        dataset: { paletteName: palette.name },
        id: `palette-${palette.name}`,
      });
      select.append(
        createElement("option", {
          textContent: `Select ${palette.display_name}`,
          value: "",
        }),
      );
      (palette.fragments || []).forEach((fragment) => {
        select.append(
          createElement("option", {
            textContent: fragment.display_name,
            value: fragment.name,
          }),
        );
      });

      controls.append(
        createElement("label", {
          children: [
            createElement("span", { textContent: palette.display_name }),
            select,
          ],
          className: "palette-field",
          htmlFor: `palette-${palette.name}`,
        }),
      );
    });
  }

  function populateEditor(selectedPalette = "", selectedFragment = "") {
    if (!editorPalette || !editorFragment) {
      return;
    }
    editorPalette.replaceChildren();
    paletteData.forEach((palette) => {
      editorPalette.append(
        createElement("option", {
          selected: palette.name === selectedPalette,
          textContent: palette.display_name,
          value: palette.name,
        }),
      );
    });
    const palette =
      paletteData.find((item) => item.name === editorPalette.value) ||
      paletteData[0] ||
      null;
    editorFragment.replaceChildren();
    if (!palette) {
      return;
    }
    (palette.fragments || []).forEach((fragment) => {
      editorFragment.append(
        createElement("option", {
          selected: fragment.name === selectedFragment,
          textContent: fragment.display_name,
          value: fragment.name,
        }),
      );
    });
  }

  async function refresh(selectedPalette = "", selectedFragment = "") {
    if (!form?.dataset.apiPalettesUrl) {
      return;
    }
    const data = await requestJson(form.dataset.apiPalettesUrl, {
      fallbackMessage: "Palette refresh failed.",
    });
    paletteData = Array.isArray(data.palettes) ? data.palettes : [];
    renderControls();
    populateEditor(selectedPalette, selectedFragment);
  }

  async function loadEditorFragment() {
    if (!editorPalette?.value || !editorFragment?.value) {
      if (editorContent) {
        editorContent.value = "";
      }
      return;
    }
    const data = await requestJson(
      paletteUrl(
        `/${encoded(editorPalette.value)}/fragments/${encoded(editorFragment.value)}`,
      ),
      { fallbackMessage: "Palette fragment could not be loaded." },
    );
    if (editorName) {
      editorName.value = "";
    }
    if (editorContent) {
      editorContent.value = data.fragment?.content || "";
    }
  }

  async function writeFragment(method, url, body) {
    return csrfJsonRequest(url, body, {
      csrfToken,
      method,
      fallbackMessage: "Palette edit failed.",
    });
  }

  async function createFragment() {
    const paletteName = editorPalette?.value || "";
    const name = editorName?.value || "";
    const content = editorContent?.value || "";
    const data = await writeFragment(
      "POST",
      paletteUrl(`/${encoded(paletteName)}/fragments`),
      {
        name,
        content,
      },
    );
    await refresh(paletteName, data.fragment?.name || "");
    showMessage(`${data.fragment?.display_name || "Fragment"} created.`, "success");
  }

  async function updateFragment() {
    const paletteName = editorPalette?.value || "";
    const fragmentName = editorFragment?.value || "";
    const content = editorContent?.value || "";
    const data = await writeFragment(
      "PUT",
      paletteUrl(`/${encoded(paletteName)}/fragments/${encoded(fragmentName)}`),
      { content },
    );
    await refresh(paletteName, data.fragment?.name || fragmentName);
    showMessage(`${data.fragment?.display_name || "Fragment"} updated.`, "success");
  }

  async function deleteFragment() {
    const paletteName = editorPalette?.value || "";
    const fragmentName = editorFragment?.value || "";
    const data = await writeFragment(
      "DELETE",
      paletteUrl(`/${encoded(paletteName)}/fragments/${encoded(fragmentName)}`),
      {},
    );
    await refresh(paletteName, "");
    if (editorContent) {
      editorContent.value = "";
    }
    showMessage(`${data.deleted || "Fragment"} deleted.`, "success");
  }

  toggle?.addEventListener("click", () => {
    if (!editor) {
      return;
    }
    const nextOpen = editor.hidden;
    setEditorOpen(nextOpen);
    if (nextOpen) {
      populateEditor(editorPalette?.value || "", editorFragment?.value || "");
      loadEditorFragment().catch((error) => {
        showMessage(error.message || "Palette fragment could not be loaded.", "error");
      });
    }
  });
  controls?.addEventListener("change", (event) => {
    const control = event.target;
    if (!control?.dataset?.paletteName || !control.value) {
      return;
    }
    insertFragment(control.dataset.paletteName, control.value);
    control.value = "";
  });
  editorPalette?.addEventListener("change", () => {
    populateEditor(editorPalette.value, "");
    loadEditorFragment().catch((error) => {
      showMessage(error.message || "Palette fragment could not be loaded.", "error");
    });
  });
  editorFragment?.addEventListener("change", () => {
    loadEditorFragment().catch((error) => {
      showMessage(error.message || "Palette fragment could not be loaded.", "error");
    });
  });
  createButton?.addEventListener("click", () => {
    createFragment().catch((error) => {
      showMessage(error.message || "Palette fragment could not be created.", "error");
    });
  });
  updateButton?.addEventListener("click", () => {
    updateFragment().catch((error) => {
      showMessage(error.message || "Palette fragment could not be updated.", "error");
    });
  });
  deleteButton?.addEventListener("click", () => {
    deleteFragment().catch((error) => {
      showMessage(error.message || "Palette fragment could not be deleted.", "error");
    });
  });

  renderControls();
  populateEditor();
  setEditorOpen(!editor?.hidden);

  return {
    refresh,
    setEditorOpen,
  };
}

function readPaletteData(root) {
  const value = readJsonScript("#palette-data", { fallback: [], root });
  return Array.isArray(value) ? value : [];
}

function promptAnnotations(prompt) {
  const annotations = [];
  let index = 0;
  while (index < prompt.length) {
    if (prompt[index] !== "(") {
      index += 1;
      continue;
    }
    const match = prompt.slice(index).match(/^\(([A-Za-z][A-Za-z0-9_-]*):/);
    if (!match) {
      index += 1;
      continue;
    }
    const annotation = readPromptAnnotation(prompt, index, match[1]);
    annotations.push(annotation);
    index = annotation.end;
  }
  return annotations;
}

function readPromptAnnotation(prompt, start, paletteName) {
  let cursor = start + paletteName.length + 2;
  cursor = requireAnnotationWhitespace(prompt, cursor);
  const fragmentStart = cursor;
  while (
    cursor < prompt.length &&
    !/\s/.test(prompt[cursor]) &&
    prompt[cursor] !== ")"
  ) {
    cursor += 1;
  }
  const fragmentName = prompt.slice(fragmentStart, cursor);
  if (!/^[A-Za-z][A-Za-z0-9_-]*$/.test(fragmentName)) {
    throw new Error("Prompt annotation has an invalid fragment name.");
  }
  cursor = requireAnnotationWhitespace(prompt, cursor);
  const contentStart = cursor;
  while (cursor < prompt.length) {
    if (prompt[cursor] === ")") {
      if (cursor === contentStart) {
        throw new Error("Prompt annotation content is required.");
      }
      return {
        start,
        end: cursor + 1,
        paletteName,
        fragmentName,
        content: prompt.slice(contentStart, cursor),
      };
    }
    if (prompt[cursor] === "(") {
      throw new Error("Prompt annotations may not be nested.");
    }
    if (prompt[cursor] === ":") {
      throw new Error("Prompt annotation content may not contain ':'.");
    }
    cursor += 1;
  }
  throw new Error("Prompt annotation is missing a closing ')'.");
}

function requireAnnotationWhitespace(prompt, cursor) {
  if (cursor >= prompt.length || !/\s/.test(prompt[cursor])) {
    throw new Error("Prompt annotation must use '(palette: fragment content)' syntax.");
  }
  while (cursor < prompt.length && /\s/.test(prompt[cursor])) {
    cursor += 1;
  }
  return cursor;
}

function annotationText(paletteName, fragment) {
  return `(${paletteName}: ${fragment.name} ${fragment.content})`;
}

function annotationAtCursor(annotations, cursor) {
  return (
    annotations.find(
      (annotation) => cursor > annotation.start && cursor < annotation.end,
    ) || null
  );
}

function encoded(value) {
  return encodeURIComponent(value);
}
