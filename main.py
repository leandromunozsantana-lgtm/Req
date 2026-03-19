"""
Load Test — GET /api/current-user-data
Railway deployment — token via variable de entorno BEARER_TOKEN

Configura en Railway:
  Variables → BEARER_TOKEN = eyJhbGci...
"""

import asyncio
import csv
import json
import os
import time
from pathlib import Path

import httpx

# ─────────────────────────────────────────────
# CONFIG — ajusta TOTAL_REQ y CONCURRENCY aquí
# o agrégalas también como variables en Railway
# ─────────────────────────────────────────────
API_URL      = os.getenv("API_URL", "https://apidevnequialpha.space/api/current-user-data")
BEARER_TOKEN = os.getenv("BEARER_TOKEN", "")
TOTAL_REQ    = int(os.getenv("TOTAL_REQ", "50000"))
CONCURRENCY  = int(os.getenv("CONCURRENCY", "100"))
TIMEOUT_S    = 15
OUTPUT_CSV   = "resultados.csv"
# ─────────────────────────────────────────────


def build_headers() -> dict:
    return {
        "accept":          "*/*",
        "accept-language": "es-419,es;q=0.9",
        "authorization":   f"Bearer {BEARER_TOKEN}",
        "content-type":    "application/json",
        "origin":          "https://xn--eky-6ma.com",
        "priority":        "u=1, i",
        "referer":         "https://xn--eky-6ma.com/",
        "sec-fetch-dest":  "empty",
        "sec-fetch-mode":  "cors",
        "sec-fetch-site":  "cross-site",
        "user-agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/16.5 Mobile/15E148 Safari/604.1"
        ),
    }


def es_buena(data: dict) -> bool:
    return isinstance(data, dict) and len(data) > 0 and "detail" not in data


resultados_csv = []
lock = asyncio.Lock()
stats = {"buenas": 0, "malas": 0, "total": 0}


async def enviar(
    client:   httpx.AsyncClient,
    index:    int,
    semaforo: asyncio.Semaphore,
) -> None:
    async with semaforo:
        inicio = time.monotonic()
        try:
            resp = await client.get(API_URL, headers=build_headers())
            ms   = round((time.monotonic() - inicio) * 1000, 2)

            try:
                data   = resp.json()
                pretty = json.dumps(data, ensure_ascii=False)
            except Exception:
                data   = {}
                pretty = resp.text

            buena = resp.status_code == 200 and es_buena(data)

            async with lock:
                stats["total"] += 1
                if buena:
                    stats["buenas"] += 1
                    print(f"[#{index}] ✅ BUENA {resp.status_code} {ms}ms | {pretty[:120]}")
                else:
                    stats["malas"] += 1
                    print(f"[#{index}] ❌ MALA  {resp.status_code} {ms}ms | {pretty[:120]}")

                resultados_csv.append({
                    "index": index, "buena": buena,
                    "status_code": resp.status_code,
                    "response_ms": ms, "error": "",
                    "raw": resp.text[:300],
                })

        except httpx.TimeoutException:
            ms = round((time.monotonic() - inicio) * 1000, 2)
            async with lock:
                stats["total"] += 1
                stats["malas"] += 1
                print(f"[#{index}] ⏱ TIMEOUT {ms}ms")
                resultados_csv.append({
                    "index": index, "buena": False, "status_code": None,
                    "response_ms": ms, "error": "TIMEOUT", "raw": "",
                })

        except Exception as exc:
            ms = round((time.monotonic() - inicio) * 1000, 2)
            async with lock:
                stats["total"] += 1
                stats["malas"] += 1
                print(f"[#{index}] ⚠ ERROR {ms}ms | {exc}")
                resultados_csv.append({
                    "index": index, "buena": False, "status_code": None,
                    "response_ms": ms, "error": str(exc)[:100], "raw": "",
                })


async def main() -> None:
    if not BEARER_TOKEN:
        print("❌ ERROR: Configura la variable de entorno BEARER_TOKEN en Railway.")
        return

    print("=" * 60)
    print(f"  Load Test — GET /api/current-user-data")
    print(f"  Total requests : {TOTAL_REQ}")
    print(f"  Concurrencia   : {CONCURRENCY}")
    print(f"  Token          : {BEARER_TOKEN[:30]}...")
    print("=" * 60)

    semaforo = asyncio.Semaphore(CONCURRENCY)
    inicio   = time.monotonic()

    async with httpx.AsyncClient(timeout=TIMEOUT_S) as client:
        for i in range(0, TOTAL_REQ, CONCURRENCY):
            indices = range(i + 1, min(i + CONCURRENCY, TOTAL_REQ) + 1)
            tasks   = [enviar(client, idx, semaforo) for idx in indices]
            await asyncio.gather(*tasks)

            # Log de progreso cada 1000 requests
            if stats["total"] % 1000 == 0:
                elapsed = time.monotonic() - inicio
                rps     = stats["total"] / elapsed
                pct     = stats["buenas"] / stats["total"] * 100
                print(f"\n--- Progreso: {stats['total']}/{TOTAL_REQ} | "
                      f"✅ {stats['buenas']} | ❌ {stats['malas']} | "
                      f"{rps:.1f} req/s | éxito {pct:.1f}% ---\n")

    elapsed = time.monotonic() - inicio
    tiempos = [r["response_ms"] for r in resultados_csv]

    print("\n" + "=" * 60)
    print("  RESUMEN FINAL")
    print("=" * 60)
    print(f"  Total    : {TOTAL_REQ}")
    print(f"  ✅ Buenas: {stats['buenas']}")
    print(f"  ❌ Malas : {stats['malas']}")
    print(f"  Éxito    : {stats['buenas']/TOTAL_REQ*100:.1f}%")
    print(f"  Duración : {elapsed:.2f}s  |  {TOTAL_REQ/elapsed:.1f} req/s")
    print(f"  Prom. ms : {sum(tiempos)/len(tiempos):.0f}ms")
    print(f"  Mín/Máx  : {min(tiempos):.0f}ms / {max(tiempos):.0f}ms")
    print("=" * 60)

    ruta = Path(OUTPUT_CSV)
    with ruta.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "index", "buena", "status_code", "response_ms", "error", "raw",
        ])
        writer.writeheader()
        writer.writerows(resultados_csv)
    print(f"\n✔ CSV guardado: {ruta.resolve()}")


if __name__ == "__main__":
    asyncio.run(main())
