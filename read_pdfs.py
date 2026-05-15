#!/usr/bin/env python
"""Script para leer y mostrar contenido de los PDFs del proyecto.

Este script puede parecer que "se queda en bucle" si imprime demasiado texto.
Para evitarlo, puedes:
  - Guardar la extracción a un .txt con --out
  - Poner una pausa por página con --sleep-ms

Uso:
  python read_pdfs.py .\guia_maestra_project_crash.pdf --max-pages 16 --sleep-ms 50
  python read_pdfs.py .\guia_maestra_project_crash.pdf --max-pages 999 --out .\guia_dump.txt
"""

import argparse
import sys
import time

# Instalar pdfplumber si no está disponible
try:
    import pdfplumber
except ImportError:
    print("Instalando pdfplumber...")
    import subprocess

    subprocess.check_call([sys.executable, "-m", "pip", "install", "pdfplumber", "-q"])
    import pdfplumber


def read_pdf(
    filename: str,
    max_pages: int = 10,
    *,
    out: str | None = None,
    sleep_ms: int = 0,
    max_chars_per_page: int = 15_000,
):
    """Lee un PDF y muestra o guarda su contenido."""
    print(f"\n{'=' * 80}")
    print(f"LEYENDO: {filename}")
    print("=" * 80)

    sink = None
    try:
        if out:
            sink = open(out, "w", encoding="utf-8")

        with pdfplumber.open(filename) as pdf:
            total = len(pdf.pages)
            limit = min(total, max_pages)
            print(f"Total de páginas: {total} | Leyendo: {limit}\n")

            if sink:
                sink.write(f"PDF: {filename}\n")
                sink.write(f"Total de páginas: {total}\n")
                sink.write(f"Páginas extraídas: {limit}\n\n")

            for i in range(limit):
                page = pdf.pages[i]
                text = (page.extract_text() or "").strip()

                if len(text) > max_chars_per_page:
                    text = text[:max_chars_per_page] + "\n... (recortado) ...\n"

                header = f"\n--- PÁGINA {i + 1}/{limit} ---\n"

                # Progreso visible (evita que parezca colgado)
                print(f"[PAGE] {i + 1}/{limit}")

                if sink:
                    sink.write(header)
                    sink.write(text + "\n" if text else "(Sin texto extraíble en esta página)\n")
                else:
                    print(header, end="")
                    print(text if text else "(Sin texto extraíble en esta página)")

                if sleep_ms > 0:
                    time.sleep(sleep_ms / 1000.0)

        if sink:
            sink.close()
            print(f"\n[OK] Texto guardado en: {out}")

    except FileNotFoundError:
        print(f"ERROR: Archivo no encontrado: {filename}")
    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        try:
            if sink and not sink.closed:
                sink.close()
        except Exception:
            pass


def main():
    p = argparse.ArgumentParser()
    p.add_argument("pdf", help="Ruta del PDF a leer")
    p.add_argument("--max-pages", type=int, default=10)
    p.add_argument("--out", default="", help="Si se indica, guarda el texto en un .txt")
    p.add_argument("--sleep-ms", type=int, default=0, help="Pausa por página (ms)")
    p.add_argument("--max-chars-per-page", type=int, default=15000)
    args = p.parse_args()

    out = args.out.strip() or None
    read_pdf(
        args.pdf,
        max_pages=args.max_pages,
        out=out,
        sleep_ms=args.sleep_ms,
        max_chars_per_page=args.max_chars_per_page,
    )


if __name__ == "__main__":
    main()
