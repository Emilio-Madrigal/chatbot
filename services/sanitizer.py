import re
from typing import Any

# Simple emoji stripper using Unicode ranges commonly used for emoji and symbols.
# Not perfect but removes majority of pictographs used in UI messages.
_EMOJI_RE = re.compile("["
    "\U0001F300-\U0001F5FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\u2600-\u26FF\u2700-\u27BF"
    "]+", flags=re.UNICODE)


def strip_emojis(value: Any) -> Any:
    """If value is a string, return a copy without emojis. Otherwise return value unchanged."""
    if not isinstance(value, str):
        return value
    return _EMOJI_RE.sub('', value)
