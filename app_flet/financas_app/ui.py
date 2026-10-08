"""Componentes visuais reutilizáveis (tema roxo, mesmo do site)."""
from __future__ import annotations

import flet as ft

ROXO = "#7c3aed"
ROXO_ESCURO = "#4c1d95"
LILAS = "#a78bfa"
VERDE = "#10b981"
AMBAR = "#f59e0b"
VERMELHO = "#f43f5e"
CORES_ITENS = ["#7c3aed", "#a21caf", "#db2777", "#4f46e5", "#6d28d9", "#1e1b4b", "#0e7490", "#ea580c"]

FUNDO_SUAVE = ft.Colors.SURFACE_CONTAINER_LOW
TEXTO_2 = ft.Colors.ON_SURFACE_VARIANT
BORDA = ft.Colors.OUTLINE_VARIANT


def tema(escuro: bool) -> ft.Theme:
    return ft.Theme(
        color_scheme_seed=ROXO,
        use_material3=True,
        page_transitions=ft.PageTransitionsTheme(),
        scaffold_bgcolor="#110c1c" if escuro else "#f6f3fd",
        card_bgcolor="#1b1429" if escuro else "#ffffff",
    )


def texto(valor: str, size: float = 14, weight=None, color=None, max_lines=None, align=None, **kw) -> ft.Text:
    return ft.Text(valor, size=size, weight=weight, color=color, max_lines=max_lines,
                   overflow=ft.TextOverflow.ELLIPSIS if max_lines else None, text_align=align, **kw)


def sutil(valor: str, size: float = 12.5, **kw) -> ft.Text:
    return texto(valor, size=size, color=TEXTO_2, **kw)


def titulo(valor: str, size: float = 17) -> ft.Text:
    return texto(valor, size=size, weight=ft.FontWeight.W_700)


def cartao(conteudo: ft.Control, padding: float = 16, col=None, on_click=None, borda_topo: str | None = None) -> ft.Container:
    """Bloco branco/escuro com cantos arredondados — a "caixinha" padrão do app."""
    return ft.Container(
        content=conteudo, padding=padding, col=col, on_click=on_click, ink=on_click is not None,
        bgcolor=ft.Colors.SURFACE_CONTAINER_LOWEST, border_radius=20,
        border=ft.Border.all(1, BORDA) if not borda_topo else ft.Border(
            top=ft.BorderSide(4, borda_topo), left=ft.BorderSide(1, BORDA),
            right=ft.BorderSide(1, BORDA), bottom=ft.BorderSide(1, BORDA)),
        shadow=ft.BoxShadow(blur_radius=18, spread_radius=-6, color=ft.Colors.with_opacity(0.12, ROXO_ESCURO),
                            offset=ft.Offset(0, 6)),
    )


def destaque(rotulo: str, valor: str, detalhe: str = "", cores: list[str] | None = None) -> ft.Container:
    """Cartão grande em degradê roxo (saldo, total de entradas…)."""
    return ft.Container(
        gradient=ft.LinearGradient(begin=ft.Alignment.TOP_LEFT, end=ft.Alignment.BOTTOM_RIGHT,
                                   colors=cores or [ROXO_ESCURO, "#6d28d9", "#8b5cf6"]),
        border_radius=24, padding=ft.Padding.symmetric(horizontal=22, vertical=20),
        shadow=ft.BoxShadow(blur_radius=30, spread_radius=-8, color=ft.Colors.with_opacity(0.35, ROXO),
                            offset=ft.Offset(0, 12)),
        content=ft.Column(spacing=4, controls=[
            texto(rotulo, 13.5, color=ft.Colors.with_opacity(0.85, ft.Colors.WHITE)),
            texto(valor, 34, ft.FontWeight.W_800, ft.Colors.WHITE),
            *([texto(detalhe, 12.5, color=ft.Colors.with_opacity(0.85, ft.Colors.WHITE))] if detalhe else []),
        ]),
    )


def numero(rotulo: str, valor: str, cor=None, col=None) -> ft.Container:
    """Quadradinho com um número (Entradas, Gastos…)."""
    return ft.Container(
        col=col, padding=ft.Padding.symmetric(horizontal=14, vertical=12), border_radius=16,
        bgcolor=ft.Colors.SURFACE_CONTAINER_LOWEST,
        border=ft.Border(top=ft.BorderSide(3, LILAS), left=ft.BorderSide(1, BORDA),
                         right=ft.BorderSide(1, BORDA), bottom=ft.BorderSide(1, BORDA)),
        content=ft.Column(spacing=2, controls=[sutil(rotulo, 12), texto(valor, 16.5, ft.FontWeight.W_700, cor)]),
    )


def chip(valor: str, tipo: str = "") -> ft.Container:
    cores = {"ok": (VERDE, ft.Colors.with_opacity(0.15, VERDE)), "aviso": (AMBAR, ft.Colors.with_opacity(0.15, AMBAR)),
             "perigo": (VERMELHO, ft.Colors.with_opacity(0.15, VERMELHO))}
    cor, fundo = cores.get(tipo, (ROXO, ft.Colors.with_opacity(0.12, ROXO)))
    return ft.Container(texto(valor, 11.5, ft.FontWeight.W_600, cor), bgcolor=fundo, border_radius=99,
                        padding=ft.Padding.symmetric(horizontal=9, vertical=2))


