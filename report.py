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

_MONTH_NAMES: dict[int, str] = {
    1: "Jan",  2: "Feb",  3: "Mar",  4: "Apr",
    5: "May",  6: "Jun",  7: "Jul",  8: "Aug",
    9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
}

# ── Internal helpers ──────────────────────────────────────────────────────────


def _fmt_row(
    date: datetime,
    tx_type: str,
    currency: str,
    amount: float,
    sign: str = "+",
) -> str:
    """Formats a single transaction into a fixed-width terminal row."""
    signed_amount = f"{sign}{abs(amount):.2f}"
    return (
        f"  {date.strftime('%Y-%m-%d %H:%M:%S'):<22} "
        f"{tx_type:<20} "
        f"{currency:<8} "
        f"{signed_amount:>14}"
    )


# ── Public print functions ────────────────────────────────────────────────────


def print_header(excluded_ids: set, start_dt: datetime) -> None:
    """Prints the report banner shown before any data is fetched."""
    print(f"\n{'='*_COL_WIDTH}")
    print("  BINANCE — Net stablecoin balance (USDC + USDT)")
    print(f"  From: {start_dt.strftime('%Y-%m-%d')} to today")
    if excluded_ids:
        print(f"  Excluded IDs: {len(excluded_ids)}")
    print(f"{'='*_COL_WIDTH}\n")


def print_detail_table(income: list[dict], expenses: list[dict]) -> None:
    """
    Prints a chronological, columnar breakdown of all income and expense
    records. Each record dict must have keys: date, tx_type, currency, amount.
    """
    print(f"\n{'='*_COL_WIDTH}")
    print(f"  {'DATE (UTC)':<22} {'TYPE':<20} {'CURRENCY':<8} {'AMOUNT':>14}")
    print(f"{'='*_COL_WIDTH}")

    if income:
        print(f"\n  >>> INCOME ({len(income)})")
        print(f"  {'-'*58}")
        for entry in income:
            print(_fmt_row(entry["date"], entry["tx_type"], entry["currency"], entry["amount"], "+"))

    if expenses:
        print(f"\n  >>> EXPENSES ({len(expenses)})")
        print(f"  {'-'*58}")
        for entry in expenses:
            print(_fmt_row(entry["date"], entry["tx_type"], entry["currency"], entry["amount"], "-"))


def print_monthly_balance(income: list[dict], expenses: list[dict]) -> None:
    """
    Aggregates records by (year, month) and prints a monthly summary table
    followed by the all-time net balance.
    """
    monthly_income: defaultdict[tuple, float] = defaultdict(float)
    monthly_expenses: defaultdict[tuple, float] = defaultdict(float)

    for entry in income:
        monthly_income[(entry["date"].year, entry["date"].month)] += entry["amount"]
    for entry in expenses:
        monthly_expenses[(entry["date"].year, entry["date"].month)] += entry["amount"]

    all_months = sorted(set(monthly_income.keys()) | set(monthly_expenses.keys()))

    print(f"\n{'='*_COL_WIDTH}")
    print("  MONTHLY BALANCE")
    print(f"{'='*_COL_WIDTH}")
    print(f"  {'MONTH':<14}  {'INCOME':>14}  {'EXPENSES':>14}  {'BALANCE':>14}")
    print(f"  {'-'*14}  {'-'*14}  {'-'*14}  {'-'*14}")

    total_income = 0.0
    total_expenses = 0.0

    for year, month in all_months:
        inc = monthly_income.get((year, month), 0.0)
        exp = monthly_expenses.get((year, month), 0.0)
        balance = inc - exp
        total_income += inc
        total_expenses += exp
        label = f"{_MONTH_NAMES[month]} {year}"
        print(f"  {label:<14}  {inc:>14.2f}  {exp:>14.2f}  {balance:>+14.2f}")

    net_balance = total_income - total_expenses
    print(f"  {'─'*14}  {'─'*14}  {'─'*14}  {'─'*14}")
    print(
        f"  {'ALL TIME':<14}  {total_income:>14.2f}  {total_expenses:>14.2f}  {net_balance:>+14.2f}"
    )
    print(f"\n  Net historical balance USD: $ {net_balance:,.2f}")
    print(f"{'='*_COL_WIDTH}\n")