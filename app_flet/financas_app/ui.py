"""Componentes visuais — mesma identidade do site (minimalista elegante).

Ameixa e lavanda sobre névoa lilás; títulos e valores em Bricolage Grotesque, texto em
Instrument Sans. Menos caixas: seções soltas, separadas por espaço e linhas finas.
Um único elemento marcante: a régua do mês.
"""
from __future__ import annotations

import flet as ft

# Cores com significado (valem nos dois temas)
ROXO = ft.Colors.PRIMARY            # ameixa no claro, lavanda clara no escuro
ROXO_ESCURO = "#43206a"
LILAS = "#b9a6e3"
VERDE = "#3a8f67"
AMBAR = "#c08427"
VERMELHO = "#c2335a"
CORES_ITENS = ["#5b2a86", "#8e3b8f", "#b4234a", "#3f3d9a", "#2f6f73", "#1f1630", "#7a4fc2", "#c06a2b"]

TEXTO_2 = ft.Colors.ON_SURFACE_VARIANT
BORDA = ft.Colors.OUTLINE_VARIANT
SUPERFICIE = ft.Colors.SURFACE_CONTAINER_LOWEST
FUNDO_SUAVE = ft.Colors.SURFACE_CONTAINER_LOW

FONTE_TITULO = "Bricolage"
FONTE_TEXTO = "Instrument"
FONTES = {
    FONTE_TITULO: "https://raw.githubusercontent.com/google/fonts/main/ofl/bricolagegrotesque/BricolageGrotesque%5Bopsz,wdth,wght%5D.ttf",
    FONTE_TEXTO: "https://raw.githubusercontent.com/google/fonts/main/ofl/instrumentsans/InstrumentSans%5Bwdth,wght%5D.ttf",
}


def tema(escuro: bool) -> ft.Theme:
    if escuro:
        esquema = ft.ColorScheme(
            primary="#c3a8f0", on_primary="#22123a", primary_container="#3a2c52", on_primary_container="#eadcff",
            secondary="#6f58a0", surface="#141019", on_surface="#eee8f7", on_surface_variant="#a397b8",
            surface_container_lowest="#1c1624", surface_container_low="#251e30", surface_container="#2a2236",
            surface_container_high="#30283d", outline="#4a3f5e", outline_variant="#2f2740", error="#f07a96")
    else:
        esquema = ft.ColorScheme(
            primary="#5b2a86", on_primary="#ffffff", primary_container="#ece5f7", on_primary_container="#2b1145",
            secondary="#b9a6e3", surface="#f6f4fa", on_surface="#1f1630", on_surface_variant="#6e6383",
            surface_container_lowest="#ffffff", surface_container_low="#efebf6", surface_container="#ece7f4",
            surface_container_high="#e6e0f0", outline="#cfc5de", outline_variant="#e3dcee", error="#b4234a")
    return ft.Theme(color_scheme_seed=esquema.primary, color_scheme=esquema, use_material3=True, font_family=FONTE_TEXTO,
                    scaffold_bgcolor=esquema.surface, card_bgcolor=esquema.surface_container_lowest,
                    page_transitions=ft.PageTransitionsTheme())


def texto(valor: str, size: float = 14, weight=None, color=None, max_lines=None, align=None, **kw) -> ft.Text:
    return ft.Text(valor, size=size, weight=weight, color=color, max_lines=max_lines,
                   overflow=ft.TextOverflow.ELLIPSIS if max_lines else None, text_align=align, **kw)


def numero_texto(valor: str, size: float = 16, weight=ft.FontWeight.W_600, color=None, **kw) -> ft.Text:
    """Valores em reais: fonte dos títulos, com espaçamento justo."""
    return ft.Text(valor, size=size, weight=weight, color=color, font_family=FONTE_TITULO,
                   style=ft.TextStyle(letter_spacing=-0.03 * size), **kw)


def sutil(valor: str, size: float = 12.5, **kw) -> ft.Text:
    return texto(valor, size=size, color=TEXTO_2, **kw)


def titulo(valor: str, size: float = 18) -> ft.Text:
    return ft.Text(valor, size=size, weight=ft.FontWeight.W_600, font_family=FONTE_TITULO,
                   style=ft.TextStyle(letter_spacing=-0.01 * size))


