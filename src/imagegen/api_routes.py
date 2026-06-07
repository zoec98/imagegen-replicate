"""JSON API route registration and response shaping.

This module owns the `/api/*` route surface for the app-like UI. It keeps the
initial endpoints small and JSON-only so later tickets can replace the
placeholder request tracking with a real request state store and background
worker without changing browser-facing route names.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx
from flask import Flask, jsonify, request, url_for

from imagegen.app_version import app_checksum
from imagegen.filenames import safe_image_filename
from imagegen.gallery import (
    GalleryImage,
    count_gallery_images,
    list_gallery_images,
)
from imagegen.generation_log import GenerationLog
from imagegen.immich_client import ImmichClient, ImmichUploadError
from imagegen.image_imports import (
    ImageImportError,
    ImageImportFetchError,
    MAX_UPLOAD_BYTES,
    import_image_from_url,
    store_imported_image,
)
from imagegen.mask_store import MaskPayloadError, save_mask_payload
from imagegen.model_registry import (
    GenerationTarget,
    ProviderId,
    ProviderModel,
    RegistryLookupError,
    default_model_for_provider,
    list_models_for_provider,
    resolve_generation_target,
    resolve_model_ref,
)
from imagegen.palettes import (
    Palette,
    PaletteConflictError,
    PaletteError,
    PaletteFragment,
    PaletteNotFoundError,
    PaletteRepository,
)
from imagegen.prompt_annotations import strip_prompt_annotations
from imagegen.provider_requests import build_provider_request
from imagegen.request_store import GenerationRequest, RequestStore
from imagegen.security import require_api_csrf, require_multipart_api_csrf
from imagegen.trash import (
    count_trash_images,
    empty_trash,
    list_trash_images,
    move_gallery_image_to_trash,
    refresh_trash_count,
    restore_trash_image,
)
from imagegen.validation import ValidationError, validate_generation_payload
from imagegen.worker import GenerationWorker


def register_api_routes(app: Flask) -> None:
    @app.get("/api/app-version")
    def api_app_version():
        return jsonify({"app_checksum": app_checksum()})

    @app.post("/api/generate")
    @require_api_csrf
    def api_generate():
        payload = request.get_json(silent=True) or {}
        app_config = app.config["IMAGEGEN_APP_CONFIG"]
        try:
            selection = _selected_generation_model(payload, app_config=app_config)
        except ValidationError as error:
            return jsonify({"error": str(error)}), 400
        try:
            validated = validate_generation_payload(
                payload,
                model=selection.model,
                target=selection.target,
                output_dir=app_config.output_dir,
            )
        except ValidationError as error:
            return jsonify({"error": str(error)}), 400

        record = _request_store(app).create(
            provider=selection.provider,
            model_alias=selection.model.alias,
            prompt=validated.prompt,
            parameters=validated.parameters,
            source_images=validated.source_images,
            edit_mode=validated.edit_mode,
        )
        _generation_log(app).create_request(
            record,
            model_alias=selection.model.alias,
            model=selection.target.provider_model,
            replicate_input=_build_provider_request(
                strip_prompt_annotations(validated.prompt),
                selection.model,
                selection.target,
                parameters=validated.parameters,
                source_image_inputs=validated.source_images,
            ),
        )
        _generation_worker(app).start(record)
        return jsonify(_request_json(app, record)), 202

    @app.get("/api/generation/<request_id>")
    def api_generation_status(request_id: str):
        record = _request_store(app).get(request_id)
        if record is None:
            return jsonify({"error": "Generation request not found."}), 404
        return jsonify(_request_json(app, record))

    @app.get("/api/images")
    def api_images():
        app_config = app.config["IMAGEGEN_APP_CONFIG"]
        trash_count = _refresh_trash_count(app)
        images = list_gallery_images(
            app_config.output_dir,
            image_url=lambda filename: url_for("image_file", filename=filename),
            metadata_url=lambda filename: url_for(
                "image_metadata",
                filename=filename,
            ),
            metadata_provider=app.config["IMAGEGEN_METADATA_PROVIDER"],
        )
        return jsonify(
            {
                "images": [_gallery_image_json(app, image) for image in images],
                "trash_count": trash_count,
            }
        )

    @app.post("/api/images/import-url")
    @require_api_csrf
    def api_import_image_url():
        payload = request.get_json(silent=True) or {}
        app_config = app.config["IMAGEGEN_APP_CONFIG"]
        close_client = False
        http_client = _image_import_http_client(app)
        if http_client is None:
            http_client = httpx.Client(timeout=30.0, follow_redirects=False)
            close_client = True
        try:
            imported = import_image_from_url(
                payload.get("url") if isinstance(payload, dict) else None,
                output_dir=app_config.output_dir,
                client=http_client,
                max_bytes=app.config.get(
                    "IMAGEGEN_IMAGE_IMPORT_MAX_BYTES",
                    MAX_UPLOAD_BYTES,
                ),
            )
        except (ImageImportError, ImageImportFetchError) as error:
            return jsonify({"error": str(error)}), 400
        finally:
            if close_client:
                http_client.close()

        image = _gallery_image_by_filename(app, imported.path.name)
        return jsonify({"image": _gallery_image_json(app, image)}), 201

    @app.post("/api/images/import-upload")
    @require_multipart_api_csrf
    def api_import_uploaded_image():
        app_config = app.config["IMAGEGEN_APP_CONFIG"]
        files = [
            uploaded_file
            for field_name in request.files
            for uploaded_file in request.files.getlist(field_name)
        ]
        if not files:
            return jsonify({"error": "Image file is required."}), 400
        if len(files) > 1:
            return jsonify(
                {"error": "Only one image file can be uploaded at a time."}
            ), 400

        try:
            imported = store_imported_image(
                files[0].read(),
                output_dir=app_config.output_dir,
                max_bytes=app.config.get(
                    "IMAGEGEN_IMAGE_IMPORT_MAX_BYTES",
                    MAX_UPLOAD_BYTES,
                ),
            )
        except ImageImportError as error:
            return jsonify({"error": str(error)}), 400

        image = _gallery_image_by_filename(app, imported.path.name)
        return jsonify({"image": _gallery_image_json(app, image)}), 201

    @app.get("/api/trash")
    def api_trash():
        app_config = app.config["IMAGEGEN_APP_CONFIG"]
        _refresh_trash_count(app)
        images = list_trash_images(app_config.trash_dir)
        return jsonify(
            {
                "images": [_trash_image_json(path.name) for path in images],
                "trash_count": len(images),
            }
        )

    @app.post("/api/trash/<path:filename>/restore")
    @require_api_csrf
    def api_restore_trash_image(filename: str):
        app_config = app.config["IMAGEGEN_APP_CONFIG"]
        try:
            restored_path = restore_trash_image(
                filename,
                trash_dir=app_config.trash_dir,
                output_dir=app_config.output_dir,
            )
        except FileNotFoundError:
            return jsonify({"error": "Trash image not found."}), 404
        return jsonify(
            {
                "filename": restored_path.name,
                "image_count": count_gallery_images(app_config.output_dir),
                "trash_count": count_trash_images(app_config.trash_dir),
            }
        )

    @app.post("/api/trash/empty")
    @require_api_csrf
    def api_empty_trash():
        app_config = app.config["IMAGEGEN_APP_CONFIG"]
        deleted = empty_trash(app_config.trash_dir)
        return jsonify(
            {
                "deleted": [path.name for path in deleted],
                "image_count": count_gallery_images(app_config.output_dir),
                "trash_count": count_trash_images(app_config.trash_dir),
            }
        )

    @app.get("/api/palettes")
    def api_palettes():
        try:
            palettes = _palette_repository(app).list_palettes()
        except PaletteError as error:
            return jsonify({"error": str(error)}), 400
        return jsonify({"palettes": [_palette_json(palette) for palette in palettes]})

    @app.get("/api/palettes/<palette_name>/fragments/<fragment_name>")
    def api_palette_fragment(palette_name: str, fragment_name: str):
        try:
            fragment = _palette_repository(app).read_fragment(
                palette_name,
                fragment_name,
            )
        except PaletteNotFoundError as error:
            return jsonify({"error": str(error)}), 404
        except PaletteError as error:
            return jsonify({"error": str(error)}), 400
        return jsonify({"fragment": _palette_fragment_json(fragment)})

    @app.post("/api/palettes/<palette_name>/fragments")
    @require_api_csrf
    def api_create_palette_fragment(palette_name: str):
        payload = request.get_json(silent=True) or {}
        try:
            name, content = _fragment_payload(payload, require_name=True)
            fragment = _palette_repository(app).create_fragment(
                palette_name,
                name,
                content,
            )
        except PaletteNotFoundError as error:
            return jsonify({"error": str(error)}), 404
        except PaletteConflictError as error:
            return jsonify({"error": str(error)}), 409
        except PaletteError as error:
            return jsonify({"error": str(error)}), 400
        return jsonify({"fragment": _palette_fragment_json(fragment)}), 201

    @app.put("/api/palettes/<palette_name>/fragments/<fragment_name>")
    @require_api_csrf
    def api_update_palette_fragment(palette_name: str, fragment_name: str):
        payload = request.get_json(silent=True) or {}
        try:
            _, content = _fragment_payload(payload, require_name=False)
            fragment = _palette_repository(app).update_fragment(
                palette_name,
                fragment_name,
                content,
            )
        except PaletteNotFoundError as error:
            return jsonify({"error": str(error)}), 404
        except PaletteError as error:
            return jsonify({"error": str(error)}), 400
        return jsonify({"fragment": _palette_fragment_json(fragment)})

    @app.delete("/api/palettes/<palette_name>/fragments/<fragment_name>")
    @require_api_csrf
    def api_delete_palette_fragment(palette_name: str, fragment_name: str):
        try:
            _palette_repository(app).delete_fragment(palette_name, fragment_name)
        except PaletteNotFoundError as error:
            return jsonify({"error": str(error)}), 404
        except PaletteError as error:
            return jsonify({"error": str(error)}), 400
        return jsonify({"deleted": fragment_name})

    @app.post("/api/images/<path:filename>/immich-upload")
    @require_api_csrf
    def api_immich_upload(filename: str):
        if not _immich_enabled(app):
            return jsonify({"error": "Immich upload is not configured."}), 404
        safe_name = safe_image_filename(filename)
        if safe_name is None:
            return jsonify({"error": "Image not found."}), 404
        image_path = app.config["IMAGEGEN_APP_CONFIG"].output_dir / safe_name
        if not image_path.is_file():
            return jsonify({"error": "Image not found."}), 404
        try:
            result = _immich_client(app).upload_image(image_path)
        except ImmichUploadError as error:
            return jsonify({"error": str(error)}), 502
        return jsonify({"filename": safe_name, "status": result.status})

    @app.post("/api/images/<path:filename>/delete")
    @require_api_csrf
    def api_delete_image(filename: str):
        safe_name = safe_image_filename(filename)
        if safe_name is None:
            return jsonify({"error": "Image not found."}), 404
        app_config = app.config["IMAGEGEN_APP_CONFIG"]
        try:
            move_gallery_image_to_trash(
                safe_name,
                output_dir=app_config.output_dir,
                trash_dir=app_config.trash_dir,
            )
        except FileNotFoundError:
            return jsonify({"error": "Image not found."}), 404
        return jsonify({"deleted": safe_name})

    @app.post("/api/images/<path:filename>/mask")
    @require_api_csrf
    def api_save_mask(filename: str):
        safe_name = safe_image_filename(filename)
        if safe_name is None:
            return jsonify({"error": "Image not found."}), 404
        app_config = app.config["IMAGEGEN_APP_CONFIG"]
        source_path = app_config.output_dir / safe_name
        if not source_path.is_file():
            return jsonify({"error": "Image not found."}), 404

        try:
            payload = request.get_json(silent=True) or {}
            saved_name = save_mask_payload(
                payload,
                source_filename=safe_name,
                source_path=source_path,
                output_dir=app_config.output_dir,
                content_length=request.content_length,
            )
        except MaskPayloadError as error:
            return jsonify({"error": str(error)}), 400
        return (
            jsonify(
                {
                    "filename": saved_name,
                    "url": url_for("image_file", filename=saved_name),
                }
            ),
            201,
        )

    if app.config.get("IMAGEGEN_ENABLE_TEST_API"):

        @app.post("/api/_test")
        @require_api_csrf
        def api_test():
            return jsonify({"ok": True})


def _request_store(app: Flask) -> RequestStore:
    store = app.config["IMAGEGEN_REQUEST_STORE"]
    if not isinstance(store, RequestStore):
        msg = "IMAGEGEN_REQUEST_STORE must be a RequestStore instance."
        raise TypeError(msg)
    return store


def _generation_worker(app: Flask) -> GenerationWorker:
    worker = app.config["IMAGEGEN_WORKER"]
    if not hasattr(worker, "start"):
        msg = "IMAGEGEN_WORKER must provide a start(request_record) method."
        raise TypeError(msg)
    return worker


def _generation_log(app: Flask) -> GenerationLog:
    generation_log = app.config["IMAGEGEN_GENERATION_LOG"]
    if not hasattr(generation_log, "create_request"):
        msg = "IMAGEGEN_GENERATION_LOG must provide generation log methods."
        raise TypeError(msg)
    return generation_log


def _palette_repository(app: Flask) -> PaletteRepository:
    return PaletteRepository(app.config["IMAGEGEN_APP_CONFIG"].fragment_root)


def _fragment_payload(
    payload: object,
    *,
    require_name: bool,
) -> tuple[str, str]:
    if not isinstance(payload, dict):
        raise PaletteError("Palette fragment payload must be an object.")
    name = payload.get("name", "")
    content = payload.get("content", "")
    if require_name and not isinstance(name, str):
        raise PaletteError("Fragment name is required.")
    if not isinstance(content, str):
        raise PaletteError("Fragment content must be a string.")
    return str(name), content


def _immich_enabled(app: Flask) -> bool:
    return bool(app.config["IMAGEGEN_APP_CONFIG"].immich_enabled)


def _refresh_trash_count(app: Flask) -> int:
    app_config = app.config["IMAGEGEN_APP_CONFIG"]
    return refresh_trash_count(
        app_config.trash_dir,
        retention_days=app_config.trashcan_hold_limit_days,
    )


def _image_import_http_client(app: Flask) -> httpx.Client | None:
    configured = app.config.get("IMAGEGEN_IMAGE_IMPORT_HTTP_CLIENT")
    if configured is None:
        return None
    if not hasattr(configured, "stream"):
        msg = "IMAGEGEN_IMAGE_IMPORT_HTTP_CLIENT must provide stream(...)."
        raise TypeError(msg)
    return configured


def _immich_client(app: Flask) -> ImmichClient:
    configured = app.config.get("IMAGEGEN_IMMICH_CLIENT")
    if configured is not None:
        if not hasattr(configured, "upload_image"):
            msg = "IMAGEGEN_IMMICH_CLIENT must provide upload_image(image_path)."
            raise TypeError(msg)
        return configured
    app_config = app.config["IMAGEGEN_APP_CONFIG"]
    return ImmichClient(
        base_url=app_config.immich_url,
        api_key=app_config.immich_api_key,
        album_id=app_config.immich_gallery_id,
    )


@dataclass(frozen=True)
class SelectedGenerationModel:
    provider: ProviderId
    model: ProviderModel
    target: GenerationTarget


def _selected_generation_model(
    payload: dict[str, object],
    *,
    app_config,
) -> SelectedGenerationModel:
    provider = _selected_provider(payload, app_config=app_config)
    edit_mode = _selected_edit_mode(payload)
    model = _selected_provider_model(payload, provider=provider)
    try:
        target = resolve_generation_target(
            provider,
            model.alias,
            edit_mode=edit_mode,
        )
    except RegistryLookupError as error:
        raise ValidationError(str(error)) from error
    return SelectedGenerationModel(provider=provider, model=model, target=target)


def _selected_provider(payload: dict[str, object], *, app_config) -> ProviderId:
    if not app_config.enabled_providers:
        raise ValidationError("No image generation provider is configured.")
    raw_provider = payload.get("provider", app_config.selected_provider)
    if raw_provider is None:
        raise ValidationError("No image generation provider is configured.")
    if not isinstance(raw_provider, str) or not raw_provider.strip():
        raise ValidationError("provider must be a valid provider id.")
    provider = raw_provider.strip()
    if provider not in {"replicate", "falai"}:
        choices = ", ".join(app_config.enabled_providers)
        raise ValidationError(
            f"Unknown provider: {provider}. Expected one of: {choices}."
        )
    if provider not in app_config.enabled_providers:
        raise ValidationError(f"Provider `{provider}` is not enabled.")
    return provider


def _selected_edit_mode(payload: dict[str, object]) -> bool:
    edit_mode = payload.get("edit_mode", False)
    if not isinstance(edit_mode, bool):
        raise ValidationError("edit_mode must be a boolean.")
    return edit_mode


def _selected_provider_model(
    payload: dict[str, object],
    *,
    provider: ProviderId,
) -> ProviderModel:
    raw_model = payload.get("model")
    if raw_model is None:
        model = default_model_for_provider(provider)
        if model is None:
            raise ValidationError(f"Provider `{provider}` has no configured models.")
        return model
    if not isinstance(raw_model, str) or not raw_model.strip():
        raise ValidationError("model must be a valid model id.")
    model_ref = raw_model.strip()
    try:
        model = resolve_model_ref(model_ref, selected_provider=provider)
    except RegistryLookupError as error:
        if ":" not in model_ref:
            choices = ", ".join(
                provider_model.alias
                for provider_model in list_models_for_provider(provider)
            )
            raise ValidationError(
                f"Unknown model: {model_ref}. Expected one of: {choices}."
            ) from error
        raise ValidationError(str(error)) from error
    if model.provider != provider:
        raise ValidationError(
            f"Model `{model_ref}` does not belong to provider `{provider}`."
        )
    return model


def _build_provider_request(
    prompt: str,
    model: ProviderModel,
    target: GenerationTarget,
    *,
    parameters: dict[str, object] | None = None,
    source_image_inputs: list[object] | None = None,
) -> dict[str, object]:
    return build_provider_request(
        prompt,
        model,
        target,
        parameters=parameters,
        source_image_inputs=source_image_inputs,
    )


def _request_json(app: Flask, record: GenerationRequest) -> dict[str, object]:
    payload = record.to_json()
    payload["status_url"] = url_for(
        "api_generation_status",
        request_id=record.request_id,
    )
    payload["poll_seconds"] = app.config["IMAGEGEN_APP_CONFIG"].replicate_poll_seconds
    return payload


def _gallery_image_json(app: Flask, image: GalleryImage) -> dict[str, str | None]:
    payload = {
        "filename": image.filename,
        "url": image.url,
        "mask_url": image.mask_url,
        "mask_save_url": url_for("api_save_mask", filename=image.filename),
        "download_url": url_for("image_download", filename=image.filename),
        "clean_download_url": url_for(
            "image_download_clean",
            filename=image.filename,
        ),
        "delete_url": url_for("api_delete_image", filename=image.filename),
        "metadata_url": image.metadata_url,
        "content_type": image.content_type,
        "created_at": image.created_at,
    }
    app_config = app.config["IMAGEGEN_APP_CONFIG"]
    if app_config.immich_enabled:
        payload["immich_upload_url"] = url_for(
            "api_immich_upload",
            filename=image.filename,
        )
    return payload


def _gallery_image_by_filename(app: Flask, filename: str) -> GalleryImage:
    app_config = app.config["IMAGEGEN_APP_CONFIG"]
    images = list_gallery_images(
        app_config.output_dir,
        image_url=lambda image_filename: url_for(
            "image_file",
            filename=image_filename,
        ),
        metadata_url=lambda image_filename: url_for(
            "image_metadata",
            filename=image_filename,
        ),
        metadata_provider=app.config["IMAGEGEN_METADATA_PROVIDER"],
    )
    for image in images:
        if image.filename == filename:
            return image
    raise FileNotFoundError(filename)


def _trash_image_json(filename: str) -> dict[str, str]:
    return {
        "filename": filename,
        "url": url_for("trash_file", filename=filename),
        "restore_url": url_for("api_restore_trash_image", filename=filename),
    }


def _palette_json(palette: Palette) -> dict[str, object]:
    return {
        "name": palette.name,
        "display_name": palette.display_name,
        "fragments": [
            _palette_fragment_json(fragment) for fragment in palette.fragments
        ],
    }


def _palette_fragment_json(fragment: PaletteFragment) -> dict[str, str]:
    return {
        "name": fragment.name,
        "display_name": fragment.display_name,
        "content": fragment.content,
    }
