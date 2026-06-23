#!/usr/bin/env python3
"""
Binance - Balance neto en stablecoins (USDC / USDT)
=====================================================
Ingresos considerados:
  - Pagos recibidos via Binance Pay  → /sapi/v1/pay/transactions  (amount > 0)
  - Depositos BEP20 recibidos        → /sapi/v1/capital/deposit/hisrec (network=BSC)

Egresos considerados:
  - Pagos enviados via Binance Pay   → /sapi/v1/pay/transactions  (amount < 0)

Solo se contabilizan USDC y USDT, desde el 1 de diciembre de 2025.
Las claves de API y exclusiones se leen desde un archivo .env en el mismo directorio.

Dependencias: pip install requests python-dotenv
"""

import hashlib
import hmac
import time
import argparse
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv
import os
import calendar

# ─── CARGAR VARIABLES DE ENTORNO ──────────────────────────────────────────────
load_dotenv()
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

if not API_KEY or not API_SECRET:
    raise SystemExit(
        "Error: No se encontraron API_KEY y/o API_SECRET en el archivo .env"
    )

# IDs de Binance a excluir (pagos personales no relacionados al negocio).
# En el .env: EXCLUDED_IDS=123456789,987654321
_raw_excluded = os.getenv("EXCLUDED_IDS", "")
EXCLUDED_IDS = {uid.strip() for uid in _raw_excluded.split(",") if uid.strip()}

BASE_URL = "https://api.binance.com"
STABLECOINS = {"USDC", "USDT"}
START_DT = datetime(2025, 12, 1, tzinfo=timezone.utc)
# ──────────────────────────────────────────────────────────────────────────────


def sign(params: dict) -> str:
    query = urlencode(params)
    return hmac.new(API_SECRET.encode(), query.encode(), hashlib.sha256).hexdigest()


def api_get(endpoint: str, params: dict) -> dict | list:
    params["timestamp"] = int(time.time() * 1000)
    params["recvWindow"] = 10000
    params["signature"] = sign(params)
    headers = {"X-MBX-APIKEY": API_KEY}
    r = requests.get(BASE_URL + endpoint, params=params, headers=headers, timeout=10)
    if not r.ok:
        raise RuntimeError(f"HTTP {r.status_code} en {endpoint}: {r.text}")
    return r.json()


def iter_windows():
    """
    Genera ventanas mensuales exactas desde START_DT hasta hoy.
    Cada ventana va del dia 1 al ultimo dia del mes (28/29/30/31).
    """

    end_dt = datetime.now(timezone.utc)
    cursor = START_DT
    while cursor < end_dt:
        year, month = cursor.year, cursor.month
        last_day = calendar.monthrange(year, month)[1]
        win_end = min(
            datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc), end_dt
        )
        yield int(cursor.timestamp() * 1000), int(
            win_end.timestamp() * 1000
        ), cursor, win_end
        # Avanzar al primer dia del mes siguiente
        if month == 12:
            cursor = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            cursor = datetime(year, month + 1, 1, tzinfo=timezone.utc)


def is_excluded(tx: dict) -> bool:
    """
    Devuelve True si el binanceId del pagador o receptor
    está en la lista de exclusiones.
    """
    if not EXCLUDED_IDS:
        return False
    payer_id = str(tx.get("payerInfo", {}).get("binanceId", ""))
    receiver_id = str(tx.get("receiverInfo", {}).get("binanceId", ""))
    return payer_id in EXCLUDED_IDS or receiver_id in EXCLUDED_IDS


# ─── BINANCE PAY ──────────────────────────────────────────────────────────────


