"""Check a running Gunicorn container using disposable CI configuration."""

import http.cookiejar
import json
import sys
import time
import urllib.error
import urllib.request


def main():
    base = sys.argv[1].rstrip("/")
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
    )
    deadline = time.monotonic() + 90
    while True:
        try:
            with opener.open(base + "/healthz", timeout=5) as response:
                health = json.load(response)
            assert health["status"] == "ok"
            assert health["version"]
            break
        except (urllib.error.URLError, TimeoutError):
            if time.monotonic() >= deadline:
                raise
            time.sleep(1)

    with opener.open(base + "/readyz", timeout=10) as response:
        assert response.status == 200
        readiness = json.load(response)
        assert readiness["checks"]["storage"]["database"] == "ok"

    for path, marker in (("/login", 'name="csrf_token"'),
                         ("/terminal", "SCAN PAIRING QR")):
        with opener.open(base + path, timeout=10) as response:
            assert response.status == 200
            assert marker in response.read().decode("utf-8"), path
    print("Gunicorn HTTP checks passed: health, readiness, login, terminal")


if __name__ == "__main__":
    main()
