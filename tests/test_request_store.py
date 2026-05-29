from imagegen.request_store import RequestStore


def test_request_store_creates_and_gets_queued_request():
    store = RequestStore()

    record = store.create(
        prompt="a small red house",
        parameters={"size": "2K"},
    )

    assert record.request_id
    assert record.status == "queued"
    assert record.prompt == "a small red house"
    assert record.parameters == {"size": "2K"}
    assert record.error is None
    assert record.prediction_id is None
    assert record.output_urls == []
    assert record.images == []
    assert store.get(record.request_id) is record


def test_request_store_unknown_request_returns_none():
    store = RequestStore()

    assert store.get("missing") is None
    assert store.update("missing", status="running") is None


def test_request_store_status_transition_preserves_submission_data():
    store = RequestStore()
    record = store.create(prompt="prompt", parameters={"max_images": 1})

    updated = store.update(
        record.request_id,
        status="running",
        prediction_id="prediction-123",
        logs=["prediction created"],
    )

    assert updated is record
    assert record.status == "running"
    assert record.prompt == "prompt"
    assert record.parameters == {"max_images": 1}
    assert record.prediction_id == "prediction-123"
    assert record.logs == ["prediction created"]
    assert record.updated_at >= record.created_at


def test_request_store_succeeded_request_tracks_outputs_and_images():
    store = RequestStore()
    record = store.create(prompt="prompt", parameters={})

    store.update(
        record.request_id,
        status="succeeded",
        output_urls=["https://example.test/image.png"],
        images=["seedream45-prediction-01.png"],
    )

    assert record.status == "succeeded"
    assert record.output_urls == ["https://example.test/image.png"]
    assert record.images == ["seedream45-prediction-01.png"]


def test_request_store_failed_request_keeps_displayable_error():
    store = RequestStore()
    record = store.create(prompt="prompt", parameters={})

    store.update(record.request_id, status="failed", error="Replicate failed.")

    assert record.status == "failed"
    assert record.error == "Replicate failed."


def test_request_store_timeout_request_keeps_displayable_error():
    store = RequestStore()
    record = store.create(prompt="prompt", parameters={})

    store.update(record.request_id, status="timeout", error="Timed out.")

    assert record.status == "timeout"
    assert record.error == "Timed out."


def test_request_store_json_contains_lifecycle_fields():
    store = RequestStore()
    record = store.create(prompt="prompt", parameters={"size": "2K"})
    store.update(record.request_id, status="running", prediction_id="prediction-123")

    payload = record.to_json()

    assert payload["request_id"] == record.request_id
    assert payload["status"] == "running"
    assert payload["prompt"] == "prompt"
    assert payload["parameters"] == {"size": "2K"}
    assert payload["error"] is None
    assert payload["prediction_id"] == "prediction-123"
    assert payload["output_urls"] == []
    assert payload["images"] == []
    assert payload["logs"] == []
    assert payload["created_at"]
    assert payload["updated_at"]
