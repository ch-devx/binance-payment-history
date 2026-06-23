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

from api import fetch_all_deposits, fetch_all_pay
from filters import EXCLUDED_IDS, START_DT, is_excluded
from report import print_detail_table, print_header, print_monthly_balance

# ── Helpers ───────────────────────────────────────────────────────────────────


def _parse_ts(raw_ts: int | str) -> datetime:
    """Converts a millisecond or second UNIX timestamp to a UTC datetime."""
    raw_ts = int(raw_ts)
    if raw_ts > 1e12:
        return datetime.fromtimestamp(raw_ts / 1000, tz=timezone.utc)
    return datetime.fromtimestamp(raw_ts, tz=timezone.utc)


# ── CLI ───────────────────────────────────────────────────────────────────────


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Balance neto USDC/USDT: Pay + BEP20 (desde dic 2025)"
    )
    parser.add_argument(
        "--pay-tipo",
        default="ALL",
        help="Filtrar Pay por orderType: C2C, PAY, ALL (default: ALL)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Imprime el JSON crudo de las transacciones Pay para inspeccionar campos",
    )
    parser.add_argument(
        "--debug-limit",
        type=int,
        default=5,
        metavar="N",
        help="Numero de transacciones a mostrar en modo --debug (default: 5)",
    )
    return parser


# ── Modes ─────────────────────────────────────────────────────────────────────


def _run_debug(debug_limit: int) -> None:
    """Fetches Pay transactions and dumps the first N as raw JSON."""
    print(f"\n{'='*62}")
    print(f"  MODO DEBUG — primeras {debug_limit} transacciones Pay (JSON crudo)")
    print(f"{'='*62}\n")
    print("Consultando Binance Pay...")
    pay_txs = fetch_all_pay()
    muestra = pay_txs[:debug_limit]
    if not muestra:
        print("  No se encontraron transacciones Pay.")
    for i, tx in enumerate(muestra, 1):
        print(f"\n  ── Transaccion #{i} ──────────────────────────────────")
        print(json.dumps(tx, indent=4, ensure_ascii=False))
    print(f"\n{'='*62}")
    print(f"  Total transacciones Pay encontradas: {len(pay_txs)}")
    print(f"  (mostrando {len(muestra)} de {len(pay_txs)})")
    print(f"{'='*62}\n")


def _run_normal(pay_tipo: str) -> None:
    """Fetches all movements, applies filters, and prints the full report."""
    print_header(EXCLUDED_IDS, START_DT)

    ingresos: list[dict] = []
    egresos: list[dict] = []

    # ── 1. Binance Pay ────────────────────────────────────────────────────
    print("Consultando Binance Pay...")
    pay_txs = fetch_all_pay()

    excluidas_pay = 0
    for tx in pay_txs:
        amount = float(tx.get("amount", 0))
        order_type = tx.get("orderType", "")

        if pay_tipo != "ALL" and order_type != pay_tipo:
            continue
        if amount == 0:
            continue
        if order_type == "CRYPTO_BOX":
            continue
        if is_excluded(tx):
            excluidas_pay += 1
            continue

        fecha_dt = _parse_ts(tx["transactionTime"])
        registro = {
            "fecha_dt": fecha_dt,
            "tipo": f"Pay/{order_type}",
            "moneda": tx.get("currency"),
            "monto": abs(amount),
            "fuente": "Pay",
        }
        if amount > 0:
            ingresos.append(registro)
        else:
            egresos.append(registro)

    if excluidas_pay:
        print(f"  ({excluidas_pay} transacciones Pay omitidas por exclusion de ID)")

    # ── 2. BEP20 Deposits ─────────────────────────────────────────────────
    print("\nConsultando depositos BEP20...")
    for dep in fetch_all_deposits():
        amount = float(dep.get("amount", 0))
        if amount <= 0:
            continue
        ingresos.append(
            {
                "fecha_dt": _parse_ts(dep.get("insertTime", 0)),
                "tipo": "Deposito/BEP20",
                "moneda": dep.get("coin"),
                "monto": amount,
                "fuente": "BEP20",
            }
        )

    if not ingresos and not egresos:
        print("\n  No se encontraron movimientos con esos filtros.")
        return

    # ── Sort & render ──────────────────────────────────────────────────────
    ingresos.sort(key=lambda x: x["fecha_dt"])
    egresos.sort(key=lambda x: x["fecha_dt"])

    print_detail_table(ingresos, egresos)
    print_monthly_balance(ingresos, egresos)


# ── Entry point ───────────────────────────────────────────────────────────────


def main() -> None:
    args = _build_parser().parse_args()
    if args.debug:
        _run_debug(args.debug_limit)
    else:
        _run_normal(args.pay_tipo)


if __name__ == "__main__":
    main()