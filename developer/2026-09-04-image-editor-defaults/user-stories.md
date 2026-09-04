# Image editor defaults

## User story 1: Predictable edit controls
w
As an img-replicate user editing a gallery image, I want the **Edit Image**
operation list ordered **Blur**, **Crop**, **Mask**, and the **Blur** setting
to start at a size appropriate for the selected image, so that the most useful
tools and blur amount are ready without manual adjustment.

### Acceptance criteria

1. The operation dropdown lists, in this exact order: `Blur`, `Crop`, `Mask`.
2. When the image editor opens for an image, initialize the blur setting from
   that image's natural pixel dimensions, not its displayed dimensions.
3. Set the initial blur radius in pixels to
   `min(max(max(image_width, image_height) / 50, 0), 50)`.
4. Show the initialized radius in the existing Blur control and use it if the
   user applies blur without changing the setting.
5. Recompute the default whenever the editor opens a different image; do not
   overwrite a value the user changes while editing the current image.
