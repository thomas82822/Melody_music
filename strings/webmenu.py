"""
🎨 Reusable "colored menu" system for the Telegram Mini App.

Why this exists: the Bot API cannot color a normal chat button, but it can
open a Telegram Mini App (a plain HTML page rendered inside the client),
and an HTML page can be colored however we like. `docs/menu.html` is a
single generic page that renders whatever button grid it's told to via a
`spec` query param; this module builds that param.

How to add a new colored menu (e.g. for a future feature):

    from strings.webmenu import build_webapp_menu, MenuButton

    url = build_webapp_menu(
        menu_id="myfeature",           # becomes the "myfeature:<action>" data sent back
        title="My Feature",
        subtitle="Pick an option",
        rows=[
            [MenuButton("Do Thing", "blue", "do_thing")],
            [MenuButton("Danger",  "red",  "danger"), MenuButton("Nice", "green", "nice")],
        ],
    )
    if url:
        InlineKeyboardButton("Open menu", web_app=WebAppInfo(url=url))
    # else: Config.WEBAPP_URL isn't set — fall back to plain inline buttons.

Then handle the reply in `melody/plugins/music/webapp_handler.py`: incoming
`message.web_app_data.data` will be `"myfeature:do_thing"` etc.
"""
import base64
import json
from dataclasses import dataclass, field
from typing import Optional

from melody.config import Config

VALID_COLORS = ("blue", "red", "green")


@dataclass
class MenuButton:
    label: str
    color: str  # "blue" | "red" | "green"
    action: str  # sent back as "<menu_id>:<action>" via tg.sendData
    icon: str = ""
    href: Optional[str] = None  # if set, opens a link instead of sending data

    def to_dict(self) -> dict:
        color = self.color if self.color in VALID_COLORS else "blue"
        d = {"label": self.label, "color": color, "icon": self.icon}
        if self.href:
            d["href"] = self.href
        else:
            d["action"] = self.action
        return d


def _menu_base_url() -> Optional[str]:
    """Derive the menu.html URL from WEBAPP_URL (which historically points
    straight at index.html for the playback-controls mini app)."""
    base = (Config.WEBAPP_URL or "").strip()
    if not base:
        return None
    if base.endswith(".html"):
        return base.rsplit("/", 1)[0] + "/menu.html"
    return base.rstrip("/") + "/menu.html"


def build_webapp_menu(
    menu_id: str,
    title: str,
    subtitle: str,
    rows: list,
    extra: Optional[dict] = None,
) -> Optional[str]:
    """Build a Mini App URL for a colored button grid.

    Returns None when `WEBAPP_URL` isn't configured — callers must fall back
    to a plain (uncolored) native keyboard in that case.
    """
    menu_base = _menu_base_url()
    if not menu_base:
        return None

    spec = {
        "menu": menu_id,
        "title": title,
        "subtitle": subtitle,
        "rows": [[b.to_dict() for b in row] for row in rows],
    }
    if extra:
        spec.update(extra)

    encoded = base64.urlsafe_b64encode(json.dumps(spec).encode("utf-8")).decode("ascii")
    return f"{menu_base}?spec={encoded}"