def cartao(conteudo: ft.Control, padding: float = 16, col=None, on_click=None, borda_topo: str | None = None) -> ft.Container:
    """Objeto destacado (cartão de crédito, meta): fundo próprio, borda fina, sem sombra."""
    return ft.Container(
        content=conteudo, padding=padding, col=col, on_click=on_click, ink=on_click is not None,
        bgcolor=SUPERFICIE, border_radius=16,
        border=ft.Border.all(1, BORDA) if not borda_topo else ft.Border(
            top=ft.BorderSide(3, borda_topo), left=ft.BorderSide(1, BORDA),
            right=ft.BorderSide(1, BORDA), bottom=ft.BorderSide(1, BORDA)),
    )


def destaque(rotulo: str, valor: str, detalhe: str = "", cor=None) -> ft.Column:
    """Número grande tipográfico (sem degradê)."""
    return ft.Column(spacing=4, controls=[
        sutil(rotulo, 14),
        numero_texto(valor, 44, ft.FontWeight.W_600, cor),
        *([sutil(detalhe, 13)] if detalhe else []),
    ])


def regua(entrou: float, partes: list[tuple[str, float, str]], fmt, falta: bool = False) -> ft.Column:
    """A régua do mês: o que entrou, dividido em para onde foi. partes = (nome, valor, cor)."""
    visiveis = [p for p in partes if p[1] > 0]
    barra = ft.Row(spacing=3, height=14, controls=[
        ft.Container(expand=max(1, round(v * 100)), bgcolor=cor, border_radius=3) for _, v, cor in visiveis
    ] or [ft.Container(expand=1, bgcolor=FUNDO_SUAVE, border_radius=3)])

    def item(nome, valor, cor, contorno=False):
        amostra = ft.Container(width=10, height=10, border_radius=3,
                               bgcolor=None if contorno else cor, border=ft.Border.all(2, TEXTO_2) if contorno else None)
        return ft.Column(spacing=2, col={"xs": 6, "md": 3}, controls=[
            ft.Row([amostra, sutil(nome, 12.5)], spacing=6),
            numero_texto(fmt(valor), 17)])

    legenda = ft.ResponsiveRow(spacing=12, run_spacing=12, controls=[
        item("Entrou", entrou, None, contorno=True), *[item(n, v, c) for n, v, c in visiveis]])
    return ft.Column([barra, legenda], spacing=14)


def numero(rotulo: str, valor: str, cor=None, col=None) -> ft.Container:
    """Número solto com uma linha fina à esquerda (sem caixa)."""
    return ft.Container(
        col=col, padding=ft.Padding.only(left=12, top=2, bottom=2),
        border=ft.Border(left=ft.BorderSide(2, LILAS)),
        content=ft.Column(spacing=2, controls=[sutil(rotulo, 12.5), numero_texto(valor, 17, color=cor)]),
    )


def chip(valor: str, tipo: str = "") -> ft.Container:
    cores = {"ok": VERDE, "aviso": AMBAR, "perigo": VERMELHO}
    cor = cores.get(tipo, ROXO)
    return ft.Container(texto(valor, 11.5, ft.FontWeight.W_600, cor), bgcolor=ft.Colors.with_opacity(0.13, cor),
                        border_radius=6, padding=ft.Padding.symmetric(horizontal=8, vertical=2))


def barra(fracao: float, cor=None) -> ft.ProgressBar:
    f = max(0.0, min(1.0, fracao))
    if cor is None:
        cor = VERMELHO if f >= 0.9 else AMBAR if f >= 0.7 else ROXO
    return ft.ProgressBar(value=f, color=cor, bgcolor=FUNDO_SUAVE, bar_height=6, border_radius=4)


def bolinha(cor, tamanho: int = 10) -> ft.Container:
    return ft.Container(width=tamanho, height=tamanho, bgcolor=cor, border_radius=tamanho)


def check(marcado: bool, on_click, cor=ROXO, tooltip: str = "", desativado: bool = False) -> ft.Container:
    """Bolinha de "pago": vazia ou preenchida com ✓. Tocar alterna."""
    return ft.Container(
        width=28, height=28, border_radius=28, alignment=ft.Alignment.CENTER,
        bgcolor=cor if marcado else None, border=ft.Border.all(2, cor if marcado else LILAS),
        content=ft.Icon(ft.Icons.CHECK_ROUNDED, size=16, color=ft.Colors.WHITE if marcado else ft.Colors.TRANSPARENT),
        on_click=None if desativado else on_click, tooltip=tooltip, opacity=0.6 if desativado else 1,
    )


