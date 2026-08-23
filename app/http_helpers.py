"""HTML response helpers with CSRF."""

from fastapi import Request
from fastapi.templating import Jinja2Templates
from starlette.responses import Response

from app.config import TEMPLATES_DIR, settings
from app.services.csrf import get_csrf_token, set_csrf_cookie

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def render_page(
    request: Request,
    template_name: str,
    context: dict,
    status_code: int = 200,
) -> Response:
    token = get_csrf_token(request)
    root_path = request.scope.get("root_path", settings.root_path or "")
    context = {**context, "csrf_token": token, "root_path": root_path}
    response = templates.TemplateResponse(
        request, template_name, context, status_code=status_code
    )
    set_csrf_cookie(response, token)
    return response
