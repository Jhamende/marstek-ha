"""
Marstek Venus E — async UDP JSON-RPC client.

Key protocol constraints:
  • UDP only — TCP is rejected by the device.
  • Source port MUST equal destination port (Marstek firmware requirement).
    → We bind the socket to port 30000 (same as the device).
  • Discovery uses a LAN broadcast to 255.255.255.255.
  • Poll interval should not be faster than 60 s to keep the device stable.
"""

from __future__ import annotations

import asyncio
import json
import logging
import socket
import time
from typing import Any

from .const import (
    DEFAULT_PORT,
    DISCOVERY_TIMEOUT,
    METHOD_BAT_STATUS,
    METHOD_EM_STATUS,
    METHOD_ES_GET_MODE,
    METHOD_ES_SET_MODE,
    METHOD_ES_STATUS,
    METHOD_GET_DEVICE,
    METHOD_PV_STATUS,
    METHOD_WIFI_STATUS,
    MODE_AI,
    MODE_AUTO,
    MODE_MANUAL,
    MODE_PASSIVE,
    UDP_COMMAND_TIMEOUT,
    UDP_RETRIES,
)

_LOGGER = logging.getLogger(__name__)


class MarsktekAPIError(Exception):
    """Raised when the device returns a JSON-RPC error."""


class MarsktekTimeoutError(MarsktekAPIError):
    """Raised when the device does not respond in time."""


# ── Low-level UDP protocol ────────────────────────────────────────────────────