def linha(principal: str, detalhe: str, valor: str, *, inicio: ft.Control | None = None, fim: ft.Control | None = None,
          cor_valor=None, riscado: bool = False, on_click=None, detalhe_valor: str = "") -> ft.Container:
    """Uma linha de lista: [bolinha] título e detalhe ........ valor [ação]."""
    estilo = ft.TextStyle(decoration=ft.TextDecoration.LINE_THROUGH, decoration_color=LILAS) if riscado else None
    return ft.Container(
        on_click=on_click, ink=on_click is not None, border_radius=10,
        padding=ft.Padding.symmetric(horizontal=4, vertical=11),
        content=ft.Row(spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
            *([ft.Container(inicio, width=28, alignment=ft.Alignment.CENTER)] if inicio else []),
            ft.Column(expand=True, spacing=1, controls=[
                ft.Text(principal, size=14.5, weight=ft.FontWeight.W_600, max_lines=2,
                        overflow=ft.TextOverflow.ELLIPSIS, style=estilo, color=TEXTO_2 if riscado else None),
                sutil(detalhe, 12.5),
            ]),
            ft.Column(spacing=0, horizontal_alignment=ft.CrossAxisAlignment.END, controls=[
                numero_texto(valor, 15, color=cor_valor, opacity=0.55 if riscado else 1),
                *([sutil(detalhe_valor, 11)] if detalhe_valor else []),
            ]),
            *([fim] if fim else []),
        ]),
    )


def lista(itens: list[ft.Control]) -> ft.Column:
    controles = []
    for i, item in enumerate(itens):
        if i:
            controles.append(ft.Divider(height=1, thickness=1, color=BORDA))
        controles.append(item)
    return ft.Column(spacing=0, controls=controles)


def grupo_dia(titulo_dia: str, total: str, itens: list[ft.Control]) -> ft.Column:
    """Lançamentos de um dia: título com linha forte embaixo, como num caderno de contas."""
    return ft.Column(spacing=0, controls=[
        ft.Container(padding=ft.Padding.only(bottom=6), border=ft.Border(bottom=ft.BorderSide(1, ft.Colors.ON_SURFACE)),
                     content=ft.Row([texto(titulo_dia, 14.5, ft.FontWeight.W_600), numero_texto(total, 14, ft.FontWeight.W_500, TEXTO_2)],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN)),
        lista(itens),
    ])


def vazio(mensagem: str) -> ft.Container:
    return ft.Container(sutil(mensagem, 14), padding=ft.Padding.symmetric(vertical=6))


def secao(nome: str, conteudo: list[ft.Control], acao: ft.Control | None = None, col=None) -> ft.Container:
    """Seção solta no fundo: título e conteúdo, sem caixa em volta."""
    topo = ft.Row([titulo(nome), *([acao] if acao else [])], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
    return ft.Container(col=col, padding=ft.Padding.only(bottom=8),
                        content=ft.Column([topo, *conteudo], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.STRETCH))


def alerta(mensagem: str, nivel: str) -> ft.Container:
    cor = VERMELHO if nivel == "perigo" else AMBAR if nivel == "aviso" else VERDE if nivel == "ok" else ROXO
    return ft.Container(
        bgcolor=ft.Colors.with_opacity(0.1, cor), border_radius=8,
        border=ft.Border(left=ft.BorderSide(3, cor)), padding=ft.Padding.symmetric(horizontal=12, vertical=10),
        content=ft.Text(mensagem, size=13.5),
    )


def tabela_comparacao(rotulo_depois: str, linhas_: list[tuple[str, float, float, bool]], fmt) -> ft.Column:
    """Tabela da simulação: rótulo | Hoje | Depois. linhas_ = (rótulo, antes, depois, maior_é_pior)."""
    def cel(conteudo):
        return ft.Container(conteudo, width=108, alignment=ft.Alignment.CENTER_RIGHT)

    cab = ft.Row([ft.Container(expand=True), cel(sutil("Hoje", 12)), cel(sutil(rotulo_depois, 12))], spacing=6)
    corpo = []
    for rotulo, antes, depois, inverter in linhas_:
        mudou = abs(antes - depois) >= 0.005
        piorou = depois > antes if inverter else depois < antes
        cor = None if not mudou else (VERMELHO if depois < 0 else AMBAR) if piorou else VERDE
        corpo.append(ft.Row([ft.Container(sutil(rotulo, 13), expand=True),
                             cel(numero_texto(fmt(antes), 13.5, ft.FontWeight.W_500, TEXTO_2)),
                             cel(numero_texto(fmt(depois), 13.5, ft.FontWeight.W_700, cor))], spacing=6))
    return ft.Column([cab, *corpo], spacing=6)


def estilo_botao() -> ft.ButtonStyle:
    return ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))
