"""DataUpdateCoordinator for Marstek Venus E."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MarsktekAPI, MarsktekAPIError, MarsktekTimeoutError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class MarsktekCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """
    Polls the Marstek Venus E battery every *scan_interval* seconds.

    The coordinator owns the MarsktekAPI instance and keeps it alive across
    polls (persistent UDP socket).  On permanent errors it tries to reconnect.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        api: MarsktekAPI,
        device_name: str,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{device_name}",
            update_interval=timedelta(seconds=scan_interval),
        )
        self.api = api
        self.device_name = device_name
        self._consecutive_errors = 0

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch all status data from the battery."""
        try:
            data = await self.api.get_all_status()
            self._consecutive_errors = 0
            return data
        except MarsktekTimeoutError as exc:
            self._consecutive_errors += 1
            _LOGGER.warning(
                "[%s] Timeout polling battery (%d consecutive): %s",
                self.device_name,
                self._consecutive_errors,
                exc,
            )
            # Try to reconnect the socket after several consecutive failures
            if self._consecutive_errors >= 3:
                _LOGGER.info("[%s] Reconnecting UDP socket…", self.device_name)
                try:
                    await self.api.connect()
                except Exception as conn_exc:
                    _LOGGER.error("[%s] Reconnect failed: %s", self.device_name, conn_exc)
            raise UpdateFailed(f"Timeout: {exc}") from exc
        except MarsktekAPIError as exc:
            raise UpdateFailed(f"API error: {exc}") from exc
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.exception("[%s] Unexpected error: %s", self.device_name, exc)
            raise UpdateFailed(f"Unexpected: {exc}") from exc
