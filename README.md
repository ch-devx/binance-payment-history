# binance-pay-history

A lightweight CLI tool that calculates a net stablecoin balance across **Binance Pay transactions** and **BEP20 on-chain deposits**, producing a clean chronological report with monthly breakdowns.

Built to solve a practical accounting problem: Binance's own interface doesn't offer a unified view of Pay + on-chain inflows in one place, and its API caps results at 100 per call — silently dropping older data if you query naively.

---

## Features

- Fetches all **Binance Pay** C2C/P2P transactions (sent and received) from the funding wallet
- Fetches all **BEP20 network deposits** (BSC) confirmed on-chain
- Tracks **USDC and USDT** only — ignores spot, futures, and other assets
- Handles **API pagination** by splitting the date range into exact monthly windows, preventing silent data loss
- Warns when a window hits the 100-result cap
- Supports **ID-based exclusion** to filter out personal or non-business payments
- Outputs a detailed transaction table + monthly balance summary to the terminal

---

## Scope & limitations

- **USD-pegged assets only** — the tool assumes all tracked coins are stablecoins
  (1:1 with USD). No price conversion is performed. If you add non-pegged assets
  via `TRACKED_COINS`, the balance totals will be in mixed units and won't reflect
  USD value accurately.
- **Funding wallet only** — Pay transactions are fetched from `walletType=1`
  (funding wallet). Spot or futures wallets are not included.
- **100-result cap per window** — the Pay API returns at most 100 results per
  monthly window. The tool warns when this limit is reached, but does not
  sub-paginate within a window. Very high-volume months may be incomplete.

---

## How it works

Binance's Pay API returns at most 100 results per request. Rather than paginating by offset (which the API doesn't support), this tool splits the full date range into **monthly windows** and queries each independently. This guarantees full coverage even for high-volume months.

```
Dec 2025  →  [start_ms .. end_ms]  →  fetch  →  filter  →  accumulate
Jan 2026  →  [start_ms .. end_ms]  →  fetch  →  filter  →  accumulate
...
```

Each window result is filtered immediately (`filters.py`) before being accumulated — keeping memory usage low and logic separated from the HTTP layer.

---

## Project structure

```
binance-pay-history/
├── main.py          # CLI entry point and orchestration
├── api.py           # Binance API layer: signing, requests, pagination
├── filters.py       # Constants and filtering predicates
├── report.py        # Terminal output: tables and monthly summary
├── requirements.txt
├── .env             # Credentials — not versioned
├── .gitignore
└── run.sh           # Linux/macOS launcher
```

---

## Requirements

- Python 3.10+
- A Binance API key with **read-only** permissions (no trading or withdrawal access needed)

---

## Installation

```bash
git clone https://github.com/ch-devx/binance-pay-history
cd binance-pay-history
python -m venv .venv
```

**Linux / macOS:**
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows:**
```bat
.venv\Scripts\activate.bat
pip install -r requirements.txt
```

---

## Configuration

Create a `.env` file in the project root:

```env
API_KEY=your_binance_api_key
API_SECRET=your_binance_api_secret
EXCLUDED_IDS=123456789,987654321
```

| Variable       | Required | Description                                                              |
|----------------|----------|--------------------------------------------------------------------------|
| `API_KEY`      | Yes      | Binance API key (read-only).                                             |
| `API_SECRET`   | Yes      | Corresponding API secret.                                                |
| `START_DATE`   | Yes      | Report start date in `YYYY-MM-DD` format.                                |
| `TRACKED_COINS`| No       | Comma-separated list of coins to track. Default: `USDC,USDT`.            |
| `EXCLUDED_IDS` | No       | Comma-separated list of `binanceId` values to exclude from the report.   |

> The `.env` file is included in `.gitignore` and should never be committed.

---

## Usage

```bash
# Full report
python main.py

# C2C transactions only
python main.py --pay-type C2C

# Inspect the raw JSON of the first 10 transactions
python main.py --debug --debug-limit 10
```

**Linux / macOS shortcut:**
```bash
./run.sh
```

> **Note:** if you get `Permission denied`, run `chmod +x run.sh` once to make the script executable.

### CLI flags

| Flag | Description |
|---|---|
| `--pay-type {C2C,PAY,ALL}` | Filter Pay transactions by order type. Default: `ALL`. |
| `--debug` | Print raw JSON of the first N Pay transactions. |
| `--debug-limit N` | Number of transactions to show in debug mode. Default: `5`. |

---

## Finding a `binanceId` to exclude

1. Run `python main.py --debug`
2. Look for `payerInfo.binanceId` or `receiverInfo.binanceId` in the printed JSON
3. Add the ID to `EXCLUDED_IDS` in your `.env`, comma-separated if multiple

---

## Technical notes

- All timestamps are handled in **UTC**
- `recvWindow=10000` tolerates minor clock drift between your machine and Binance's servers
- BEP20 **withdrawals** use `status=6` (completed); **deposits** use `status=1` (confirmed) — pending transfers are excluded in both cases
- The deposit endpoint uses `status=1` (confirmed only) to avoid counting pending transfers