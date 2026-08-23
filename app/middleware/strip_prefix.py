"""Strip a URL prefix when the app is served behind a path-based reverse proxy."""

from starlette.types import ASGIApp, Receive, Scope, Send


class StripPrefixMiddleware:
    def __init__(self, app: ASGIApp, prefix: str) -> None:
        self.app = app
        self.prefix = prefix.rstrip("/") or ""

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if self.prefix and scope["type"] == "http":
            path = scope.get("path", "")
            if path == self.prefix or path.startswith(f"{self.prefix}/"):
                scope = dict(scope)
                remainder = path[len(self.prefix):] or "/"
                scope["path"] = remainder
                scope["root_path"] = (scope.get("root_path") or "") + self.prefix
        await self.app(scope, receive, send)
