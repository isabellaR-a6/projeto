"""Minhas Finanças — app em Flet (Python).

Rodar no computador:   python main.py
Rodar no navegador:    python main.py --web
Gerar o app Android:   flet build apk   (veja o README desta pasta)
"""
import sys

import flet as ft

from financas_app.app import main

if __name__ == "__main__":
    if "--web" in sys.argv:
        ft.run(main, view=ft.AppView.WEB_BROWSER, port=int(sys.argv[sys.argv.index("--web") + 1]) if len(sys.argv) > sys.argv.index("--web") + 1 else 8550)
    else:
        ft.run(main)
