#!/usr/bin/env python3
"""
main.py
=======
CLI entry point and orchestration for the Binance net stablecoin balance report.

Imports:
  api.py     → fetch_all_pay, fetch_all_deposits
  filters.py → EXCLUDED_IDS, START_DT, is_excluded
  report.py  → print_header, print_detail_table, print_monthly_balance
"""

import argparse
import json
from datetime import datetime, timezone

from api import fetch_all_deposits, fetch_all_pay, fetch_all_withdrawals
from filters import EXCLUDED_IDS, START_DT, is_excluded
from report import print_detail_table, print_header, print_monthly_balance

# ── Helpers ───────────────────────────────────────────────────────────────────


def _parse_timestamp(raw_ts: int | str) -> datetime:
    """Converts a millisecond or second UNIX timestamp to a UTC datetime."""
    raw_ts = int(raw_ts)
    if raw_ts > 1e12:
        return datetime.fromtimestamp(raw_ts / 1000, tz=timezone.utc)
    return datetime.fromtimestamp(raw_ts, tz=timezone.utc)


# ── CLI ───────────────────────────────────────────────────────────────────────


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Net USDC/USDT balance: Binance Pay + BEP20 deposits (from Dec 2025)"
    )
    parser.add_argument(
        "--pay-type",
        default="ALL",
        help="Filter Pay transactions by orderType: C2C, PAY, ALL (default: ALL)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print the raw JSON of the first N Pay transactions to inspect available fields",
    )
    parser.add_argument(
        "--debug-limit",
        type=int,
        default=5,
        metavar="N",
        help="Number of transactions to show in --debug mode (default: 5)",
    )
    parser.add_argument(
        "--from",
        dest="start_date",
        default=None,
        metavar="YYYY-MM-DD",
        help="Override the start date for the report (default: START_DATE from .env or 2025-12-01)",
    )
    return parser


# ── Modes ─────────────────────────────────────────────────────────────────────


def _run_debug(debug_limit: int) -> None:
    """Fetches Pay transactions and dumps the first N as raw JSON."""
    print(f"\n{'='*62}")
    print(f"  DEBUG MODE — first {debug_limit} Pay transactions (raw JSON)")
    print(f"{'='*62}\n")
    print("Querying Binance Pay...")
    pay_txs = fetch_all_pay()
    sample = pay_txs[:debug_limit]
    if not sample:
        print("  No Pay transactions found.")
    for i, tx in enumerate(sample, 1):
        print(f"\n  ── Transaction #{i} ──────────────────────────────────")
        print(json.dumps(tx, indent=4, ensure_ascii=False))
    print(f"\n{'='*62}")
    print(f"  Total Pay transactions found: {len(pay_txs)}")
    print(f"  (showing {len(sample)} of {len(pay_txs)})")
    print(f"{'='*62}\n")


def _run_normal(pay_type: str) -> None:
    """Fetches all movements, applies filters, and prints the full report."""
    print_header(EXCLUDED_IDS, START_DT)

    income: list[dict] = []
    expenses: list[dict] = []

    # ── 1. Binance Pay ────────────────────────────────────────────────────
    print("Querying Binance Pay...")
    pay_txs = fetch_all_pay()

    excluded_count = 0
    for tx in pay_txs:
        amount = float(tx.get("amount", 0))
        order_type = tx.get("orderType", "")

        if pay_type != "ALL" and order_type != pay_type:
            continue
        if amount == 0:
            continue
        if order_type == "CRYPTO_BOX":
            continue
        if is_excluded(tx):
            excluded_count += 1
            continue

        record = {
            "date": _parse_timestamp(tx["transactionTime"]),
            "tx_type": f"Pay/{order_type}",
            "currency": tx.get("currency"),
            "amount": abs(amount),
            "source": "Pay",
        }
        if amount > 0:
            income.append(record)
        else:
            expenses.append(record)

    if excluded_count:
        print(f"  ({excluded_count} Pay transactions skipped due to ID exclusion)")

    # ── 2. BEP20 Deposits ─────────────────────────────────────────────────
    print("\nQuerying BEP20 deposits...")
    for dep in fetch_all_deposits():
        amount = float(dep.get("amount", 0))
        if amount <= 0:
            continue
        income.append(
            {
                "date": _parse_timestamp(dep.get("insertTime", 0)),
                "tx_type": "Deposit/BEP20",
                "currency": dep.get("coin"),
                "amount": amount,
                "source": "BEP20",
            }
        )

    # ── 3. BEP20 Withdrawals ──────────────────────────────────────────────
    print("\nQuerying BEP20 withdrawals...")
    for w in fetch_all_withdrawals():
        amount = float(w.get("amount", 0))
        if amount <= 0:
            continue
        expenses.append(
            {
                "date": _parse_timestamp(w.get("applyTime", 0)),
                "tx_type": "Withdraw/BEP20",
                "currency": w.get("coin"),
                "amount": amount,
                "source": "BEP20",
            }
        )

    if not income and not expenses:
        print("\n  No movements found matching the current filters.")
        return

    # ── Sort & render ──────────────────────────────────────────────────────
    income.sort(key=lambda x: x["date"])
    expenses.sort(key=lambda x: x["date"])

    print_detail_table(income, expenses)
    print_monthly_balance(income, expenses)


# ── Entry point ───────────────────────────────────────────────────────────────


def main() -> None:
    args = _build_parser().parse_args()

    if args.start_date:
        import filters
        try:
            filters.START_DT = datetime.strptime(args.start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            raise SystemExit(f"Error: --from '{args.start_date}' is not a valid date (expected YYYY-MM-DD).")

    if args.debug:
        _run_debug(args.debug_limit)
    else:
        _run_normal(args.pay_type)


if __name__ == "__main__":
    main()