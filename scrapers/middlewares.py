"""
RotateUserAgentMiddleware — picks a fresh random User-Agent for every request.
This reduces the chance of being rate-limited by sites that fingerprint by UA.
Falls back to a hard-coded modern Chrome UA if fake-useragent's data file is
unavailable (common in fresh CI environments).
"""

import logging

logger = logging.getLogger(__name__)

FALLBACK_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


class RotateUserAgentMiddleware:
    def __init__(self):
        self._ua = None
        try:
            from fake_useragent import UserAgent, FakeUserAgentError

            self._ua = UserAgent()
            logger.debug("fake-useragent loaded successfully")
        except Exception as exc:  # noqa: BLE001
            logger.warning("fake-useragent unavailable (%s) — using fallback UA", exc)

    def process_request(self, request, spider):
        try:
            ua = self._ua.random if self._ua else FALLBACK_UA
        except Exception:  # noqa: BLE001
            ua = FALLBACK_UA
        request.headers["User-Agent"] = ua
        logger.debug("UA set: %.80s", ua)
