"""
filters.py
==========
Constants (STABLECOINS, START_DT, EXCLUDED_IDS) and all filtering predicates.
Imported by api.py (for fetch-level filtering) and main.py (for exclusion logic).
"""

import os
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

# ── Constants ─────────────────────────────────────────────────────────────────

_raw_coins = os.getenv("TRACKED_COINS", "USDC,USDT")
STABLECOINS: set[str] = {c.strip().upper() for c in _raw_coins.split(",") if c.strip()}

_raw_start = os.getenv("START_DATE", "2025-12-01")
try:
    START_DT: datetime = datetime.strptime(_raw_start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
except ValueError:
    raise SystemExit(f"Error: START_DATE '{_raw_start}' is not a valid date (expected YYYY-MM-DD).")

_raw_excluded = os.getenv("EXCLUDED_IDS", "")
EXCLUDED_IDS: set[str] = {uid.strip() for uid in _raw_excluded.split(",") if uid.strip()}

# ── Predicates ────────────────────────────────────────────────────────────────


def is_excluded(tx: dict) -> bool:
    """
    Returns True if the payer or receiver binanceId is in the EXCLUDED_IDS set.
    Used in main.py after fetch, so personal/non-business payments are skipped.
    """
    if not EXCLUDED_IDS:
        return False
    payer_id = str(tx.get("payerInfo", {}).get("binanceId", ""))
    receiver_id = str(tx.get("receiverInfo", {}).get("binanceId", ""))
    return payer_id in EXCLUDED_IDS or receiver_id in EXCLUDED_IDS


def is_valid_pay_tx(tx: dict) -> bool:
    """
    Returns True if the Pay transaction:
      - comes from the funding wallet (walletType == 1)
      - is denominated in a tracked stablecoin
    """
    return tx.get("walletType") == 1 and tx.get("currency") in STABLECOINS


def is_valid_deposit(dep: dict) -> bool:
    """Returns True if the deposit coin is a tracked stablecoin."""
    return dep.get("coin") in STABLECOINS

def is_valid_withdrawal(w: dict) -> bool:
    """Returns True if the withdrawal coin is a tracked stablecoin."""
    return w.get("coin") in STABLECOINS