"""
Shared third-party SDK clients for the workflow service.
"""

from anthropic import Anthropic
from deepgram import DeepgramClient

from .config import ANTHROPIC_API_KEY, DEEPGRAM_API_KEY

anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)
deepgram_client = DeepgramClient(api_key=DEEPGRAM_API_KEY)

__all__ = ["anthropic_client", "deepgram_client"]
