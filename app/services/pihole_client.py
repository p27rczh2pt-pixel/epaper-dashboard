import time

import requests


class PiholeAuthError(Exception):
    """Raised when Pi-hole rejects the app password or a session can't be established."""


class PiholeAPIError(Exception):
    """Raised when Pi-hole returns a non-auth error response."""


class PiholeClient:
    """
    Thin client for the Pi-hole v6 REST API.

    v6 auth flow: POST /api/auth with the app password returns a session id
    (sid) and a CSRF token, valid for a limited time. The sid is then passed
    on subsequent requests. This client handles login and transparent
    re-auth when the session expires.

    The sid is sent as the `sid` HTTP header rather than a `?sid=` query
    param: sids are base64 and contain `+`/`/` characters, and Pi-hole's
    query-string parser doesn't correctly decode the percent-encoded form
    (`%2B`/`%2F`) that `requests` produces for those bytes, causing
    spurious 401s. The header path isn't affected by that decoding step.
    """

    def __init__(self, host, app_password, verify_tls=True, timeout=5):
        self.base_url = host.rstrip("/") + "/api"
        self.app_password = app_password
        self.verify_tls = verify_tls
        self.timeout = timeout

        self._session = requests.Session()
        self._sid = None
        self._csrf = None
        self._sid_expires_at = 0.0

    def _authenticate(self):
        try:
            resp = self._session.post(
                f"{self.base_url}/auth",
                json={"password": self.app_password},
                timeout=self.timeout,
                verify=self.verify_tls,
            )
        except requests.RequestException as exc:
            raise PiholeAuthError(f"Could not reach Pi-hole at {self.base_url}: {exc}") from exc

        if resp.status_code == 401:
            raise PiholeAuthError("Pi-hole rejected the app password")
        resp.raise_for_status()

        payload = resp.json()
        session_info = payload.get("session") or {}
        if not session_info.get("valid"):
            raise PiholeAuthError("Pi-hole authentication failed: session not valid")

        self._sid = session_info.get("sid")
        self._csrf = session_info.get("csrf")
        validity = session_info.get("validity", 300)
        # Refresh a bit early so we don't race the server-side expiry.
        self._sid_expires_at = time.monotonic() + max(validity - 15, 5)

    def _ensure_authenticated(self):
        if not self._sid or time.monotonic() >= self._sid_expires_at:
            self._authenticate()

    def _get(self, path, params=None):
        self._ensure_authenticated()
        resp = self._request_with_reauth(path, params or {})
        resp.raise_for_status()
        return resp.json()

    def _request_with_reauth(self, path, params):
        try:
            resp = self._session.get(
                f"{self.base_url}{path}",
                params=params,
                headers={"sid": self._sid},
                timeout=self.timeout,
                verify=self.verify_tls,
            )
        except requests.RequestException as exc:
            raise PiholeAPIError(f"Request to {path} failed: {exc}") from exc

        if resp.status_code == 401:
            # Session likely expired server-side before our local TTL guess did.
            self._sid = None
            self._ensure_authenticated()
            try:
                resp = self._session.get(
                    f"{self.base_url}{path}",
                    params=params,
                    headers={"sid": self._sid},
                    timeout=self.timeout,
                    verify=self.verify_tls,
                )
            except requests.RequestException as exc:
                raise PiholeAPIError(f"Request to {path} failed after re-auth: {exc}") from exc

        return resp

    def get_summary(self):
        return self._get("/stats/summary")

    def get_top_domains(self, blocked=True, count=10):
        return self._get("/stats/top_domains", params={"blocked": str(blocked).lower(), "count": count})

    def get_top_clients(self, count=10):
        return self._get("/stats/top_clients", params={"count": count})

    def get_system_info(self):
        return self._get("/info/system")

    def get_devices(self):
        """
        All devices Pi-hole's network table has ever seen (via DHCP/ARP,
        not just recent DNS queriers) — keyed by MAC (`hwaddr`), which is
        stable across DHCP IP changes. Distinct from /api/clients, which is
        the (unrelated) client-groups config API.
        """
        return self._get("/network/devices")

    def close(self):
        """Best-effort session teardown. Safe to skip; sessions expire on their own."""
        if not self._sid:
            return
        try:
            self._session.delete(
                f"{self.base_url}/auth",
                headers={"sid": self._sid},
                timeout=self.timeout,
                verify=self.verify_tls,
            )
        except requests.RequestException:
            pass
        finally:
            self._sid = None
            self._csrf = None
            self._sid_expires_at = 0.0
