#!/usr/bin/env python
"""Script para leer y mostrar contenido de los PDFs del proyecto."""

import sys

# Instalar pdfplumber si no está disponible
try:
    import pdfplumber
except ImportError:
    print("Instalando pdfplumber...")
    import subprocess
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pdfplumber', '-q'])
    import pdfplumber

def read_pdf(filename, max_pages=10):
    """Lee un PDF y muestra su contenido."""
    print(f"\n{'='*80}")
    print(f"LEYENDO: {filename}")
    print('='*80)
    
    try:
        with pdfplumber.open(filename) as pdf:
            print(f"Total de páginas: {len(pdf.pages)}\n")
            for i, page in enumerate(pdf.pages[:max_pages]):
                text = page.extract_text()
                if text:
                    print(f"\n--- PÁGINA {i+1} ---")
                    print(text)
    except FileNotFoundError:
        print(f"ERROR: Archivo no encontrado: {filename}")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == '__main__':
    read_pdf('Proyecto de IA 1 - Parte I.pdf', max_pages=15)
    read_pdf('project_crash.pdf', max_pages=20)
