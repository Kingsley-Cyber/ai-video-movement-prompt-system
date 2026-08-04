"""Generation-provider adapters with no directing or knowledge authority."""

from .base import AdapterError, GenerationAdapter
from .veo import VeoVertexAdapter

__all__ = ["AdapterError", "GenerationAdapter", "VeoVertexAdapter"]
