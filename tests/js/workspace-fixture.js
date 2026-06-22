export function renderWorkspace({ modelRegistry = [], selectedProvider = "" } = {}) {
  document.body.innerHTML = `
    <script id="model-registry-data" type="application/json">${JSON.stringify(modelRegistry)}</script>
    <script id="palette-data" type="application/json">[]</script>
    <form
      class="prompt-form"
      data-api-generate-url="/api/generate"
      data-api-images-url="/api/images"
      data-api-app-version-url="/api/app-version"
      data-api-palettes-url="/api/palettes"
      data-poll-seconds="1"
    >
      <select id="provider-selector" name="provider">
        <option value="replicate">Replicate</option>
        <option value="falai">fal.ai</option>
      </select>
      <select id="model-selector" name="model"></select>
      <div class="pricing-info"></div>
      <div class="pricing-tooltip"></div>
      <div class="parameter-grid"></div>
      <div class="palette-controls"></div>
      <button class="palette-editor-toggle" type="button"></button>
      <div class="palette-editor" hidden>
        <select id="palette-editor-palette"></select>
        <select id="palette-editor-fragment"></select>
        <input id="palette-editor-name">
        <textarea id="palette-editor-content"></textarea>
        <button class="palette-editor-create" type="button"></button>
        <button class="palette-editor-update" type="button"></button>
        <button class="palette-editor-delete" type="button"></button>
      </div>
      <textarea id="prompt"></textarea>
      <button class="generate-button" type="submit"></button>
      <button class="edit-toggle" type="button"></button>
      <span class="source-counter"></span>
      <button class="source-clear" type="button" hidden></button>
      <span class="source-selection-status"></span>
      <div class="messages"></div>
      <button class="trashcan-toggle" type="button"></button>
      <span class="trashcan-count"></span>
      <button class="upload-toggle" type="button"></button>
    </form>
    <div class="gallery"></div>
    <div class="trash-overlay" hidden>
      <button class="trash-close" type="button"></button>
      <button class="trash-empty" type="button"></button>
      <div class="trash-gallery"></div>
      <div class="trash-empty-state" hidden></div>
    </div>
    <div class="upload-overlay" hidden>
      <button class="upload-close" type="button"></button>
      <input class="upload-url">
      <button class="upload-url-load" type="button"></button>
      <div class="upload-drop-target"></div>
      <input class="upload-file-input" type="file">
      <button class="upload-file-choose" type="button"></button>
      <div class="upload-status"></div>
      <div class="upload-immich-browser">
        <button class="upload-immich-prev" type="button"></button>
        <button class="upload-immich-next" type="button"></button>
        <span class="upload-immich-page"></span>
        <div class="upload-immich-empty" hidden></div>
        <div class="upload-immich-gallery"></div>
      </div>
    </div>
    <div class="mask-editor-overlay" hidden>
      <div class="mask-editor-stage"></div>
      <div class="mask-editor-canvas-wrap"></div>
      <canvas class="mask-editor-source"></canvas>
      <canvas class="mask-editor-mask"></canvas>
      <select class="mask-editor-operation">
        <option value="crop" selected>Crop</option>
        <option value="blur">Blur</option>
        <option value="mask">Mask</option>
      </select>
      <div class="mask-editor-control-group mask-editor-brush-controls">
        <input class="mask-editor-brush-size" type="range" value="50">
        <label class="mask-editor-falloff-tool">
          <input class="mask-editor-brush-falloff" type="range" value="0">
        </label>
        <span class="mask-editor-brush-size-value"></span>
        <span class="mask-editor-brush-falloff-value"></span>
      </div>
      <div class="mask-editor-control-group mask-editor-crop-controls" hidden>
        <button class="mask-editor-crop" type="button"></button>
      </div>
      <div class="mask-editor-control-group mask-editor-blur-controls" hidden>
        <input class="mask-editor-blur-radius" type="range" min="0" max="50" step="0.1" value="20">
        <span class="mask-editor-blur-radius-value"></span>
        <button class="mask-editor-blur" type="button"></button>
      </div>
      <button class="mask-editor-invert" type="button"></button>
      <button class="mask-editor-save" type="button"></button>
      <h2 id="mask-editor-title">Image editor</h2>
      <button class="mask-editor-close" type="button"></button>
    </div>
  `;

  const providerSelector = document.querySelector("#provider-selector");
  providerSelector.value = selectedProvider;
}
