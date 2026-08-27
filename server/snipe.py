from __future__ import annotations

import json
import re
import time
import unicodedata
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote, unquote, urljoin, urlparse

import requests


class SnipeError(RuntimeError):
    pass


@dataclass
class Resolution:
    status: str
    candidates: list[dict[str, Any]]
    match_fields: dict[int, list[str]]


class SnipeClient:
    def __init__(
        self,
        base_url: str,
        token: str,
        custom_field: str,
        timeout: float = 12,
        verify_tls: bool = True,
        session: requests.Session | None = None,
        status_cache_seconds: int = 300,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token.strip()
        self.custom_field = custom_field
        self.timeout = timeout
        self.verify_tls = verify_tls
        self.session = session or requests.Session()
        self.status_cache_seconds = max(0, int(status_cache_seconds))
        self._status_cache: dict[str, tuple[float, dict[str, Any]]] = {}

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> Any:
        if not self.token or self.token.startswith("wklej_"):
            raise SnipeError("Brak skonfigurowanego tokenu API Snipe-IT.")
        try:
            response = self.session.request(
                method,
                f"{self.base_url}/api/v1{path}",
                params=params,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                timeout=self.timeout,
                verify=self.verify_tls,
            )
        except requests.RequestException as exc:
            raise SnipeError(f"Błąd połączenia z Snipe-IT: {exc}") from exc

        try:
            body = response.json()
        except ValueError as exc:
            raise SnipeError(
                f"Snipe-IT zwrócił nieprawidłową odpowiedź HTTP {response.status_code}."
            ) from exc

        if response.status_code == 401:
            raise SnipeError("Token API został odrzucony przez Snipe-IT.")
        if response.status_code == 403:
            raise SnipeError("Konto API nie ma wymaganych uprawnień.")
        if response.status_code >= 400:
            raise SnipeError(f"Snipe-IT zwrócił HTTP {response.status_code}.")
        return body

    @staticmethod
    def _records(body: Any) -> list[dict[str, Any]]:
        if isinstance(body, list):
            return [item for item in body if isinstance(item, dict)]
        if not isinstance(body, dict):
            return []
        if body.get("status") == "error":
            return []
        rows = body.get("rows")
        if isinstance(rows, list):
            return [item for item in rows if isinstance(item, dict)]
        if body.get("id") is not None:
            return [body]
        return []

    @staticmethod
    def _normalize(value: Any) -> str:
        return str(value or "").strip().casefold()

    @staticmethod
    def _clean_scan_value(value: Any) -> str:
        """Remove scanner framing characters without changing visible payload."""
        cleaned = "".join(
            character
            for character in str(value or "")
            if not unicodedata.category(character).startswith("C")
        ).strip()
        if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {"'", '"'}:
            cleaned = cleaned[1:-1].strip()
        return cleaned

    def _custom_value(self, asset: dict[str, Any]) -> str:
        custom_fields = asset.get("custom_fields") or {}
        if isinstance(custom_fields, dict):
            direct = custom_fields.get(self.custom_field)
            if isinstance(direct, dict):
                return str(direct.get("value") or "")
            if direct is not None:
                return str(direct)
            for label, details in custom_fields.items():
                if isinstance(details, dict):
                    field_key = details.get("field") or details.get("db_column")
                    if field_key == self.custom_field or label == self.custom_field:
                        return str(details.get("value") or "")
        if isinstance(custom_fields, list):
            for details in custom_fields:
                if isinstance(details, dict) and (
                    details.get("field") == self.custom_field
                    or details.get("db_column") == self.custom_field
                ):
                    return str(details.get("value") or "")
        return ""

    @staticmethod
    def user_display_name(user: dict[str, Any]) -> str:
        name = str(user.get("name") or "").strip()
        if name:
            return name
        first = str(user.get("first_name") or "").strip()
        last = str(user.get("last_name") or "").strip()
        return f"{first} {last}".strip() or str(user.get("username") or user.get("id"))

    def test_connection(self) -> None:
        self._request("GET", "/hardware", params={"limit": 1})
        self._request("GET", "/users", params={"limit": 1})
        self._request("GET", "/statuslabels", params={"limit": 1})

    def list_status_labels(self) -> list[dict[str, Any]]:
        """Return all usable Snipe-IT status labels for administrator selects."""
        body = self._request(
            "GET",
            "/statuslabels",
            params={"limit": 500, "sort": "name", "order": "asc"},
        )
        labels: list[dict[str, Any]] = []
        for item in self._records(body):
            name = str(item.get("name") or "").strip()
            try:
                status_id = int(item["id"])
            except (KeyError, TypeError, ValueError):
                continue
            if not name:
                continue
            labels.append(
                {
                    "id": status_id,
                    "name": name,
                    "type": str(item.get("type") or "").strip(),
                }
            )
        return sorted(labels, key=lambda item: item["name"].casefold())

    def search_users(self, query: str) -> list[dict[str, Any]]:
        body = self._request(
            "GET", "/users", params={"search": query.strip(), "limit": 25}
        )
        return self._records(body)

    def get_user(self, user_id: int) -> dict[str, Any]:
        body = self._request("GET", f"/users/{user_id}")
        records = self._records(body)
        if len(records) != 1:
            raise SnipeError("Nie znaleziono wybranego użytkownika.")
        return records[0]

    def get_asset(self, asset_id: int) -> dict[str, Any]:
        body = self._request("GET", f"/hardware/{asset_id}")
        records = self._records(body)
        if len(records) != 1:
            raise SnipeError("Nie znaleziono sprzętu wskazanego przez kod QR.")
        asset = records[0]
        asset["_bridge_uam_asset_tag"] = self._custom_value(asset).strip()
        return asset

    def find_user_by_email(self, email: str) -> dict[str, Any]:
        wanted = email.strip()
        body = self._request(
            "GET", "/users", params={"email": wanted, "limit": 100}
        )
        matches = [
            user
            for user in self._records(body)
            if self._normalize(user.get("email")) == self._normalize(wanted)
        ]
        if not matches:
            raise SnipeError(
                "Konto dostawcy tożsamości nie ma odpowiadającego użytkownika w Snipe-IT."
            )
        if len(matches) > 1:
            raise SnipeError(
                "W Snipe-IT istnieje więcej niż jedno konto z tym adresem e-mail."
            )
        return matches[0]

    def get_status_label_exact(self, name: str) -> dict[str, Any]:
        wanted = name.strip()
        cache_key = self._normalize(wanted)
        cached = self._status_cache.get(cache_key)
        if cached and cached[0] > time.time():
            return dict(cached[1])
        body = self._request(
            "GET", "/statuslabels", params={"search": wanted, "limit": 100}
        )
        matches = [
            label
            for label in self._records(body)
            if self._normalize(label.get("name")) == self._normalize(wanted)
        ]
        if not matches:
            raise SnipeError(f"Brak statusu „{wanted}” w Snipe-IT.")
        if len(matches) > 1:
            raise SnipeError(f"Status „{wanted}” nie jest jednoznaczny w Snipe-IT.")
        try:
            int(matches[0]["id"])
        except (KeyError, TypeError, ValueError) as exc:
            raise SnipeError(f"Status „{wanted}” nie ma prawidłowego ID.") from exc
        result = dict(matches[0])
        if self.status_cache_seconds > 0:
            self._status_cache[cache_key] = (
                time.time() + self.status_cache_seconds,
                dict(result),
            )
        return result

    def _exact_matches(
        self, records: list[dict[str, Any]], field: str, value: str
    ) -> list[dict[str, Any]]:
        wanted = self._normalize(value)
        if field == self.custom_field:
            return [
                asset
                for asset in records
                if self._normalize(self._custom_value(asset)) == wanted
            ]
        return [
            asset
            for asset in records
            if self._normalize(asset.get(field)) == wanted
        ]

    def resolve_asset(self, scan_value: str) -> Resolution:
        code = self._clean_scan_value(scan_value)
        if not code:
            return Resolution("not_found", [], {})

        qr_asset_id = self._snipe_hardware_url_id(code)
        if qr_asset_id is not None:
            asset = self.get_asset(qr_asset_id)
            return Resolution(
                "matched", [asset], {int(asset["id"]): ["QR Snipe-IT"]}
            )

        found: dict[int, dict[str, Any]] = {}
        matches: dict[int, list[str]] = {}

        successful_queries = 0
        last_error: SnipeError | None = None
        lookups = (
            ("Asset Tag", "asset_tag", f"/hardware/bytag/{quote(code, safe='')}"),
            ("Serial Number", "serial", f"/hardware/byserial/{quote(code, safe='')}"),
        )
        for label, field, path in lookups:
            try:
                body = self._request("GET", path)
                successful_queries += 1
            except SnipeError as exc:
                # Brak w jednym indeksie nie może przerwać szukania w pozostałych.
                last_error = exc
                continue
            for asset in self._exact_matches(self._records(body), field, code):
                asset_id = int(asset["id"])
                found[asset_id] = asset
                matches.setdefault(asset_id, []).append(label)

        filter_value = json.dumps(
            {self.custom_field: f"is:{code}"}, ensure_ascii=False, separators=(",", ":")
        )
        custom_queries = (
            {self.custom_field: code, "limit": 100},
            {"filter": filter_value, "limit": 100},
            {"search": code, "limit": 100},
        )
        custom_matches: list[dict[str, Any]] = []
        for params in custom_queries:
            try:
                body = self._request("GET", "/hardware", params=params)
                successful_queries += 1
            except SnipeError as exc:
                last_error = exc
                continue
            custom_matches = self._exact_matches(
                self._records(body), self.custom_field, code
            )
            if custom_matches:
                break

        for asset in custom_matches:
            asset_id = int(asset["id"])
            found[asset_id] = asset
            matches.setdefault(asset_id, []).append("UAM Asset Tag")

        if successful_queries == 0 and last_error:
            raise last_error

        candidates = list(found.values())
        for asset in candidates:
            asset["_bridge_uam_asset_tag"] = self._custom_value(asset).strip()
        if not candidates:
            status = "not_found"
        elif len(candidates) == 1:
            status = "matched"
        else:
            status = "ambiguous"
        return Resolution(status, candidates, matches)

    def _snipe_hardware_url_id(self, value: str) -> int | None:
        """Extract a numeric asset ID from a scanned /hardware/<id> segment."""
        cleaned = self._clean_scan_value(value)
        decoded = unquote(cleaned)
        # Some legacy scanner/browser combinations insert visible whitespace
        # into a long URL. It is not meaningful inside a URL and must not stop
        # recognition of the Snipe-IT hardware path.
        compact = re.sub(r"\s+", "", decoded)
        match = re.search(r"/hardware/([0-9]+)", compact, re.IGNORECASE)
        return int(match.group(1)) if match else None

    @staticmethod
    def asset_image_url(asset: dict[str, Any]) -> str:
        value = asset.get("image")
        if isinstance(value, dict):
            value = value.get("url") or value.get("image") or value.get("src")
        return str(value or "").strip()

    def fetch_asset_image(self, asset: dict[str, Any], max_bytes: int = 8_000_000) -> bytes:
        image_value = self.asset_image_url(asset)
        if not image_value:
            raise SnipeError("Sprzęt nie ma zdjęcia.")

        image_url = urljoin(f"{self.base_url}/", image_value)
        parsed = urlparse(image_url)
        expected = urlparse(self.base_url)
        if (
            parsed.scheme.casefold() != expected.scheme.casefold()
            or parsed.netloc.casefold() != expected.netloc.casefold()
        ):
            raise SnipeError("Adres zdjęcia nie należy do skonfigurowanego Snipe-IT.")

        try:
            response = self.session.request(
                "GET",
                image_url,
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Accept": "image/*",
                },
                timeout=self.timeout,
                verify=self.verify_tls,
            )
        except requests.RequestException as exc:
            raise SnipeError(f"Nie udało się pobrać zdjęcia sprzętu: {exc}") from exc

        content_type = str(response.headers.get("Content-Type") or "").split(";", 1)[0]
        if response.status_code >= 400 or not content_type.startswith("image/"):
            raise SnipeError("Snipe-IT nie zwrócił prawidłowego zdjęcia sprzętu.")
        content = bytes(response.content)
        if not content or len(content) > max_bytes:
            raise SnipeError("Zdjęcie sprzętu jest puste albo zbyt duże.")
        return content

    @staticmethod
    def checkout_block_reason(asset: dict[str, Any]) -> str | None:
        assigned_to = asset.get("assigned_to")
        if assigned_to:
            if isinstance(assigned_to, dict):
                name = assigned_to.get("name") or assigned_to.get("username")
                return f"Sprzęt jest już przypisany: {name or 'inny odbiorca'}."
            return "Sprzęt jest już przypisany."

        available_actions = asset.get("available_actions")
        if isinstance(available_actions, dict) and available_actions.get("checkout") is False:
            return "Status sprzętu nie pozwala na wydanie."
        if asset.get("user_can_checkout") is False:
            return "Snipe-IT nie pozwala wydać tego sprzętu."
        return None

    @classmethod
    def asset_status_name(cls, asset: dict[str, Any]) -> str:
        status = asset.get("status_label") or asset.get("status")
        if isinstance(status, dict):
            return str(status.get("name") or "").strip()
        return str(status or "").strip()

    @classmethod
    def asset_status_meta(cls, asset: dict[str, Any]) -> str:
        status = asset.get("status_label") or asset.get("status")
        if isinstance(status, dict):
            return str(status.get("status_meta") or "").strip()
        return ""

    @staticmethod
    def assigned_display_name(asset: dict[str, Any]) -> str:
        assigned = asset.get("assigned_to")
        if isinstance(assigned, dict):
            return str(
                assigned.get("name")
                or assigned.get("username")
                or assigned.get("email")
                or assigned.get("id")
                or ""
            ).strip()
        return str(assigned or "").strip()

    @classmethod
    def checkin_block_reason(
        cls, asset: dict[str, Any], allowed_status_names: tuple[str, ...]
    ) -> str | None:
        if not asset.get("assigned_to"):
            return "Sprzęt nie jest przypisany. Nie można go przyjąć."

        current_status = cls.asset_status_name(asset)
        allowed = {cls._normalize(name) for name in allowed_status_names}
        if cls._normalize(current_status) not in allowed:
            label = current_status or "brak statusu"
            allowed_display = " lub ".join(f"„{name}”" for name in allowed_status_names)
            return (
                f"Nie można przyjąć sprzętu ze statusem „{label}”. "
                f"Dozwolony status: {allowed_display}, a sprzęt musi być przypisany."
            )
        current_meta = cls._normalize(cls.asset_status_meta(asset))
        if current_meta not in {"deployed", "assigned", "przypisany"}:
            label = cls.asset_status_meta(asset) or "brak"
            return (
                f"Nie można przyjąć sprzętu z meta statusem „{label}”. "
                "Wymagany meta status: „Przypisany”."
            )
        return None

    @staticmethod
    def _require_success(body: Any, fallback: str) -> dict[str, Any]:
        if isinstance(body, dict) and body.get("status") == "success":
            return body
        message = body.get("messages") if isinstance(body, dict) else None
        if isinstance(message, dict):
            message = "; ".join(
                f"{key}: {', '.join(map(str, value if isinstance(value, list) else [value]))}"
                for key, value in message.items()
            )
        raise SnipeError(str(message or fallback))

    def checkout_asset(
        self,
        asset_id: int,
        target_user_id: int,
        status_id: int,
        note: str,
    ) -> dict[str, Any]:
        body = self._request(
            "POST",
            f"/hardware/{asset_id}/checkout",
            payload={
                "checkout_to_type": "user",
                "assigned_user": target_user_id,
                "status_id": status_id,
                "note": note,
            },
        )
        return self._require_success(body, "Snipe-IT nie potwierdził przypisania.")

    def checkin_asset(
        self, asset_id: int, status_id: int, note: str
    ) -> dict[str, Any]:
        body = self._request(
            "POST",
            f"/hardware/{asset_id}/checkin",
            payload={"status_id": status_id, "note": note},
        )
        return self._require_success(body, "Snipe-IT nie potwierdził zwrotu.")