def barra(fracao: float, cor: str | None = None) -> ft.ProgressBar:
    f = max(0.0, min(1.0, fracao))
    if cor is None:
        cor = VERMELHO if f >= 0.9 else AMBAR if f >= 0.7 else ROXO
    return ft.ProgressBar(value=f, color=cor, bgcolor=ft.Colors.with_opacity(0.12, ROXO), bar_height=8, border_radius=8)


def bolinha(cor: str, tamanho: int = 10) -> ft.Container:
    return ft.Container(width=tamanho, height=tamanho, bgcolor=cor, border_radius=tamanho)


def check(marcado: bool, on_click, cor: str = ROXO, tooltip: str = "", desativado: bool = False) -> ft.Container:
    """Bolinha de "pago": vazia ou preenchida com ✓. Tocar alterna."""
    return ft.Container(
        width=30, height=30, border_radius=30, alignment=ft.Alignment.CENTER,
        bgcolor=cor if marcado else None, border=ft.Border.all(2, cor if marcado else LILAS),
        content=ft.Icon(ft.Icons.CHECK_ROUNDED, size=18, color=ft.Colors.WHITE if marcado else ft.Colors.TRANSPARENT),
        on_click=None if desativado else on_click, tooltip=tooltip, opacity=0.6 if desativado else 1,
    )


def linha(principal: str, detalhe: str, valor: str, *, inicio: ft.Control | None = None, fim: ft.Control | None = None,
          cor_valor=None, riscado: bool = False, on_click=None, detalhe_valor: str = "") -> ft.Container:
    """Uma linha de lista: [bolinha] Título / detalhe ........ valor [ação]."""
    estilo = ft.TextStyle(decoration=ft.TextDecoration.LINE_THROUGH, decoration_color=LILAS) if riscado else None
    return ft.Container(
        on_click=on_click, ink=on_click is not None, border_radius=12,
        padding=ft.Padding.symmetric(horizontal=6, vertical=10),
        content=ft.Row(spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
            *([ft.Container(inicio, width=30, alignment=ft.Alignment.CENTER)] if inicio else []),
            ft.Column(expand=True, spacing=1, controls=[
                ft.Text(principal, size=14.5, weight=ft.FontWeight.W_600, max_lines=2,
                        overflow=ft.TextOverflow.ELLIPSIS, style=estilo,
                        color=TEXTO_2 if riscado else None),
                sutil(detalhe, 12),
            ]),
            ft.Column(spacing=0, horizontal_alignment=ft.CrossAxisAlignment.END, controls=[
                texto(valor, 14.5, ft.FontWeight.W_700, cor_valor, opacity=0.55 if riscado else 1),
                *([sutil(detalhe_valor, 11)] if detalhe_valor else []),
            ]),
            *([fim] if fim else []),
        ]),
    )


def lista(itens: list[ft.Control]) -> ft.Column:
    controles = []
    for i, item in enumerate(itens):
        if i:
            controles.append(ft.Divider(height=1, color=BORDA))
        controles.append(item)
    return ft.Column(spacing=0, controls=controles)


def vazio(mensagem: str) -> ft.Container:
    return ft.Container(sutil(mensagem, 13.5), padding=ft.Padding.symmetric(vertical=8))


def secao(nome: str, conteudo: list[ft.Control], acao: ft.Control | None = None, col=None) -> ft.Container:
    topo = ft.Row([titulo(nome), *([acao] if acao else [])], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
    return cartao(ft.Column([topo, *conteudo], spacing=10), col=col)


def alerta(mensagem: str, nivel: str) -> ft.Container:
    cor = VERMELHO if nivel == "perigo" else AMBAR if nivel == "aviso" else VERDE
    icone = ft.Icons.ERROR_OUTLINE if nivel == "perigo" else ft.Icons.INFO_OUTLINE
    return ft.Container(
        bgcolor=ft.Colors.with_opacity(0.12, cor), border_radius=12,
        border=ft.Border(left=ft.BorderSide(4, cor)), padding=ft.Padding.symmetric(horizontal=12, vertical=10),
        content=ft.Row([ft.Icon(icone, color=cor, size=18), ft.Text(mensagem, size=13.5, expand=True)], spacing=10),
    )


def tabela_comparacao(rotulo_depois: str, linhas_: list[tuple[str, float, float, bool]], fmt) -> ft.Column:
    """Tabela da simulação: rótulo | Hoje | Depois. linhas_ = (rótulo, antes, depois, maior_é_pior)."""
    def cel(t, cor=None, peso=None, sut=False):
        return ft.Container(texto(t, 13, peso, TEXTO_2 if sut else cor), width=104, alignment=ft.Alignment.CENTER_RIGHT)

    cab = ft.Row([ft.Container(expand=True), cel("HOJE", peso=ft.FontWeight.W_700, sut=True),
                  cel(rotulo_depois.upper(), peso=ft.FontWeight.W_700, sut=True)], spacing=6)
    corpo = []
    for rotulo, antes, depois, inverter in linhas_:
        mudou = abs(antes - depois) >= 0.005
        piorou = depois > antes if inverter else depois < antes
        cor = None if not mudou else (VERMELHO if depois < 0 else AMBAR) if piorou else VERDE
        corpo.append(ft.Row([ft.Container(sutil(rotulo, 13), expand=True), cel(fmt(antes), sut=True),
                             cel(fmt(depois), cor, ft.FontWeight.W_700)], spacing=6))
    return ft.Column([cab, *corpo], spacing=6)
