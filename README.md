# Binance Pay History — Balance Neto en Stablecoins

Script de línea de comandos que calcula el balance neto de pagos recibidos y enviados vía **Binance Pay**, sumando también los **depósitos recibidos por la red BEP20 (BSC)**. Solo contabiliza **USDC** y **USDT**, desde el **1 de diciembre de 2025**.

## ¿Qué hace?

- Consulta el endpoint `/sapi/v1/pay/transactions` para obtener todos los pagos C2C recibidos y enviados por Binance Pay.
- Consulta `/sapi/v1/capital/deposit/hisrec` para sumar los depósitos on-chain recibidos por la red BEP20.
- Filtra automáticamente:
  - Solo monedas **USDC** y **USDT**.
  - Solo movimientos de la **funding wallet**.
  - Excluye transacciones tipo `CRYPTO_BOX` (sobres rojos / recompensas).
  - Permite excluir manualmente transacciones de IDs de Binance específicos (ej. pagos de amigos/conocidos no relacionados al negocio).
- Genera un reporte con:
  - Detalle cronológico de ingresos y egresos.
  - Balance mensual (ingresos, egresos, neto por mes).
  - Balance histórico total.

## Requisitos

- Python 3.10+
- Una API Key de Binance con permisos de lectura (no requiere permisos de trading ni retiro).

## Instalación

1. Clona o descarga este proyecto.
2. Crea un entorno virtual e instala las dependencias:

   ```bash
   python -m venv .venv
   ```

   **Windows:**
   ```bat
   .venv\Scripts\activate.bat
   pip install requests python-dotenv
   ```

   **Linux / macOS:**
   ```bash
   source .venv/bin/activate
   pip install requests python-dotenv
   ```

3. Crea un archivo `.env` en la raíz del proyecto (ver sección siguiente).

## Configuración (`.env`)

Crea un archivo `.env` en el mismo directorio que `main.py`:

```env
API_KEY=tu_api_key_de_binance
API_SECRET=tu_api_secret_de_binance
EXCLUDED_IDS=123456789,987654321
```

| Variable | Obligatoria | Descripción |
|---|---|---|
| `API_KEY` | Sí | API Key generada en Binance (solo lectura). |
| `API_SECRET` | Sí | API Secret correspondiente. |
| `EXCLUDED_IDS` | No | Lista de `binanceId` separados por coma a excluir del cálculo (ej. pagos de amigos o conocidos). |

> ⚠️ El archivo `.env` nunca debe subirse a un repositorio. Ya está incluido en `.gitignore`.

## Uso

### Windows

Doble clic en `run.bat`, o desde terminal:

```bat
.venv\Scripts\python.exe main.py
```

### Linux / macOS

```bash
./run.sh
```

o directamente:

```bash
.venv/bin/python main.py
```

### Opciones disponibles

| Flag | Descripción |
|---|---|
| `--pay-tipo {C2C,PAY,ALL}` | Filtra las transacciones Pay por tipo de orden. Default: `ALL`. |
| `--debug` | Imprime el JSON crudo de las primeras transacciones Pay (útil para inspeccionar campos como `binanceId`). |
| `--debug-limit N` | Cantidad de transacciones a mostrar en modo `--debug`. Default: `5`. |

Ejemplos:

```bash
# Reporte completo normal
python main.py

# Solo transacciones C2C
python main.py --pay-tipo C2C

# Inspeccionar el JSON crudo de las primeras 10 transacciones
python main.py --debug --debug-limit 10
```

## Cómo obtener el `binanceId` de alguien para excluirlo

1. Corre el programa con `--debug`.
2. Busca en el JSON impreso los campos `payerInfo.binanceId` y `receiverInfo.binanceId` de la transacción correspondiente a esa persona.
3. Agrega ese número a `EXCLUDED_IDS` en el `.env`, separado por coma si hay varios.

## Notas técnicas

- Las consultas se hacen en **ventanas mensuales exactas** (del día 1 al último día de cada mes) para no exceder el límite de 100 resultados por llamada de la API de Binance Pay.
- Se usa `recvWindow=10000` para tolerar pequeñas diferencias de reloj entre tu equipo y los servidores de Binance.
- Los montos de retiros BEP20 **no** se contabilizan; solo se restan los pagos enviados vía Binance Pay y se suman los depósitos BEP20 recibidos.

## Estructura del proyecto

```
binance_payment_history/
├── main.py          # Script principal
├── .env             # Credenciales (no versionado)
├── .gitignore
├── run.bat          # Lanzador para Windows
├── run.sh           # Lanzador para Linux/macOS
└── README.md
```