def fetch_all_pay() -> list:
    """
    Devuelve todas las transacciones Pay en stablecoins (funding wallet).
    amount > 0 = recibido, amount < 0 = enviado.
    """
    all_tx = []
    for start_ms, end_ms, cursor, win_end in iter_windows():
        print(
            f"  [Pay]    {cursor.strftime('%Y-%m-%d')} -> {win_end.strftime('%Y-%m-%d')} ...",
            end=" ",
        )
        body = api_get(
            "/sapi/v1/pay/transactions",
            {
                "startTime": start_ms,
                "endTime": end_ms,
                "limit": 100,
            },
        )
        if isinstance(body, dict) and body.get("code") != "000000":
            raise RuntimeError(f"Error Pay API: {body}")
        txs = body.get("data", []) if isinstance(body, dict) else []
        filtradas = [
            tx
            for tx in txs
            if tx.get("walletType") == 1 and tx.get("currency") in STABLECOINS
        ]
        print(f"{len(txs)} totales, {len(filtradas)} stablecoins")
        all_tx.extend(filtradas)
    return all_tx


# ─── DEPOSITOS BEP20 ─────────────────────────────────────────────────────────


def fetch_all_deposits() -> list:
    """Depositos BEP20 completados (status=1) en stablecoins."""
    all_dep = []
    for start_ms, end_ms, cursor, win_end in iter_windows():
        print(
            f"  [BEP20 deposito] {cursor.strftime('%Y-%m-%d')} -> {win_end.strftime('%Y-%m-%d')} ...",
            end=" ",
        )
        deps = api_get(
            "/sapi/v1/capital/deposit/hisrec",
            {
                "network": "BSC",
                "status": 1,
                "startTime": start_ms,
                "endTime": end_ms,
                "limit": 1000,
            },
        )
        filtradas = [d for d in deps if d.get("coin") in STABLECOINS]
        print(f"{len(deps)} totales, {len(filtradas)} stablecoins")
        all_dep.extend(filtradas)
    return all_dep


# ─── HELPERS ──────────────────────────────────────────────────────────────────


def parse_ts(raw_ts) -> datetime:
    """Convierte timestamp en ms o segundos a datetime UTC."""
    raw_ts = int(raw_ts)
    if raw_ts > 1e12:
        return datetime.fromtimestamp(raw_ts / 1000, tz=timezone.utc)
    return datetime.fromtimestamp(raw_ts, tz=timezone.utc)


def fmt_row(fecha_dt, tipo, moneda, monto, signo="+"):
    signo_monto = f"{signo}{abs(monto):.2f}"
    return (
        f"  {fecha_dt.strftime('%Y-%m-%d %H:%M:%S'):<22} "
        f"{tipo:<20} "
        f"{moneda:<8} "
        f"{signo_monto:>14}"
    )


# ─── MAIN ─────────────────────────────────────────────────────────────────────


