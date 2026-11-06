"""Platform actions. Each is `fn(ctx, item) -> Result`."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Result:
    url: str
    remote_id: str = ""


def get(action: str):
    """Look an action up by name ("instagram.reel"). Imported lazily so YouTube's optional libraries are only needed when used."""
    platform, kind = action.split(".")
    if platform == "instagram":
        from . import instagram as m
    elif platform == "facebook":
        from . import facebook as m
    elif platform == "youtube":
        from . import youtube as m
    else:
        raise KeyError(action)
    return getattr(m, kind)
