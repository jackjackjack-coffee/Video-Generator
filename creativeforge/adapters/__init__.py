"""Adapter implementations. Importing this module registers all adapters."""

from creativeforge.adapters import base  # noqa: F401
from creativeforge.adapters.audio import pixabay  # noqa: F401
from creativeforge.adapters.compose import remotion  # noqa: F401
from creativeforge.adapters.image import google_flow_imagen  # noqa: F401
from creativeforge.adapters.video import google_flow_veo  # noqa: F401
from creativeforge.adapters.voice import edge_tts as _edge  # noqa: F401
from creativeforge.adapters.voice import voicebox  # noqa: F401

__all__ = ["base"]
