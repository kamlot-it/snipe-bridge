from __future__ import annotations

import pytest

from server.snipe import SnipeClient, SnipeError


class FakeResponse:
    def __init__(self, payload, status_code=200, headers=None, content=b""):
        self._payload = payload
        self.status_code = status_code
        self.headers = headers or {}
        self.content = content

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self):
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if url.endswith("/hardware/64"):
            return FakeResponse(
                {
                    "id": 64,
                    "asset_tag": "IT-0064",
                    "serial": "SN-0064",
                    "model": {"id": 5, "name": "Zoom H6"},
                    "assigned_to": {"id": 7, "name": "Jan Kowalski"},
                    "status_label": {
                        "name": "Wydane",
                        "status_meta": "Przypisany",
                    },
                }
            )
        if url.endswith("/hardware/bytag/UAM-42") or url.endswith(
            "/hardware/byserial/UAM-42"
        ):
            return FakeResponse({"status": "error", "messages": "not found"}, 404)
        if url.endswith("/hardware"):
            params = kwargs.get("params", {})
            if params.get("search") == "UAM-42":
                return FakeResponse(
                    {
                        "rows": [
                            {
                                "id": 42,
                                "asset_tag": "IT-0042",
                                "serial": "SN-0042",
                                "name": "Dell Latitude",
                                "status_label": {
                                    "name": "Wydane",
                                    "status_meta": "deployable",
                                },
                                "assigned_to": None,
                                "custom_fields": {
                                    "UAM Asset Tag": {
                                        "field": "_snipeit_inventory_tag_1",
                                        "value": "UAM-42",
                                    }
                                },
                            }
                        ]
                    }
                )
            return FakeResponse({"rows": []})
        if url.endswith("/statuslabels"):
            params = kwargs.get("params", {})
            name = params.get("search")
            rows = [
                {"id": 12, "name": "Wydane", "type": "deployable"},
                {"id": 13, "name": "Gotowy", "type": "deployable"},
            ]
            if params.get("limit") == 500:
                return FakeResponse({"rows": rows})
            if name == "Wydane":
                return FakeResponse({"rows": rows[:1]})
            return FakeResponse({"rows": []})
        if url.endswith("/users"):
            email = kwargs.get("params", {}).get("email")
            if email == "operator@example.org":
                return FakeResponse(
                    {
                        "rows": [
                            {
                                "id": 9,
                                "name": "Operator Meteor",
                                "email": "operator@example.org",
                            }
                        ]
                    }
                )
            return FakeResponse({"rows": []})
        if url.endswith("/hardware/42/checkout"):
            return FakeResponse({"status": "success", "messages": "ok"})
        if url.endswith("/hardware/42/checkin"):
            return FakeResponse({"status": "success", "messages": "ok"})
        raise AssertionError(f"Nieoczekiwane żądanie: {method} {url}")


def make_client():
    client = SnipeClient(
        "https://snipe.example.test",
        "token",
        "_snipeit_inventory_tag_1",
    )
    client.session = FakeSession()
    return client


def test_resolves_exact_custom_field_via_search_fallback():
    client = make_client()
    resolution = client.resolve_asset("UAM-42")

    assert resolution.status == "matched"
    assert resolution.candidates[0]["id"] == 42
    assert resolution.candidates[0]["_bridge_uam_asset_tag"] == "UAM-42"
    assert resolution.match_fields == {42: ["UAM Asset Tag"]}
    assert any(
        (call[2].get("params") or {}).get("search") == "UAM-42"
        for call in client.session.calls
    )


def test_resolves_snipe_hardware_qr_url_by_hardware_path():
    client = make_client()

    resolution = client.resolve_asset("https://snipe.example.test/hardware/64")

    assert resolution.status == "matched"
    assert resolution.candidates[0]["id"] == 64
    assert resolution.match_fields == {64: ["QR Snipe-IT"]}
    assert client._snipe_hardware_url_id("https://other.example/hardware/64") == 64
    assert client._snipe_hardware_url_id("https://snipe.example.test/users/64") is None


