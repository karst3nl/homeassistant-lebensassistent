"""Begrenzte URL-Formulare und CSRF-Prüfung vor jedem schreibenden Aufruf."""

import hmac
import re
from urllib.parse import parse_qs, urlsplit

from fastapi import HTTPException, Request


def authority(value: str, scheme: str) -> tuple[str, int]:
    if not re.fullmatch(
        r"(?:[A-Za-z0-9._-]+|\[[0-9A-Fa-f:]+\])(?::[0-9]{1,5})?", value
    ):
        raise ValueError("Invalid authority")
    parsed = urlsplit(f"//{value}")
    port = parsed.port
    if port is None:
        port = 443 if scheme == "https" else 80
    if parsed.hostname is None or not 1 <= port <= 65535:
        raise ValueError("Invalid authority")
    return parsed.hostname.lower(), port


def check_browser_origin(request: Request) -> None:
    site = request.headers.get("sec-fetch-site")
    if site is not None and site not in ("same-origin", "none"):
        raise HTTPException(403, "Forbidden")
    origins = request.headers.getlist("origin")
    if not origins:
        return
    try:
        if len(origins) != 1:
            raise ValueError("Ambiguous origin")
        # HA's no-referrer response policy makes native form POSTs send null.
        # read_form has already verified the token; the peer/prefix gate must
        # also have succeeded. Local requests never get this exception.
        if origins[0] == "null" and request.scope.get(
            "lebensassistent.ingress_verified"
        ):
            return
        origin = urlsplit(origins[0])
        if (
            origin.scheme not in ("http", "https")
            or origin.path
            or origin.query
            or origin.fragment
            or not origin.netloc
        ):
            raise ValueError("Invalid origin")
        hosts = request.headers.getlist("host")
        if len(hosts) != 1:
            raise ValueError("Ambiguous host")
        candidates = [authority(hosts[0], origin.scheme)]
        forwarded = request.headers.getlist("x-forwarded-host")
        if request.scope.get("lebensassistent.ingress_verified") and forwarded:
            if len(forwarded) != 1:
                raise ValueError("Ambiguous forwarded host")
            candidates.append(authority(forwarded[0], origin.scheme))
        if authority(origin.netloc, origin.scheme) not in candidates:
            raise ValueError("Foreign origin authority")
    except ValueError:
        raise HTTPException(403, "Forbidden") from None


async def read_form(
    request: Request, allowed: set[str], *, max_fields: int = 16
) -> dict[str, str]:
    content_type = request.headers.get("content-type", "").split(";", 1)[0].lower()
    if content_type != "application/x-www-form-urlencoded":
        raise HTTPException(415, "Unsupported form encoding")
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 32768:
            raise HTTPException(413, "Form too large")
    try:
        values = parse_qs(
            body.decode("utf-8"),
            keep_blank_values=True,
            strict_parsing=True,
            max_num_fields=max_fields,
            errors="strict",
        )
    except (ValueError, UnicodeError):
        raise HTTPException(400, "Invalid form") from None
    if any(len(value) != 1 for value in values.values()) or set(values) - allowed - {
        "csrf_token"
    }:
        raise HTTPException(400, "Invalid form fields")
    form = {key: value[0] for key, value in values.items()}
    submitted = form.pop("csrf_token", "")
    if not hmac.compare_digest(
        submitted.encode("utf-8"), request.app.state.csrf_token.encode("ascii")
    ):
        raise HTTPException(403, "Forbidden")
    check_browser_origin(request)
    return form
