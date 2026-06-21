# Image Upload User Story

## Story

As a user, I want to upload images into the configured images directory so that
I can use externally sourced or existing gallery images as local image
generation inputs.

## User Goals

- Add an image from a URL.
- Add an image by dragging and dropping a local image file.
- Browse the configured Immich main gallery and import selected images.
- Keep uploaded/imported images available in the same local gallery as generated
  images.

## Primary Workflow

1. The workspace shows an upload button between the trash control and the
   palette controls.
2. The user clicks the upload button.
3. An upload overlay opens.
4. The user uploads or imports images through one of the supported input
   methods.
5. Imported images are stored in the configured images directory.
6. The local gallery refreshes and shows the newly available images.

## Upload Overlay Requirements

The overlay pane should include:

- A URL field for entering an image URL.
- A `Load` button next to the URL field.
- A drag-and-drop target that accepts dropped files with MIME type `image/*`.
- A gallery-like Immich browser for selecting images from the Immich main
  gallery.

## URL Import

### User Behavior

The user pastes an image URL and clicks `Load`.

### Acceptance Criteria

- The URL field accepts HTTP and HTTPS image URLs.
- The `Load` button starts the import.
- The app validates that the fetched content is an image before storing it.
- The imported image is written into the configured images directory.
- The local gallery refreshes after a successful import.
- Failed imports show an actionable error without hiding useful details.

## Drag-And-Drop Upload

### User Behavior

The user drops one or more local image files onto the upload target.

### Acceptance Criteria

- The drop target accepts files with MIME type `image/*`.
- Non-image drops are rejected with a clear error.
- Accepted images are written into the configured images directory.
- The local gallery refreshes after successful uploads.
- Existing files are not overwritten without an explicit user action.

## Immich Gallery Import

### User Behavior

The user browses images from the Immich main gallery in the upload overlay and
imports selected images into the local images directory.

### Acceptance Criteria

- The Immich browser appears only when Immich is configured.
- The browser uses a gallery-like layout consistent with the local gallery.
- The Immich main gallery is paginated because it may contain tens of thousands
  of images.
- Images are loaded in batches of 20.
- The user can move between batches without loading the full Immich gallery at
  once.
- Imported Immich images are copied into the configured images directory.
- The local gallery refreshes after a successful import.

## Data And Storage Requirements

- Uploaded and imported files are stored under the configured images directory.
- Browser-submitted filenames, URLs, MIME types, and remote metadata are not
  trusted.
- Stored filenames are safe and collision-resistant.
- Unsupported or invalid image data is rejected before storage.

## Open Questions

- Should URL imports preserve the remote filename when it is safe, or always use
  a generated local filename?
  - always use a generated local filename.
- Should drag-and-drop support multiple files in the first implementation?
  - For initial implementation, support single file uploads only.
- Should Immich imports support search/filtering in addition to pagination?
  - For initial implementation, support pagination only.
- Should imported images receive embedded metadata describing their source?
  - We keep the existing image metadata unchanged. 
