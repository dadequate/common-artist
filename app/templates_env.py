"""Shared Jinja2Templates instance so globals (gallery_name, etc.) apply everywhere."""
import os
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")
templates.env.globals["gallery_name"] = os.environ.get("GALLERY_NAME", "CommonArtist Gallery")
