from fastapi import Request


def get_client_ip(request: Request) -> str | None:
    """
    Resolve the real client IP address from the request.

    Priority order:
      1. CF-Connecting-IP  — Cloudflare sets this to the true visitor IP
      2. X-Real-IP         — set by nginx / single-hop proxies
      3. X-Forwarded-For   — leftmost entry is the originating client
      4. request.client.host — direct TCP connection (last resort)

    Always takes the *first* (leftmost) value from multi-value headers because
    that is the client-supplied IP; rightmost entries are added by proxies and
    are trustworthy only when you control every hop.
    """
    for header in ("CF-Connecting-IP", "X-Real-IP", "X-Forwarded-For"):
        value = request.headers.get(header)
        if value:
            return value.split(",")[0].strip()
    return request.client.host if request.client else None
