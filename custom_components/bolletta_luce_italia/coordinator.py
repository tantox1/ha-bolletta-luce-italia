"""Coordinatore dati di Bolletta Luce Italia."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .archive import BillArchive
from .calculator import calculate
from .const import *  # noqa: F403
from .period import (
    PERIOD_SUM_KEYS,
    build_period_archive,
    invoice_months,
    is_bimonthly,
    month_elapsed_fraction,
    period_bounds,
    period_label,
    period_months,
    project_month,
    sum_months,
)


class BillCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Legge le entità sorgente e aggiorna tutti i risultati insieme."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            logger=__import__("logging").getLogger(__name__),
            name=DOMAIN,  # noqa: F405
            config_entry=entry,
            update_interval=timedelta(minutes=5),
        )
        self.entry = entry
        self.archive = BillArchive(hass, entry.entry_id)
        self._active_month: str | None = None
        self._active_snapshot: dict[str, Any] | None = None

    @property
    def config(self) -> dict[str, Any]:
        return {**self.entry.data, **self.entry.options}

    async def _async_setup(self) -> None:
        await self.archive.async_load()
        # Recupera il mese in corso salvato prima del riavvio: se nel frattempo
        # il mese è cambiato, il primo aggiornamento lo archivia correttamente.
        self._active_month, self._active_snapshot = self.archive.active()

    def _state_number(self, entity_id: str | None, required: bool = False) -> float:
        if not entity_id:
            if required:
                raise UpdateFailed("Entità sorgente non configurata")
            return 0.0
        state = self.hass.states.get(entity_id)
        if state is None or state.state in {"unknown", "unavailable", "none", ""}:
            if required:
                raise UpdateFailed(f"Sorgente non disponibile: {entity_id}")
            return 0.0
        try:
            return float(state.state)
        except ValueError as err:
            raise UpdateFailed(f"Valore non numerico: {entity_id}") from err

    async def _async_update_data(self) -> dict[str, Any]:
        cfg = self.config
        values = {
            "raw_energy_f1": self._state_number(cfg.get(CONF_ENERGY_F1), True),  # noqa: F405
            "raw_energy_f2": self._state_number(cfg.get(CONF_ENERGY_F2), True),  # noqa: F405
            "raw_energy_f3": self._state_number(cfg.get(CONF_ENERGY_F3), True),  # noqa: F405
        }
        if cfg.get(CONF_TARIFF_MODEL) == TARIFF_INDEXED:  # noqa: F405
            values.update({
                "pun_f1": self._state_number(cfg.get(CONF_PUN_F1), True),  # noqa: F405
                "pun_f2": self._state_number(cfg.get(CONF_PUN_F2), True),  # noqa: F405
                "pun_f3": self._state_number(cfg.get(CONF_PUN_F3), True),  # noqa: F405
            })
        if cfg.get(CONF_EV_ENABLED):  # noqa: F405
            values["ev_grid"] = self._state_number(cfg.get(CONF_EV_GRID))  # noqa: F405
            values["ev_pv"] = self._state_number(cfg.get(CONF_EV_PV))  # noqa: F405

        now = dt_util.now()
        month_key = now.strftime("%Y-%m")
        result = calculate(values, cfg, now.month)
        result["month"] = month_key

        if (
            self._active_month
            and self._active_month != month_key
            and self._active_snapshot
        ):
            await self.archive.async_archive(self._active_month, self._active_snapshot)
        self._active_month = month_key
        self._active_snapshot = dict(result)
        self.archive.set_active(month_key, result)

        archived = self.archive.archived_months()
        invoices = self.archive.data.get("invoices", {})
        self._add_period(result, cfg, month_key, archived, now)

        invoice_month, invoice = self.archive.latest_invoice()
        result["invoice_count"] = len(invoices)
        result["invoice_archive"] = invoices
        result["latest_invoice_month"] = invoice_month
        result["latest_invoice"] = invoice
        result["latest_real_energy"] = invoice.get("energy") if invoice else None
        result["latest_real_total"] = invoice.get("total") if invoice else None
        result["latest_energy_bill_total"] = (
            invoice.get("energy_bill_total") if invoice else None
        )
        result["latest_invoice_rai"] = invoice.get("rai") if invoice else None
        result["latest_bonus"] = invoice.get("bonus") if invoice else None
        result["latest_amount_due"] = invoice.get("amount_due") if invoice else None

        # Lo scostamento confronta la bolletta con la somma delle stime di
        # tutti i mesi che copre: uno per la mensile, due per la bimestrale.
        result["deviation"] = None
        result["deviation_months"] = []
        result["deviation_missing_months"] = []
        result["deviation_estimate"] = None
        if invoice and invoice_month:
            covered = invoice_months(invoice_month, invoice, cfg)
            estimate, missing = sum_months(covered, archived, "estimate")
            result["deviation_months"] = covered
            result["deviation_missing_months"] = missing
            result["deviation_estimate"] = estimate
            if estimate is not None:
                result["deviation"] = round(invoice["total"] - estimate, 2)

        periods = build_period_archive(archived, invoices, cfg, month_key, result)
        result["period_archive"] = periods
        result["period_archive_count"] = len(periods)
        result["monthly_archive"] = archived
        return result

    def _add_period(
        self,
        result: dict[str, Any],
        cfg: dict[str, Any],
        month_key: str,
        archived: dict[str, dict[str, Any]],
        now: Any,
    ) -> None:
        """Aggiunge stima, energia e proiezione del periodo di fatturazione."""
        months = period_months(month_key, cfg)
        position = months.index(month_key)
        previous = months[:position]
        following = months[position + 1:]
        start, end = period_bounds(months)

        result["billing_period"] = BILLING_BIMONTHLY if is_bimonthly(cfg) else BILLING_MONTHLY  # noqa: F405
        result["period_label"] = period_label(months)
        result["period_months"] = months
        result["period_start"] = start
        result["period_end"] = end
        result["month_in_period"] = position + 1
        result["months_in_period"] = len(months)

        _, missing = sum_months(previous, archived, "estimate")
        result["period_complete"] = not missing
        result["period_missing_months"] = missing
        for key in PERIOD_SUM_KEYS:
            total = float(result.get(key) or 0)
            for month in previous:
                total += float(archived.get(month, {}).get(key) or 0)
            digits = 3 if key.startswith("energy") else 2
            result[f"period_{key}"] = round(total + 1e-10, digits)

        previous_estimate = round(
            sum(float(archived.get(m, {}).get("estimate") or 0) for m in previous)
            + 1e-10,
            2,
        )
        result["previous_months_estimate"] = previous_estimate

        vat = float(cfg.get(CONF_VAT, 10.0) or 0)  # noqa: F405
        fraction = month_elapsed_fraction(now)
        month_projection = project_month(result, vat, fraction)
        result["month_projection"] = month_projection
        result["month_elapsed_percent"] = round(fraction * 100, 1)

        # I mesi successivi del periodo vengono stimati con la stessa spesa
        # variabile del mese corrente, aggiornando soltanto il canone RAI.
        installments = max(1, int(float(cfg.get(CONF_RAI_INSTALLMENTS, 10) or 10)))  # noqa: F405
        rai_rate = float(cfg.get(CONF_RAI_YEAR, 0) or 0) / installments  # noqa: F405
        current_rai = float(result.get("rai") or 0)
        future = 0.0
        for month in following:
            month_number = int(month[5:7])
            future_rai = rai_rate if 1 <= month_number <= installments else 0.0
            future += month_projection - current_rai + future_rai
        result["period_projection"] = round(
            previous_estimate + month_projection + future + 1e-10, 2
        )

    async def async_record_invoice(
        self,
        month: str,
        energy: float,
        total: float,
        **details: Any,
    ) -> None:
        await self.archive.async_record_invoice(month, energy, total, **details)
        await self.async_request_refresh()

    async def async_import_invoices(
        self,
        invoices: list[dict[str, Any]],
    ) -> None:
        await self.archive.async_import_invoices(invoices)
        await self.async_request_refresh()

    async def async_archive_current(self, month: str | None = None) -> None:
        if not self.data:
            return
        key = month or self.data["month"]
        await self.archive.async_archive(key, self.data)
        await self.async_request_refresh()

    async def async_set_month_estimate(
        self,
        month: str,
        estimate: float,
        energy_total: float | None = None,
    ) -> None:
        """Inserisce a mano la stima di un mese non archiviato."""
        snapshot: dict[str, Any] = {"estimate": round(float(estimate), 2)}
        if energy_total is not None:
            snapshot["energy_total"] = round(float(energy_total), 3)
        await self.archive.async_archive(month, snapshot)
        await self.async_request_refresh()