def main():
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
    args = parser.parse_args()

    # ── MODO DEBUG ────────────────────────────────────────────────────────────
    if args.debug:
        import json

        print(f"\n{'='*62}")
        print(
            f"  MODO DEBUG — primeras {args.debug_limit} transacciones Pay (JSON crudo)"
        )
        print(f"{'='*62}\n")
        print("Consultando Binance Pay...")
        pay_txs = fetch_all_pay()
        muestra = pay_txs[: args.debug_limit]
        if not muestra:
            print("  No se encontraron transacciones Pay.")
        for i, tx in enumerate(muestra, 1):
            print(f"\n  ── Transaccion #{i} ──────────────────────────────────")
            print(json.dumps(tx, indent=4, ensure_ascii=False))
        print(f"\n{'='*62}")
        print(f"  Total transacciones Pay encontradas: {len(pay_txs)}")
        print(f"  (mostrando {len(muestra)} de {len(pay_txs)})")
        print(f"{'='*62}\n")
        return

    # ── MODO NORMAL ───────────────────────────────────────────────────────────
    print(f"\n{'='*62}")
    print("  BINANCE - Balance neto stablecoins (USDC + USDT)")
    print(f"  Desde: {START_DT.strftime('%Y-%m-%d')} hasta hoy")
    if EXCLUDED_IDS:
        print(f"  IDs excluidos: {len(EXCLUDED_IDS)}")
    print(f"{'='*62}\n")

    ingresos = []
    egresos = []

    # ── 1. Binance Pay ────────────────────────────────────────────────────────
    print("Consultando Binance Pay...")
    pay_txs = fetch_all_pay()

    excluidas_pay = 0
    for tx in pay_txs:
        amount = float(tx.get("amount", 0))
        order_type = tx.get("orderType", "")

        if args.pay_tipo != "ALL" and order_type != args.pay_tipo:
            continue
        if amount == 0:
            continue
        if order_type == "CRYPTO_BOX":
            continue
        if is_excluded(tx):
            excluidas_pay += 1
            continue

        fecha_dt = parse_ts(tx["transactionTime"])
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

    # ── 2. Depositos BEP20 ────────────────────────────────────────────────────
    print("\nConsultando depositos BEP20...")
    for dep in fetch_all_deposits():
        amount = float(dep.get("amount", 0))
        if amount <= 0:
            continue
        ingresos.append(
            {
                "fecha_dt": parse_ts(dep.get("insertTime", 0)),
                "tipo": "Deposito/BEP20",
                "moneda": dep.get("coin"),
                "monto": amount,
                "fuente": "BEP20",
            }
        )

    if not ingresos and not egresos:
        print("\n  No se encontraron movimientos con esos filtros.")
        return

    # ── Ordenar ───────────────────────────────────────────────────────────────
    ingresos.sort(key=lambda x: x["fecha_dt"])
    egresos.sort(key=lambda x: x["fecha_dt"])

    # ── Tabla de detalle ──────────────────────────────────────────────────────
    print(f"\n{'='*62}")
    print(f"  {'FECHA (UTC)':<22} {'TIPO':<20} {'MONEDA':<8} {'MONTO':>14}")
    print(f"{'='*62}")

    if ingresos:
        print(f"\n  >>> INGRESOS ({len(ingresos)})")
        print(f"  {'-'*58}")
        for ing in ingresos:
            print(
                fmt_row(ing["fecha_dt"], ing["tipo"], ing["moneda"], ing["monto"], "+")
            )

    if egresos:
        print(f"\n  >>> EGRESOS ({len(egresos)})")
        print(f"  {'-'*58}")
        for eg in egresos:
            print(fmt_row(eg["fecha_dt"], eg["tipo"], eg["moneda"], eg["monto"], "-"))

    # ── Balance mensual ───────────────────────────────────────────────────────
    mes_ing = defaultdict(float)
    mes_eg = defaultdict(float)

    for ing in ingresos:
        mes_ing[(ing["fecha_dt"].year, ing["fecha_dt"].month)] += ing["monto"]
    for eg in egresos:
        mes_eg[(eg["fecha_dt"].year, eg["fecha_dt"].month)] += eg["monto"]

    todos_los_meses = sorted(set(mes_ing.keys()) | set(mes_eg.keys()))

    MESES_ES = {
        1: "Enero",
        2: "Febrero",
        3: "Marzo",
        4: "Abril",
        5: "Mayo",
        6: "Junio",
        7: "Julio",
        8: "Agosto",
        9: "Sep",
        10: "Oct",
        11: "Nov",
        12: "Dic",
    }

    print(f"\n{'='*62}")
    print(f"  BALANCE MENSUAL")
    print(f"{'='*62}")
    print(f"  {'MES':<14}  {'INGRESOS':>14}  {'EGRESOS':>14}  {'BALANCE':>14}")
    print(f"  {'-'*14}  {'-'*14}  {'-'*14}  {'-'*14}")

    total_global_ing = 0.0
    total_global_eg = 0.0

    for year, month in todos_los_meses:
        ing = mes_ing.get((year, month), 0.0)
        eg = mes_eg.get((year, month), 0.0)
        bal = ing - eg
        total_global_ing += ing
        total_global_eg += eg
        label = f"{MESES_ES[month]} {year}"
        print(f"  {label:<14}  {ing:>14.2f}  {eg:>14.2f}  {bal:>+14.2f}")

    balance_neto = total_global_ing - total_global_eg

    print(f"  {'─'*14}  {'─'*14}  {'─'*14}  {'─'*14}")
    print(
        f"  {'TOTAL HIST.':<14}  {total_global_ing:>14.2f}  {total_global_eg:>14.2f}  {balance_neto:>+14.2f}"
    )
    print(f"\n  Balance neto historico USD: $ {balance_neto:,.2f}")
    print(f"{'='*62}\n")


if __name__ == "__main__":
    main()
