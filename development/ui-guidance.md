# UI Guidance

Build the first screen as the actual generation workspace, not a marketing
page.

The UI should provide:

- Model selector.
- Mode-aware fields for text-to-image and image-edit workflows.
- Image upload/source controls for image-edit models.
- Model-specific parameter widgets.
- Style and character palette insertion.
- Generate button with loading and error states.
- Result preview gallery.
- Download/open controls for generated files.
- Gallery controls for loading embedded metadata into the workspace, creating
  masks, uploading when configured, and deleting/restoring local images.

Responsive behavior matters. Test layouts at mobile, tablet, and desktop
widths. Controls should remain usable on touch devices, with adequate spacing
and no text overlap.

Keep JavaScript progressive and focused. Server-rendered Flask/Jinja pages are
preferred unless there is a clear reason for a heavier frontend.

Use familiar controls:

- icons inside buttons for compact gallery tools
- swatches for color
- segmented controls for modes
- toggles/checkboxes for binary settings
- sliders/steppers/inputs for numeric values
- menus for option sets
- tabs for views when needed

Do not use visible in-app text to explain features, keyboard shortcuts, or
styling. The interface should expose the workflow directly.

Cards should be used for individual repeated items, modals, and framed tools.
Avoid nested cards and marketing-style page sections.

Text must fit inside controls across mobile and desktop. Use stable dimensions
for fixed-format UI elements such as galleries, toolbars, icon buttons,
counters, boards, and tiles so hover states or dynamic labels do not shift the
layout.

When frontend behavior changes, ask the user to validate the browser UI if they
have explicitly said not to use the browser skill.
