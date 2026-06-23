"""
report.py
=========
All terminal output: report header, transaction detail table,
and monthly / all-time balance summary.

No imports from api.py or filters.py — this module is intentionally
self-contained so it can be tested or reused independently.
"""

from collections import defaultdict
from datetime import datetime

# ── Internal constants ────────────────────────────────────────────────────────

_COL_WIDTH = 62

_MESES_ES: dict[int, str] = {
    1: "Enero",   2: "Febrero", 3: "Marzo",  4: "Abril",
    5: "Mayo",    6: "Junio",   7: "Julio",  8: "Agosto",
    9: "Sep",    10: "Oct",    11: "Nov",   12: "Dic",
}

# ── Internal helpers ──────────────────────────────────────────────────────────


def _fmt_row(
    fecha_dt: datetime,
    tipo: str,
    moneda: str,
    monto: float,
    signo: str = "+",
) -> str:
    """Formats a single transaction into a fixed-width terminal row."""
    signo_monto = f"{signo}{abs(monto):.2f}"
    return (
        f"  {fecha_dt.strftime('%Y-%m-%d %H:%M:%S'):<22} "
        f"{tipo:<20} "
        f"{moneda:<8} "
        f"{signo_monto:>14}"
    )


# ── Public print functions ────────────────────────────────────────────────────


def print_header(excluded_ids: set, start_dt: datetime) -> None:
    """Prints the report banner shown before any data is fetched."""
    print(f"\n{'='*_COL_WIDTH}")
    print("  BINANCE - Balance neto stablecoins (USDC + USDT)")
    print(f"  Desde: {start_dt.strftime('%Y-%m-%d')} hasta hoy")
    if excluded_ids:
        print(f"  IDs excluidos: {len(excluded_ids)}")
    print(f"{'='*_COL_WIDTH}\n")


def print_detail_table(ingresos: list[dict], egresos: list[dict]) -> None:
    """
    Prints a chronological, columnar breakdown of all income and expense
    records. Each record dict must have keys: fecha_dt, tipo, moneda, monto.
    """
    print(f"\n{'='*_COL_WIDTH}")
    print(f"  {'FECHA (UTC)':<22} {'TIPO':<20} {'MONEDA':<8} {'MONTO':>14}")
    print(f"{'='*_COL_WIDTH}")

    if ingresos:
        print(f"\n  >>> INGRESOS ({len(ingresos)})")
        print(f"  {'-'*58}")
        for ing in ingresos:
            print(_fmt_row(ing["fecha_dt"], ing["tipo"], ing["moneda"], ing["monto"], "+"))

    if egresos:
        print(f"\n  >>> EGRESOS ({len(egresos)})")
        print(f"  {'-'*58}")
        for eg in egresos:
            print(_fmt_row(eg["fecha_dt"], eg["tipo"], eg["moneda"], eg["monto"], "-"))


def print_monthly_balance(ingresos: list[dict], egresos: list[dict]) -> None:
    """
    Aggregates records by (year, month) and prints a monthly summary table
    followed by the all-time net balance.
    """
    mes_ing: defaultdict[tuple, float] = defaultdict(float)
    mes_eg: defaultdict[tuple, float] = defaultdict(float)

    for ing in ingresos:
        mes_ing[(ing["fecha_dt"].year, ing["fecha_dt"].month)] += ing["monto"]
    for eg in egresos:
        mes_eg[(eg["fecha_dt"].year, eg["fecha_dt"].month)] += eg["monto"]

    all_months = sorted(set(mes_ing.keys()) | set(mes_eg.keys()))

    print(f"\n{'='*_COL_WIDTH}")
    print("  BALANCE MENSUAL")
    print(f"{'='*_COL_WIDTH}")
    print(f"  {'MES':<14}  {'INGRESOS':>14}  {'EGRESOS':>14}  {'BALANCE':>14}")
    print(f"  {'-'*14}  {'-'*14}  {'-'*14}  {'-'*14}")

    total_ing = 0.0
    total_eg = 0.0

    for year, month in all_months:
        ing = mes_ing.get((year, month), 0.0)
        eg = mes_eg.get((year, month), 0.0)
        bal = ing - eg
        total_ing += ing
        total_eg += eg
        label = f"{_MESES_ES[month]} {year}"
        print(f"  {label:<14}  {ing:>14.2f}  {eg:>14.2f}  {bal:>+14.2f}")

    balance_neto = total_ing - total_eg
    print(f"  {'─'*14}  {'─'*14}  {'─'*14}  {'─'*14}")
    print(
        f"  {'TOTAL HIST.':<14}  {total_ing:>14.2f}  {total_eg:>14.2f}  {balance_neto:>+14.2f}"
    )
    print(f"\n  Balance neto historico USD: $ {balance_neto:,.2f}")
    print(f"{'='*_COL_WIDTH}\n")