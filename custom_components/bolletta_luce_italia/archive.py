"""Archivio persistente mensile e bollette reali."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import STORAGE_KEY, STORAGE_VERSION
from .period import trim_snapshot

# Lo snapshot del mese in corso viene scritto al massimo ogni 15 minuti,
# per non consumare la scheda SD con una scrittura a ogni aggiornamento.
_ACTIVE_SAVE_DELAY = 900

_ENERGY_KEYS = {"energy", "energy_f1", "energy_f2", "energy_f3"}
_MONEY_KEYS = {
    "total",
    "energy_bill_total",
    "rai",
    "bonus",
    "amount_due",
    "matter",
    "transport",
    "system_charges",
    "excise",
    "vat",
}


class BillArchive:
    """Conserva stime chiuse e consuntivi reali nello storage di HA."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, STORAGE_KEY.format(entry_id=entry_id)
        )
        self.data: dict[str, Any] = {"months": {}, "invoices": {}}

    async def async_load(self) -> None:
        loaded = await self._store.async_load()
        if loaded:
            self.data.update(loaded)

    async def async_save(self) -> None:
        await self._store.async_save(self.data)

    async def async_archive(self, month: str, snapshot: dict[str, Any]) -> None:
        self.data.setdefault("months", {})[month] = trim_snapshot(snapshot)
        await self.async_save()

    def billing_schedule(self) -> list[dict[str, Any]]:
        return list(self.data.get("billing_schedule") or [])

    async def async_set_billing_schedule(self, schedule: list[dict[str, Any]]) -> None:
        if schedule != self.data.get("billing_schedule"):
            self.data["billing_schedule"] = schedule
            await self.async_save()

    def active(self) -> tuple[str | None, dict[str, Any] | None]:
        """Ultimo snapshot salvato del mese in corso."""
        active = self.data.get("active") or {}
        return active.get("month"), active.get("snapshot")

    def set_active(self, month: str, snapshot: dict[str, Any]) -> None:
        """Memorizza lo snapshot corrente con scrittura ritardata."""
        self.data["active"] = {"month": month, "snapshot": trim_snapshot(snapshot)}
        self._store.async_delay_save(lambda: self.data, _ACTIVE_SAVE_DELAY)

    def archived_months(self) -> dict[str, dict[str, Any]]:
        """Stime mensili chiuse, ridotte alle voci utili."""
        return {
            month: trim_snapshot(snapshot)
            for month, snapshot in self.data.get("months", {}).items()
        }

    def _set_invoice(
        self,
        month: str,
        energy: float,
        total: float,
        details: dict[str, Any],
    ) -> None:
        record: dict[str, Any] = {
            "energy": round(float(energy), 3),
            "total": round(float(total), 2),
        }
        for key, value in details.items():
            if value is None:
                continue
            if key in _ENERGY_KEYS:
                record[key] = round(float(value), 3)
            elif key in _MONEY_KEYS:
                record[key] = round(float(value), 2)
            else:
                record[key] = value
        self.data.setdefault("invoices", {})[month] = record

    async def async_record_invoice(
        self,
        month: str,
        energy: float,
        total: float,
        **details: Any,
    ) -> None:
        self._set_invoice(month, energy, total, details)
        await self.async_save()

    async def async_import_invoices(
        self,
        invoices: list[dict[str, Any]],
    ) -> None:
        for invoice in invoices:
            values = dict(invoice)
            month = values.pop("month")
            energy = values.pop("energy")
            total = values.pop("total")
            self._set_invoice(month, energy, total, values)
        await self.async_save()

    def latest_invoice(self) -> tuple[str | None, dict[str, Any] | None]:
        invoices = self.data.get("invoices", {})
        if not invoices:
            return None, None
        key = max(invoices)
        return key, invoices[key]