@pytest.mark.parametrize(
    "scanned_value",
    [
        "https://snipe.example.test/hardware/64?source=qr",
        "https://snipe.example.test/hardware/64#asset",
        "\ufeffhttps://snipe.example.test/hardware/64\x1d",
        '"https://snipe.example.test/hardware/64"',
        "http://snipe.example.test/hardware/64",
        "prefix https://different.example/hardware/64/details suffix",
        "https://different.example/hard ware/64".replace("hard ware", "hardware "),
    ],
)
def test_hardware_qr_tolerates_scanner_framing_and_safe_url_variants(scanned_value):
    client = make_client()
    resolution = client.resolve_asset(scanned_value)
    assert resolution.status == "matched"
    assert resolution.candidates[0]["id"] == 64
    assert resolution.match_fields == {64: ["QR Snipe-IT"]}


def test_hardware_qr_uses_id_even_when_original_host_is_different():
    client = make_client()
    resolution = client.resolve_asset("https://other.example.test/hardware/64")
    assert resolution.status == "matched"
    assert resolution.candidates[0]["id"] == 64


def test_exact_status_and_user_email_lookup():
    client = make_client()

    assert client.get_status_label_exact("Wydane")["id"] == 12
    assert client.find_user_by_email("operator@example.org")["id"] == 9
    with pytest.raises(SnipeError, match="Brak statusu"):
        client.get_status_label_exact("Nie istnieje")


def test_lists_status_labels_for_settings_dropdowns():
    client = make_client()
    assert [item["name"] for item in client.list_status_labels()] == [
        "Gotowy",
        "Wydane",
    ]


def test_checkout_uses_user_status_and_operator_note():
    client = make_client()
    client.checkout_asset(
        42, 7, 12, "Snipe Bridge MC319Z; operator: operator@example.test"
    )

    method, url, kwargs = client.session.calls[-1]
    assert method == "POST"
    assert url.endswith("/hardware/42/checkout")
    assert kwargs["json"]["checkout_to_type"] == "user"
    assert kwargs["json"]["assigned_user"] == 7
    assert kwargs["json"]["status_id"] == 12
    assert "operator@example.test" in kwargs["json"]["note"]


def test_checkin_uses_status_and_required_note():
    client = make_client()
    client.checkin_asset(42, 13, "Wymaga serwisu")

    method, url, kwargs = client.session.calls[-1]
    assert method == "POST"
    assert url.endswith("/hardware/42/checkin")
    assert kwargs["json"] == {"status_id": 13, "note": "Wymaga serwisu"}


def test_checkin_guard_requires_assignment_and_allowed_status():
    allowed = ("Wydane", "Gotowy do wydania")
    assert (
        SnipeClient.checkin_block_reason(
                {
                    "assigned_to": {"id": 7},
                    "status_label": {
                        "name": "Wydane",
                        "status_meta": "Przypisany",
                    },
            },
            allowed,
        )
        is None
    )
    assert "nie jest przypisany" in SnipeClient.checkin_block_reason(
        {"assigned_to": None, "status_label": {"name": "Wydane"}}, allowed
    )
    assert "Nie można przyjąć" in SnipeClient.checkin_block_reason(
        {
            "assigned_to": {"id": 7},
            "status_label": {"name": "W serwisie"},
        },
        allowed,
    )
    assert "meta statusem" in SnipeClient.checkin_block_reason(
        {
            "assigned_to": {"id": 7},
            "status_label": {"name": "Wydane", "status_meta": "Gotowy"},
        },
        allowed,
    )


def test_checkout_rejects_snipe_error_inside_http_200():
    client = make_client()

    def rejected_request(method, url, **kwargs):
        return FakeResponse({"status": "error", "messages": "already assigned"})

    client.session.request = rejected_request
    with pytest.raises(SnipeError, match="already assigned"):
        client.checkout_asset(42, 7, 12, "test")
