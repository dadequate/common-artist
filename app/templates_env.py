"""Shared Jinja2Templates instance with dynamic settings injection."""
import typing
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from starlette.responses import Response


class _AppTemplates(Jinja2Templates):
    def TemplateResponse(  # type: ignore[override]
        self,
        *args: typing.Any,
        **kwargs: typing.Any,
    ) -> Response:
        import app.settings_store as s
        # Resolve (request, name, context) or (name, context) call forms
        if args and isinstance(args[0], Request):
            request, name = args[0], args[1]
            context: dict = args[2] if len(args) > 2 else kwargs.pop("context", {})
        else:
            name = args[0]
            context = args[1] if len(args) > 1 else kwargs.pop("context", {})
            request = kwargs.pop("request", context.get("request"))

        context.setdefault("gallery_name", s.get("gallery_name"))
        context.setdefault("app_version", s.APP_VERSION)
        return super().TemplateResponse(request, name, context, **kwargs)


templates = _AppTemplates(directory="app/templates")