class _MarsktekProtocol(asyncio.DatagramProtocol):
    """asyncio DatagramProtocol that routes incoming packets to waiting futures."""

    def __init__(self) -> None:
        self.transport: asyncio.DatagramTransport | None = None
        # pending[request_id] = Future
        self._pending: dict[int, asyncio.Future[dict]] = {}
        # For discovery: collect ALL broadcast responses
        self._discovery_queue: asyncio.Queue[dict] | None = None

    # ── Protocol callbacks ────────────────────────────────────────────────────

    def connection_made(self, transport: asyncio.DatagramTransport) -> None:
        self.transport = transport
        # Allow broadcasts to be received
        sock = transport.get_extra_info("socket")
        if sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        try:
            msg = json.loads(data.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            _LOGGER.debug("Non-JSON UDP packet from %s: %r", addr, data[:80])
            return

        req_id = msg.get("id")
        _LOGGER.debug("UDP ← %s  id=%s  keys=%s", addr[0], req_id, list(msg.keys()))

        # Route to discovery queue if active
        if self._discovery_queue is not None and "result" in msg:
            try:
                self._discovery_queue.put_nowait(msg)
            except asyncio.QueueFull:
                pass
            return

        # Route to a pending request future
        if req_id is not None and req_id in self._pending:
            fut = self._pending.pop(req_id)
            if not fut.done():
                fut.set_result(msg)

    def error_received(self, exc: Exception) -> None:
        _LOGGER.warning("UDP socket error: %s", exc)

    def connection_lost(self, exc: Exception | None) -> None:
        if exc:
            _LOGGER.warning("UDP connection lost: %s", exc)
        # Fail all pending futures
        for fut in self._pending.values():
            if not fut.done():
                fut.set_exception(MarsktekAPIError(f"Connection lost: {exc}"))
        self._pending.clear()

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def send_and_receive(
        self,
        host: str,
        port: int,
        payload: dict[str, Any],
        timeout: float = UDP_COMMAND_TIMEOUT,
    ) -> dict[str, Any]:
        """Send *payload* to *host:port* and wait for matching response."""
        if self.transport is None or self.transport.is_closing():
            raise MarsktekAPIError("Transport not available")

        req_id: int = payload["id"]
        loop = asyncio.get_event_loop()
        fut: asyncio.Future[dict] = loop.create_future()
        self._pending[req_id] = fut

        raw = json.dumps(payload).encode("utf-8")
        _LOGGER.debug("UDP → %s:%s  %s", host, port, payload.get("method"))
        self.transport.sendto(raw, (host, port))

        try:
            return await asyncio.wait_for(fut, timeout=timeout)
        except asyncio.TimeoutError:
            self._pending.pop(req_id, None)
            raise MarsktekTimeoutError(
                f"No response from {host}:{port} for method {payload.get('method')}"
            )


# ── High-level API class ──────────────────────────────────────────────────────

class MarsktekAPI:
    """
    Async client for the Marstek Open API (Rev 2.0).

    Usage::

        api = MarsktekAPI("192.168.1.50")
        await api.connect()
        data = await api.get_all_status()
        await api.set_mode_auto()
        await api.close()

    One *MarsktekAPI* instance manages a single persistent UDP socket bound to
    the *port* (default 30000).  Keep a single instance per device (the
    DataUpdateCoordinator takes care of this).
    """

    def __init__(self, host: str, port: int = DEFAULT_PORT) -> None:
        self.host = host
        self.port = port
        self._protocol: _MarsktekProtocol | None = None
        self._transport: asyncio.DatagramTransport | None = None
        self._req_id: int = 1

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def connect(self) -> None:
        """Create (or recreate) the UDP socket."""
        await self.close()
        loop = asyncio.get_event_loop()
        proto = _MarsktekProtocol()
        try:
            transport, _ = await loop.create_datagram_endpoint(
                lambda: proto,
                local_addr=("0.0.0.0", self.port),
                allow_broadcast=True,
                reuse_port=True,
            )
        except OSError:
            # Fallback: let OS pick source port (some devices accept it anyway)
            _LOGGER.warning(
                "Cannot bind to port %s; falling back to ephemeral port. "
                "Some firmware versions may not respond.",
                self.port,
            )
            transport, _ = await loop.create_datagram_endpoint(
                lambda: proto,
                allow_broadcast=True,
            )
        self._transport = transport
        self._protocol = proto
        _LOGGER.debug("MarsktekAPI connected (host=%s port=%s)", self.host, self.port)

    async def close(self) -> None:
        """Close the UDP socket."""
        if self._transport and not self._transport.is_closing():
            self._transport.close()
        self._transport = None
        self._protocol = None

    def _next_id(self) -> int:
        rid = self._req_id
        self._req_id = (self._req_id % 0xFFFF) + 1
        return rid

    # ── Generic command sender ────────────────────────────────────────────────

    async def _cmd(
        self,
        method: str,
        params: dict | None = None,
        retries: int = UDP_RETRIES,
        timeout: float = UDP_COMMAND_TIMEOUT,
    ) -> dict[str, Any]:
        """Send a JSON-RPC command with retry on timeout."""
        if self._protocol is None:
            await self.connect()

        payload = {"id": self._next_id(), "method": method, "params": params or {"id": 0}}
        last_exc: Exception = MarsktekAPIError("Unknown error")

        for attempt in range(retries + 1):
            try:
                response = await self._protocol.send_and_receive(
                    self.host, self.port, payload, timeout=timeout
                )
                if "error" in response:
                    err = response["error"]
                    raise MarsktekAPIError(
                        f"{method} error {err.get('code')}: {err.get('message')}"
                    )
                return response.get("result", {})
            except MarsktekTimeoutError as exc:
                last_exc = exc
                _LOGGER.debug(
                    "%s timed out (attempt %d/%d)", method, attempt + 1, retries + 1
                )
                if attempt < retries:
                    await asyncio.sleep(1.0)
            except MarsktekAPIError:
                raise

        raise last_exc

    # ── Status queries ────────────────────────────────────────────────────────

    async def get_bat_status(self) -> dict[str, Any]:
        """Bat.GetStatus → soc, charg_flag, dischrg_flag, bat_temp, bat_capacity, rated_capacity."""
        return await self._cmd(METHOD_BAT_STATUS)

    async def get_pv_status(self) -> dict[str, Any]:
        """PV.GetStatus → pv_power, pv_voltage, pv_current, pv_state."""
        return await self._cmd(METHOD_PV_STATUS)

    async def get_es_status(self) -> dict[str, Any]:
        """ES.GetStatus → bat_soc, bat_cap, pv_power, ongrid_power, offgrid_power, totals…"""
        return await self._cmd(METHOD_ES_STATUS)

    async def get_es_mode(self) -> dict[str, Any]:
        """ES.GetMode → mode, ongrid_power, offgrid_power, bat_soc."""
        return await self._cmd(METHOD_ES_GET_MODE, params={"id": 0})

    async def get_em_status(self) -> dict[str, Any]:
        """EM.GetStatus → ct_state, a_power, b_power, c_power, total_power."""
        return await self._cmd(METHOD_EM_STATUS)

    async def get_wifi_status(self) -> dict[str, Any]:
        """Wifi.GetStatus → ssid, rssi, sta_ip, …"""
        return await self._cmd(METHOD_WIFI_STATUS)

    async def get_all_status(self) -> dict[str, Any]:
        """
        Fetch all status endpoints and merge into a single dict.
        ES.GetStatus is tried first; if it times out we gracefully fall back.
        """
        combined: dict[str, Any] = {}

        # Bat status — most important, raise if it fails
        bat = await self.get_bat_status()
        combined.update({"bat_" + k if k != "id" else k: v for k, v in bat.items()})
        # Keep top-level soc for convenience
        combined["soc"] = bat.get("soc")

        # ES status — may timeout on older firmware
        try:
            es = await self.get_es_status()
            combined.update(es)
        except MarsktekTimeoutError:
            _LOGGER.debug("ES.GetStatus timed out — will use ES.GetMode as fallback")
            try:
                es_mode = await self.get_es_mode()
                combined.update(es_mode)
            except MarsktekTimeoutError:
                _LOGGER.warning("ES.GetMode also timed out; energy data unavailable")

        # EM (CT meter) — optional
        try:
            em = await self.get_em_status()
            combined["ct_state"] = em.get("ct_state", 0)
            combined["phase_a_power"] = em.get("a_power", 0)
            combined["phase_b_power"] = em.get("b_power", 0)
            combined["phase_c_power"] = em.get("c_power", 0)
            combined["total_ct_power"] = em.get("total_power", 0)
        except MarsktekTimeoutError:
            _LOGGER.debug("EM.GetStatus timed out — CT data unavailable")

        # WiFi — optional
        try:
            wifi = await self.get_wifi_status()
            combined["wifi_rssi"] = wifi.get("rssi")
            combined["wifi_ssid"] = wifi.get("ssid")
        except MarsktekTimeoutError:
            _LOGGER.debug("Wifi.GetStatus timed out")

        return combined

    # ── Mode control ──────────────────────────────────────────────────────────

    async def set_mode_auto(self) -> bool:
        result = await self._cmd(
            METHOD_ES_SET_MODE,
            params={"id": 0, "config": {"mode": MODE_AUTO}},
        )
        return bool(result.get("set_result", False))

    async def set_mode_ai(self) -> bool:
        result = await self._cmd(
            METHOD_ES_SET_MODE,
            params={"id": 0, "config": {"mode": MODE_AI, "ai_cfg": {"enable": 1}}},
        )
        return bool(result.get("set_result", False))

    async def set_mode_manual(
        self,
        time_num: int = 0,
        start_time: str = "00:00",
        end_time: str = "23:59",
        week_set: int = 127,
        power: int = 0,
        enable: int = 0,
    ) -> bool:
        """
        Switch to Manual mode.  The API requires a schedule slot even when
        just switching to manual (slot 9 is used as a disabled placeholder
        if no schedule is provided).
        """
        result = await self._cmd(
            METHOD_ES_SET_MODE,
            params={
                "id": 0,
                "config": {
                    "mode": MODE_MANUAL,
                    "manual_cfg": {
                        "time_num": time_num,
                        "start_time": start_time,
                        "end_time": end_time,
                        "week_set": week_set,
                        "power": power,
                        "enable": enable,
                    },
                },
            },
        )
        return bool(result.get("set_result", False))

    async def set_mode_passive(self, power: int = 0, cd_time: int = 0) -> bool:
        """
        Switch to Passive mode.

        :param power:   Target power in watts.
                        Positive  → discharge to grid.
                        Negative  → charge from grid.
        :param cd_time: Countdown in seconds (0 = indefinite).
        """
        result = await self._cmd(
            METHOD_ES_SET_MODE,
            params={
                "id": 0,
                "config": {
                    "mode": MODE_PASSIVE,
                    "passive_cfg": {"power": power, "cd_time": cd_time},
                },
            },
        )
        return bool(result.get("set_result", False))

    async def set_manual_schedule(
        self,
        time_num: int,
        start_time: str,
        end_time: str,
        week_set: int,
        power: int,
        enable: bool = True,
    ) -> bool:
        """Configure a single Manual-mode schedule slot (0–9)."""
        result = await self._cmd(
            METHOD_ES_SET_MODE,
            params={
                "id": 0,
                "config": {
                    "mode": MODE_MANUAL,
                    "manual_cfg": {
                        "time_num": time_num,
                        "start_time": start_time,
                        "end_time": end_time,
                        "week_set": week_set,
                        "power": power,
                        "enable": 1 if enable else 0,
                    },
                },
            },
        )
        return bool(result.get("set_result", False))

    async def clear_all_schedules(self) -> None:
        """Disable all 10 manual schedule slots."""
        for slot in range(10):
            try:
                await self.set_manual_schedule(
                    time_num=slot,
                    start_time="00:00",
                    end_time="00:01",
                    week_set=127,
                    power=0,
                    enable=False,
                )
            except MarsktekAPIError as exc:
                _LOGGER.warning("Could not clear slot %d: %s", slot, exc)

    # ── Discovery (static / class method) ────────────────────────────────────

    @staticmethod
    async def discover_devices(
        port: int = DEFAULT_PORT,
        timeout: float = DISCOVERY_TIMEOUT,
    ) -> list[dict[str, Any]]:
        """
        Broadcast Marstek.GetDevice on the LAN and collect all responses.
        Returns a list of device info dicts (device, ver, ble_mac, wifi_mac, ip).
        """
        loop = asyncio.get_event_loop()
        queue: asyncio.Queue[dict] = asyncio.Queue()

        proto = _MarsktekProtocol()
        proto._discovery_queue = queue

        try:
            transport, _ = await loop.create_datagram_endpoint(
                lambda: proto,
                local_addr=("0.0.0.0", port),
                allow_broadcast=True,
                reuse_port=True,
            )
        except OSError:
            transport, _ = await loop.create_datagram_endpoint(
                lambda: proto,
                allow_broadcast=True,
            )

        payload = json.dumps(
            {"id": 0, "method": METHOD_GET_DEVICE, "params": {"ble_mac": "0"}}
        ).encode("utf-8")
        transport.sendto(payload, ("255.255.255.255", port))
        _LOGGER.debug("Discovery broadcast sent on port %s", port)

        devices: list[dict[str, Any]] = []
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=remaining)
                result = msg.get("result", {})
                if result.get("device") and result.get("ip"):
                    # Avoid duplicates
                    if not any(d["ip"] == result["ip"] for d in devices):
                        _LOGGER.info(
                            "Discovered Marstek device: %s at %s (fw v%s)",
                            result.get("device"),
                            result.get("ip"),
                            result.get("ver"),
                        )
                        devices.append(result)
            except asyncio.TimeoutError:
                break

        transport.close()
        return devices
