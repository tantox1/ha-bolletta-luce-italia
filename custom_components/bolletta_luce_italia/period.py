"""Periodi di fatturazione mensili e bimestrali, indipendenti da Home Assistant."""

from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime
from typing import Any

from .const import (
    BILLING_BIMONTHLY,
    BIMESTER_EVEN,
    CONF_BILLING_PERIOD,
    CONF_BIMESTER_START,
)

MONTH_NAMES = (
    "gen", "feb", "mar", "apr", "mag", "giu",
    "lug", "ago", "set", "ott", "nov", "dic",
)

# Voci sommate sul periodo ed esposte come attributi "period_<voce>".
PERIOD_SUM_KEYS = (
    "energy_f1",
    "energy_f2",
    "energy_f3",
    "energy_total",
    "matter",
    "cdispd_cost",
    "network_cost",
    "fixed_cost",
    "excise",
    "vat",
    "rai",
    "estimate",
)

# Voci conservate nello storico mensile esposto ai grafici.
ARCHIVE_KEYS = PERIOD_SUM_KEYS + ("effective_price",)


def _parse(key: str) -> tuple[int, int]:
    year, month = key.split("-")
    return int(year), int(month)


def _key(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def month_add(key: str, delta: int) -> str:
    """Somma un numero di mesi a una chiave AAAA-MM."""
    year, month = _parse(key)
    index = year * 12 + (month - 1) + delta
    return _key(index // 12, index % 12 + 1)


def months_between(start: str, end: str) -> list[str]:
    """Elenco inclusivo dei mesi fra due chiavi AAAA-MM."""
    if end < start:
        start, end = end, start
    months = [start]
    while months[-1] < end:
        months.append(month_add(months[-1], 1))
    return months


def is_bimonthly(config: dict[str, Any]) -> bool:
    return config.get(CONF_BILLING_PERIOD) == BILLING_BIMONTHLY


def period_months(month_key: str, config: dict[str, Any]) -> list[str]:
    """Mesi del periodo di fatturazione che contiene il mese indicato."""
    if not is_bimonthly(config):
        return [month_key]
    _, month = _parse(month_key)
    # Bimestri dispari: gen-feb, mar-apr, ... Bimestri pari: dic-gen, feb-mar, ...
    starts_on_odd = config.get(CONF_BIMESTER_START) != BIMESTER_EVEN
    first_month = (month % 2 == 1) == starts_on_odd
    if first_month:
        return [month_key, month_add(month_key, 1)]
    return [month_add(month_key, -1), month_key]


def period_label(months: list[str]) -> str:
    """Etichetta leggibile, per esempio "nov–dic 2026" o "dic 2026–gen 2027"."""
    first_year, first_month = _parse(months[0])
    last_year, last_month = _parse(months[-1])
    first = MONTH_NAMES[first_month - 1]
    last = MONTH_NAMES[last_month - 1]
    if len(months) == 1:
        return f"{first} {first_year}"
    if first_year == last_year:
        return f"{first}–{last} {last_year}"
    return f"{first} {first_year}–{last} {last_year}"


def period_bounds(months: list[str]) -> tuple[str, str]:
    """Primo e ultimo giorno del periodo in formato ISO."""
    first_year, first_month = _parse(months[0])
    last_year, last_month = _parse(months[-1])
    end_day = monthrange(last_year, last_month)[1]
    return (
        date(first_year, first_month, 1).isoformat(),
        date(last_year, last_month, end_day).isoformat(),
    )


def invoice_months(
    invoice_month: str,
    invoice: dict[str, Any],
    config: dict[str, Any],
) -> list[str]:
    """Mesi coperti da una bolletta reale.

    Se la bolletta riporta il periodo di fatturazione si usano quelle date,
    altrimenti si usa il periodo configurato che contiene il mese indicato.
    """
    start = invoice.get("period_start")
    end = invoice.get("period_end")
    if start and end:
        return months_between(str(start)[:7], str(end)[:7])
    return period_months(invoice_month, config)


def sum_months(
    months: list[str],
    archived: dict[str, dict[str, Any]],
    key: str,
) -> tuple[float | None, list[str]]:
    """Somma una voce sui mesi indicati e restituisce anche i mesi mancanti."""
    total = 0.0
    missing: list[str] = []
    for month in months:
        value = archived.get(month, {}).get(key)
        if value is None:
            missing.append(month)
        else:
            total += float(value)
    return (None if missing else round(total + 1e-10, 2)), missing


def month_elapsed_fraction(now: datetime) -> float:
    """Frazione trascorsa del mese corrente, mai inferiore a un giorno."""
    days = monthrange(now.year, now.month)[1]
    elapsed_days = (
        now.day - 1
        + now.hour / 24
        + now.minute / 1440
    )
    return min(1.0, max(elapsed_days, 1.0) / days)


def project_month(result: dict[str, Any], vat_percent: float, fraction: float) -> float:
    """Proietta la stima del mese corrente a fine mese.

    Quote fisse, relativa IVA e canone RAI non dipendono dai consumi e non
    vengono estrapolate; il resto cresce in proporzione al tempo trascorso.
    """
    fixed_with_vat = float(result.get("fixed_cost", 0)) * (1 + vat_percent / 100)
    rai = float(result.get("rai", 0))
    variable = float(result.get("estimate", 0)) - fixed_with_vat - rai
    return round(fixed_with_vat + rai + max(variable, 0.0) / fraction + 1e-10, 2)


def trim_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Tiene soltanto le voci utili dello snapshot mensile."""
    return {key: snapshot[key] for key in ARCHIVE_KEYS if key in snapshot}


def build_period_archive(
    archived: dict[str, dict[str, Any]],
    invoices: dict[str, dict[str, Any]],
    config: dict[str, Any],
    current_month: str | None = None,
    current: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Riepilogo per periodo di stime archiviate e bollette reali."""
    months = dict(archived)
    if current_month and current is not None:
        months[current_month] = current

    periods: dict[str, dict[str, Any]] = {}

    def _period(period: list[str]) -> dict[str, Any]:
        key = period[0]
        if key not in periods:
            start, end = period_bounds(period)
            periods[key] = {
                "key": key,
                "label": period_label(period),
                "months": period,
                "period_start": start,
                "period_end": end,
                "in_progress": bool(current_month and current_month in period),
            }
        return periods[key]

    for month in months:
        _period(period_months(month, config))

    for month, invoice in invoices.items():
        covered = invoice_months(month, invoice, config)
        item = _period(covered)
        item["months"] = covered
        item["real_total"] = invoice.get("total")
        item["real_energy"] = invoice.get("energy")
        item["amount_due"] = invoice.get("amount_due")
        item["invoice_month"] = month

    for item in periods.values():
        estimate, missing = sum_months(item["months"], months, "estimate")
        energy, _ = sum_months(item["months"], months, "energy_total")
        item["estimate"] = estimate
        item["estimate_energy"] = energy
        item["missing_months"] = missing
        partial = [
            float(months[m]["estimate"])
            for m in item["months"]
            if m in months and months[m].get("estimate") is not None
        ]
        item["estimate_partial"] = round(sum(partial) + 1e-10, 2) if partial else None
        real = item.get("real_total")
        item["deviation"] = (
            round(float(real) - estimate, 2)
            if real is not None and estimate is not None and not item["in_progress"]
            else None
        )

    return [periods[key] for key in sorted(periods)]
