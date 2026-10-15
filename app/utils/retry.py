"""How long to wait before retrying a failed API call."""
from __future__ import annotations

import re

_RETRY_IN = re.compile(r"retry in (\d+(?:\.\d+)?)\s*s", re.IGNORECASE)
_RETRY_DELAY = re.compile(r"'retryDelay':\s*'(\d+(?:\.\d+)?)s'")
MAX_WAIT_SECONDS = 65.0


def retry_delay(error: Exception, attempt: int) -> float:
    """Seconds to wait after failed attempt number `attempt` (1, 2, 3, ...).

    * Rate limit (429): wait as long as the API asks ("Please retry in 32s").
    * Overloaded (503): wait a bit longer each time.
    * Anything else: short waits (2s, 4s, ...).
    """
    message = str(error)
    for pattern in (_RETRY_IN, _RETRY_DELAY):
        match = pattern.search(message)
        if match:
            return min(float(match.group(1)) + 1.0, MAX_WAIT_SECONDS)
    if "503" in message or "UNAVAILABLE" in message:
        return min(5.0 * attempt, MAX_WAIT_SECONDS)
    return 2.0 * attempt
