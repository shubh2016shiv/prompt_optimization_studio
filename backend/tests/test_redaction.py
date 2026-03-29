from app.observability.redaction import redact_sensitive_data


def test_redacts_nested_secret_keys_case_insensitive():
    payload = {
        "api_key": "secret",
        "Authorization": "Bearer abc123",
        "nested": {
            "X-API-KEY": "value",
            "toKen": "tok-value",
            "safe": "hello",
        },
    }

    redacted = redact_sensitive_data(payload)

    assert redacted["api_key"] == "***REDACTED***"
    assert redacted["Authorization"] == "***REDACTED***"
    assert redacted["nested"]["X-API-KEY"] == "***REDACTED***"
    assert redacted["nested"]["toKen"] == "***REDACTED***"
    assert redacted["nested"]["safe"] == "hello"


def test_redacts_bearer_string_without_losing_other_text():
    payload = {
        "headers": {
            "custom": "Authorization: Bearer abc123xyz and extra",
        }
    }

    redacted = redact_sensitive_data(payload)
    assert "Bearer ***REDACTED***" in redacted["headers"]["custom"]


def test_does_not_mutate_non_secret_fields():
    payload = {
        "raw_prompt": "Analyze contracts",
        "answers": ["a", "b"],
    }

    redacted = redact_sensitive_data(payload)
    assert redacted == payload
