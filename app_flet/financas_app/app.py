"""Minhas Finanças em Flet: as mesmas telas e regras do site, como app de computador e celular."""
from __future__ import annotations

import json
import time
from datetime import date, datetime

import flet as ft

from . import biometria
from . import regras as R
from . import ui
from .dados import BancoDemonstracao, BancoSupabase, ErroApp, pasta_dados
from .ui import AMBAR, LILAS, ROXO, ROXO_ESCURO, TEXTO_2, VERDE, VERMELHO

TELAS = [
    ("inicio", "Início", ft.Icons.HOME_OUTLINED, ft.Icons.HOME_ROUNDED),
    ("lancamentos", "Extrato", ft.Icons.RECEIPT_LONG_OUTLINED, ft.Icons.RECEIPT_LONG_ROUNDED),
    ("cartoes", "Cartões", ft.Icons.CREDIT_CARD_OUTLINED, ft.Icons.CREDIT_CARD_ROUNDED),
    ("simular", "Simular", ft.Icons.CALCULATE_OUTLINED, ft.Icons.CALCULATE_ROUNDED),
    ("entradas", "Entradas", ft.Icons.SOUTH_WEST_OUTLINED, ft.Icons.SOUTH_WEST_ROUNDED),
    ("metas", "Metas", ft.Icons.SAVINGS_OUTLINED, ft.Icons.SAVINGS_ROUNDED),
]
NOME_STATUS = {"aberta": "aberta", "fechada": "fechada", "vencida": "vencida", "paga": "paga", "vazia": "sem gastos"}
TRAVAR_DEPOIS_DE = 60  # segundos com o app em segundo plano até pedir a biometria de novo


class Preferencias:
    """Configurações deste aparelho (não vão para o banco)."""

    def __init__(self) -> None:
        self.arquivo = pasta_dados() / "preferencias.json"
        try:
            self.d = json.loads(self.arquivo.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.d = {}

    def get(self, chave, padrao=None):
        return self.d.get(chave, padrao)

    def set(self, chave, valor) -> None:
        self.d[chave] = valor
        self.arquivo.write_text(json.dumps(self.d), encoding="utf-8")


def montado(controle: ft.Control) -> bool:
    """No Flet 1.0, ler `.page` de um controle que ainda não está na tela dá erro."""
    try:
        return controle.page is not None
    except RuntimeError:
        return False


# ---------- Campos de formulário ----------
def campo_dinheiro(rotulo: str, valor: float | None = None, autofocus=False, on_change=None) -> ft.TextField:
    """Campo estilo app de banco: digita só números e a vírgula entra sozinha (1500 → 15,00)."""
    def mascara(e):
        digitos = "".join(ch for ch in e.control.value if ch.isdigit()).lstrip("0")[:11]
        e.control.value = R.brl(int(digitos) / 100)[3:] if digitos else ""
        e.control.update()
        if on_change:
            on_change(e)
    return ft.TextField(label=rotulo, value=R.brl(valor)[3:] if valor else "", hint_text="0,00",
                        keyboard_type=ft.KeyboardType.NUMBER, prefix_icon=ft.Icons.ATTACH_MONEY_ROUNDED,
                        autofocus=autofocus, on_change=mascara, border_radius=12)


def campo_data(rotulo: str, iso: str) -> ft.TextField:
    return ft.TextField(label=rotulo, value=f"{iso[8:10]}/{iso[5:7]}/{iso[:4]}", hint_text="dd/mm/aaaa",
                        keyboard_type=ft.KeyboardType.DATETIME, border_radius=12,
                        prefix_icon=ft.Icons.CALENDAR_MONTH_OUTLINED)


def ler_data(campo: ft.TextField) -> str | None:
    try:
        return datetime.strptime(campo.value.strip(), "%d/%m/%Y").date().isoformat()
    except ValueError:
        return None


def segmentado(opcoes: list[tuple[str, str]], atual: str, on_change=None) -> ft.SegmentedButton:
    return ft.SegmentedButton(
        segments=[ft.Segment(value=v, label=ft.Text(t, size=13.5, max_lines=1)) for v, t in opcoes], selected=[atual],
        show_selected_icon=False, on_change=on_change, expand=True,
        # Pouco espaço interno: "Dinheiro" cabe numa linha mesmo com 4 opções num celular de 360px.
        style=ft.ButtonStyle(padding=ft.Padding.symmetric(horizontal=2, vertical=10),
                             shape=ft.RoundedRectangleBorder(radius=10)),
    )


def seletor(rotulo: str, opcoes: list[tuple[str, str]], atual: str | None, on_select=None) -> ft.Dropdown:
    return ft.Dropdown(label=rotulo, value=atual, expand=True, on_select=on_select,
                       options=[ft.DropdownOption(key=k, text=t) for k, t in opcoes])


class App:
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.prefs = Preferencias()
        self.banco = None
        self.d: dict = {}
        self.mes = R.comp_atual()
        self.tela = "inicio"
        self.ocultar = bool(self.prefs.get("ocultar", False))
        self.filtro = "todos"
        self.busca = ""
        self.sim = {"tipo": "credito", "valor": "", "cartao": "", "data": R.hoje(), "modo": "avista", "parcelas": "2", "fatura": ""}
        self.salvando = False
        # Enquanto um formulário está aberto, o aviso "salvo" espera ele fechar (senão o aviso,
        # que também é uma janela no Flet, fica por cima e atrapalha fechar o formulário).
        self.avisos_adiados: list[str] | None = None
        self.travado = False
        self.saiu_em: float | None = None

    # ======================================================================
    # Início, login, código e trava
    # ======================================================================
    async def iniciar(self) -> None:
        p = self.page
        p.title = "Minhas Finanças"
        p.fonts = ui.FONTES
        p.theme = ui.tema(False)
        p.dark_theme = ui.tema(True)
        # Botões com cantos de 10px (em vez da pílula padrão do Material)
        for t in (p.theme, p.dark_theme):
            t.filled_button_theme = ft.FilledButtonTheme(style=ui.estilo_botao())
            t.outlined_button_theme = ft.OutlinedButtonTheme(style=ui.estilo_botao())
            t.text_button_theme = ft.TextButtonTheme(style=ui.estilo_botao())
        p.theme_mode = ft.ThemeMode.SYSTEM
        p.padding = 0
        p.window.width, p.window.height = 1180, 820
        p.window.min_width, p.window.min_height = 360, 600
        p.on_app_lifecycle_state_change = self.ao_mudar_estado
        p.on_resize = lambda e: self.render() if self.d and not self.travado else None
        self.carregando()
        modo = self.prefs.get("modo")
        if modo is None:
            return self.tela_login()
        await self.abrir_banco(modo)
        if not await self.banco.email():
            return self.tela_login()
        if await self.banco.precisa_codigo():
            return self.tela_codigo()
        # Já tinha sessão salva: pede a biometria antes de mostrar qualquer valor.
        if self.prefs.get("trava", True):
            return await self.tela_trava()
        await self.abrir_app()

    async def abrir_banco(self, modo: str) -> None:
        self.banco = BancoDemonstracao() if modo == "demonstracao" else BancoSupabase()
        await self.banco.iniciar()

    def carregando(self, msg: str = "Carregando…") -> None:
        p = self.page
        p.navigation_bar = None
        p.floating_action_button = None
        p.controls.clear()
        p.add(ft.Container(expand=True, alignment=ft.Alignment.CENTER, content=ft.Column(
            [ft.ProgressRing(color=ROXO), ui.sutil(msg, 14)], tight=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=14)))
        p.update()

    def tela_cheia(self, *controles: ft.Control) -> None:
        """Tela centralizada (login, código, trava) com fundo em degradê."""
        p = self.page
        p.navigation_bar = None
        p.floating_action_button = None
        p.controls.clear()
        p.add(ft.Container(
            expand=True, alignment=ft.Alignment.CENTER, padding=20,
            content=ft.Container(width=400, padding=28, border_radius=20, bgcolor=ft.Colors.SURFACE_CONTAINER_LOWEST,
                                 border=ft.Border.all(1, ui.BORDA),
                                 content=ft.Column(list(controles), tight=True, spacing=14,
                                                   horizontal_alignment=ft.CrossAxisAlignment.STRETCH)),
        ))
        p.update()

    def tela_login(self, erro: str = "") -> None:
        email = ft.TextField(label="E-mail", keyboard_type=ft.KeyboardType.EMAIL, border_radius=12, autofocus=True,
                             prefix_icon=ft.Icons.ALTERNATE_EMAIL_ROUNDED)
        senha = ft.TextField(label="Senha", password=True, can_reveal_password=True, border_radius=12,
                             prefix_icon=ft.Icons.PASSWORD_ROUNDED)
        msg = ft.Text(erro, color=VERMELHO, size=13)
        botao = ft.FilledButton("Entrar", height=48)

        async def entrar(_=None):
            if not email.value.strip() or not senha.value:
                msg.value = "Preencha e-mail e senha."
                return msg.update()
            botao.disabled, botao.content = True, "Entrando…"
            botao.update()
            try:
                await self.abrir_banco("supabase")
                await self.banco.entrar(email.value.strip(), senha.value)
                self.prefs.set("modo", "supabase")
                if await self.banco.precisa_codigo():
                    return self.tela_codigo()
                await self.abrir_app()
            except ErroApp as e:
                self.tela_login(str(e))

        async def demonstracao(_):
            self.prefs.set("modo", "demonstracao")
            await self.abrir_banco("demonstracao")
            await self.abrir_app()

        botao.on_click = entrar
        senha.on_submit = entrar
        self.tela_cheia(
            ft.Row([ft.Container(ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET_ROUNDED, color=ft.Colors.ON_PRIMARY, size=30),
                                 width=60, height=60, border_radius=18, alignment=ft.Alignment.CENTER,
                                 bgcolor=ROXO)],
                   alignment=ft.MainAxisAlignment.CENTER),
            ui.titulo("Minhas Finanças", 28),
            ui.sutil("Área particular. Entre com seu e-mail e senha.", 14),
            email, senha, msg, botao,
            ft.TextButton("Ver demonstração com dados de exemplo", icon=ft.Icons.SCIENCE_OUTLINED, on_click=demonstracao),
        )

    def tela_codigo(self, erro: str = "") -> None:
        codigo = ft.TextField(label="Código de 6 dígitos", keyboard_type=ft.KeyboardType.NUMBER, max_length=6,
                              text_align=ft.TextAlign.CENTER, text_size=24, autofocus=True, border_radius=12)
        msg = ft.Text(erro, color=VERMELHO, size=13)

        async def confirmar(_=None):
            try:
                await self.banco.verificar_codigo("".join(c for c in codigo.value if c.isdigit()))
                await self.abrir_app()
            except ErroApp as e:
                self.tela_codigo(str(e))

        async def outra_conta(_):
            await self.banco.sair()
            self.tela_login()

        codigo.on_submit = confirmar
        self.tela_cheia(
            ft.Icon(ft.Icons.SHIELD_OUTLINED, color=ROXO, size=40),
            ui.texto("Verificação", 22, ft.FontWeight.W_800),
            ui.sutil("Abra seu app autenticador e digite o código de Minhas Finanças.", 14),
            codigo, msg, ft.FilledButton("Confirmar", height=48, on_click=confirmar),
            ft.TextButton("Entrar com outra conta", on_click=outra_conta),
        )

    async def tela_trava(self) -> None:
        """App bloqueado: pede a biometria do aparelho (ou a senha, se o aparelho não tiver)."""
        self.travado = True
        sit = await biometria.situacao(self.page)
        msg = ft.Text("", color=VERMELHO, size=13, text_align=ft.TextAlign.CENTER)
        senha = ft.TextField(label="Sua senha", password=True, can_reveal_password=True, border_radius=12,
                             visible=not sit.disponivel, prefix_icon=ft.Icons.PASSWORD_ROUNDED)
        botao_senha = ft.FilledButton("Desbloquear com a senha", height=46, visible=not sit.disponivel)

        async def com_biometria(_=None):
            msg.value = ""
            msg.update()
            if await biometria.autenticar(self.page):
                await self.destravar()
            else:
                msg.value = "Não foi possível confirmar. Tente de novo ou use a senha."
                msg.update()

        async def com_senha(_=None):
            if self.banco.demonstracao or await self.banco.conferir_senha(senha.value or ""):
                await self.destravar()
            else:
                msg.value = "Senha incorreta."
                msg.update()

        def mostrar_senha(_):
            senha.visible = botao_senha.visible = True
            self.page.update()

        async def sair(_):
            await self.sair()

        botao_senha.on_click = com_senha
        senha.on_submit = com_senha
        explicacao = (f"Use o {sit.nome} para abrir. O app não vê nem guarda seu rosto ou digital: "
                      "quem confere é o próprio aparelho.") if sit.disponivel else sit.motivo
        self.tela_cheia(
            ft.Row([ft.Container(ft.Icon(ft.Icons.FINGERPRINT, size=44, color=ft.Colors.ON_PRIMARY), width=84, height=84,
                                 border_radius=84, alignment=ft.Alignment.CENTER,
                                 bgcolor=ROXO,
                                 on_click=com_biometria if sit.disponivel else None, ink=True)],
                   alignment=ft.MainAxisAlignment.CENTER),
            ui.texto("Minhas Finanças está travado", 20, ft.FontWeight.W_800, align=ft.TextAlign.CENTER),
            ui.sutil(explicacao, 13.5, align=ft.TextAlign.CENTER),
            *([ft.FilledButton(f"Desbloquear com {sit.nome}", icon=ft.Icons.FINGERPRINT, height=48,
                               on_click=com_biometria),
               ft.TextButton("Usar minha senha", on_click=mostrar_senha)] if sit.disponivel else []),
            senha, botao_senha, msg,
            ft.TextButton("Sair da conta", icon=ft.Icons.LOGOUT_ROUNDED, on_click=sair),
        )
        if sit.disponivel:
            await com_biometria()

    async def destravar(self) -> None:
        self.travado = False
        await self.abrir_app()

    async def ao_mudar_estado(self, e) -> None:
        """Ao voltar para o app depois de um tempo fora, trava de novo."""
        estado = e.state if hasattr(e, "state") else e.data
        if estado in (ft.AppLifecycleState.HIDE, ft.AppLifecycleState.PAUSE, "hide", "pause"):
            self.saiu_em = time.monotonic()
        elif estado in (ft.AppLifecycleState.RESUME, ft.AppLifecycleState.SHOW, "resume", "show"):
            fora = self.saiu_em and time.monotonic() - self.saiu_em > TRAVAR_DEPOIS_DE
            self.saiu_em = None
            if fora and self.d and not self.travado and self.prefs.get("trava", True):
                await self.tela_trava()

    async def sair(self) -> None:
        if self.banco:
            await self.banco.sair()
        self.prefs.set("modo", None)
        self.d = {}
        self.travado = False
        self.tela_login()

    # ======================================================================
    # Estrutura do app
    # ======================================================================
    async def abrir_app(self) -> None:
        self.carregando()
        try:
            self.d = await self.banco.carregar_tudo()
        except ErroApp as e:
            return self.tela_cheia(ui.titulo("Não foi possível carregar seus dados"), ui.sutil(str(e)),
                                   ft.FilledButton("Tentar de novo", on_click=lambda _: self.page.run_task(self.abrir_app)))
        self.render()

    def dinheiro(self, v) -> str:
        return "R$ ••••" if self.ocultar else R.brl(v)

    def aviso(self, msg: str, erro: bool = False) -> None:
        if self.avisos_adiados is not None and not erro:
            self.avisos_adiados.append(msg)
            return
        self.page.show_dialog(ft.SnackBar(content=ft.Text(msg, color=ft.Colors.WHITE), bgcolor=VERMELHO if erro else "#2e1065",
                                          behavior=ft.SnackBarBehavior.FLOATING, duration=2800))

    async def executar(self, fn, sucesso: str = "") -> bool:
        """Grava, recarrega e redesenha. Toques repetidos enquanto salva são ignorados (evita duplicar)."""
        if self.salvando:
            return False
        self.salvando = True
        try:
            await fn()
            self.d = await self.banco.carregar_tudo()
            self.render()
            if sucesso:
                self.aviso(sucesso)
            return True
        except ErroApp as e:
            self.aviso(str(e), erro=True)
            return False
        finally:
            self.salvando = False

    @property
    def largo(self) -> bool:
        return (self.page.width or 0) >= 900

    @property
    def celular(self) -> bool:
        return (self.page.width or 1000) < 600

    def largura_janela(self) -> float:
        """Formulários: 440px no computador, a tela toda (menos margem) no celular."""
        return max(260, min(440, (self.page.width or 440) - 72))

    def render(self) -> None:
        p = self.page
        indice = [t[0] for t in TELAS].index(self.tela)
        destinos = [ft.NavigationBarDestination(icon=i, selected_icon=s, label=n) for _, n, i, s in TELAS]

        def trocar(e):
            self.tela = TELAS[int(e.control.selected_index)][0]
            self.render()

        corpo = ft.Container(expand=True, padding=ft.Padding.only(left=16 if self.celular else 24, right=16 if self.celular else 24,
                                                                  top=6, bottom=96),
                             content=ft.Column(self.tela_atual(), spacing=30, scroll=ft.ScrollMode.AUTO, expand=True,
                                                       horizontal_alignment=ft.CrossAxisAlignment.STRETCH))
        if self.largo:
            p.navigation_bar = None
            menu = ft.NavigationRail(
                selected_index=indice, on_change=trocar, label_type=ft.NavigationRailLabelType.ALL, min_width=96,
                leading=ft.Container(ft.Text("Minhas\nFinanças", size=16, weight=ft.FontWeight.W_700, font_family=ui.FONTE_TITULO,
                                              text_align=ft.TextAlign.CENTER), padding=ft.Padding.symmetric(vertical=16)),
                destinations=[ft.NavigationRailDestination(icon=i, selected_icon=s, label=n) for _, n, i, s in TELAS])
            area = ft.Row([menu, ft.VerticalDivider(width=1), ft.Column([self.cabecalho(), corpo], expand=True, spacing=0)],
                          expand=True, spacing=0)
        else:
            p.navigation_bar = ft.NavigationBar(selected_index=indice, on_change=trocar, destinations=destinos,
                                                label_behavior=ft.NavigationBarLabelBehavior.ALWAYS_SHOW)
            area = ft.Column([self.cabecalho(), corpo], expand=True, spacing=0)
        p.floating_action_button = None if self.tela == "simular" else ft.FloatingActionButton(
            icon=ft.Icons.ADD_ROUNDED, bgcolor=ROXO, foreground_color=ft.Colors.ON_PRIMARY, tooltip="Novo lançamento",
            shape=ft.RoundedRectangleBorder(radius=16),
            on_click=lambda _: self.form_lancamento())
        p.controls.clear()
        p.add(ft.SafeArea(area, expand=True))
        p.update()

    def cabecalho(self) -> ft.Container:
        def mudar_mes(n):
            def h(_):
                self.mes = R.comp_atual() if n == 0 else R.somar_meses(self.mes, n)
                self.render()
            return h

        def alternar_ocultar(_):
            self.ocultar = not self.ocultar
            self.prefs.set("ocultar", self.ocultar)
            self.render()

        async def travar(_):
            await self.tela_trava()

        async def sair(_):
            await self.sair()

        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=8, vertical=6),
            content=ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                ft.Row(spacing=0, controls=[
                    ft.IconButton(ft.Icons.CHEVRON_LEFT_ROUNDED, on_click=mudar_mes(-1), tooltip="Mês anterior"),
                    ft.Container(ui.titulo(R.nome_mes(self.mes).capitalize(), 18 if self.celular else 21), border_radius=8, ink=True,
                                 padding=ft.Padding.symmetric(horizontal=6, vertical=2), on_click=mudar_mes(0),
                                 tooltip="Voltar para o mês atual"),
                    ft.IconButton(ft.Icons.CHEVRON_RIGHT_ROUNDED, on_click=mudar_mes(1), tooltip="Próximo mês"),
                ]),
                ft.Row(spacing=0, controls=[
                    ft.IconButton(ft.Icons.VISIBILITY_OFF_ROUNDED if self.ocultar else ft.Icons.VISIBILITY_ROUNDED,
                                  tooltip="Mostrar valores" if self.ocultar else "Esconder valores",
                                  on_click=alternar_ocultar),
                    *([ft.PopupMenuButton(icon=ft.Icons.MORE_VERT_ROUNDED, tooltip="Mais opções", items=[
                        ft.PopupMenuItem(content="Segurança", icon=ft.Icons.SETTINGS_OUTLINED,
                                         on_click=lambda _: self.page.run_task(self.dialogo_seguranca)),
                        ft.PopupMenuItem(content="Travar agora", icon=ft.Icons.LOCK_ROUNDED, on_click=travar),
                        ft.PopupMenuItem(content="Sair", icon=ft.Icons.LOGOUT_ROUNDED, on_click=sair),
                    ])] if self.celular else [
                        ft.IconButton(ft.Icons.SETTINGS_OUTLINED, tooltip="Segurança", on_click=lambda _: self.page.run_task(self.dialogo_seguranca)),
                        ft.IconButton(ft.Icons.LOCK_ROUNDED, tooltip="Travar agora", on_click=travar),
                        ft.IconButton(ft.Icons.LOGOUT_ROUNDED, tooltip="Sair", on_click=sair),
                    ]),
                ]),
            ]),
        )

    def tela_atual(self) -> list[ft.Control]:
        topo = []
        if self.banco and self.banco.demonstracao:
            topo.append(ui.alerta("Modo demonstração: dados de exemplo guardados só neste aparelho. "
                                  "Para usar sua conta, toque em Sair e entre com e-mail e senha.", "info"))
        return topo + {
            "inicio": self.tela_inicio, "lancamentos": self.tela_lancamentos, "cartoes": self.tela_cartoes,
            "simular": self.tela_simular, "entradas": self.tela_entradas, "metas": self.tela_metas,
        }[self.tela]()

    def cartao_de(self, cid):
        return next((c for c in self.d["cartoes"] if c["id"] == cid), None)

    def cor_lancamento(self, l: dict) -> str:
        if l["tipo"] == "receita":
            return VERDE
        c = self.cartao_de(l.get("cartao_id"))
        return c.get("cor", ROXO) if c else ROXO

    # ======================================================================
    # Início
    # ======================================================================
    def alertas(self, r: R.Resumo) -> list[tuple[str, str]]:
        d, lista = self.d, []
        for f in R.faturas_atrasadas(d, r.parcelas):
            lista.append(("perigo", f"Fatura {f.cartao['nome']} de {R.nome_mes(f.comp, False)} venceu há "
                                    f"{-R.dias_ate(f.vencimento)} dias: faltam {self.dinheiro(f.a_pagar)}"))
        for k in (R.somar_meses(R.comp_atual(), -1), R.comp_atual(), R.somar_meses(R.comp_atual(), 1)):
            for c in d["cartoes"]:
                f = R.fatura(d, c, k, r.parcelas)
                dias = R.dias_ate(f.vencimento)
                if f.a_pagar > 0 and 0 <= dias <= 5:
                    quando = "hoje" if dias == 0 else "amanhã" if dias == 1 else f"em {dias} dias"
                    lista.append(("aviso", f"Fatura {c['nome']} vence {quando}: faltam {self.dinheiro(f.a_pagar)}"))
        for c in d["cartoes"]:
            usado, limite = R.limite_usado(d, c, r.parcelas), float(c["limite"])
            if limite and usado / limite >= 0.8:
                lista.append(("perigo" if usado >= limite else "aviso",
                              f"Você já usou {round(usado / limite * 100)}% do limite do {c['nome']}"))
        if r.saldo < 0:
            lista.append(("perigo", f"Pelo previsto, {R.nome_mes(r.comp, False)} fecha no negativo"))
        return lista

    def tela_inicio(self) -> list[ft.Control]:
        d = self.d
        r = R.resumo_mes(d, self.mes)
        if not any(d[t] for t in ("lancamentos", "cartoes", "metas")):
            return [ui.cartao(ft.Column([
                ui.titulo("Vamos começar", 20),
                ui.sutil("Alguns passos e o painel já começa a mostrar para onde vai o dinheiro.", 14),
                ft.FilledButton("Cadastrar um cartão", icon=ft.Icons.CREDIT_CARD_ROUNDED, on_click=lambda _: self.form_cartao()),
                ft.OutlinedButton("Lançar salário ou gasto", icon=ft.Icons.ADD_ROUNDED, on_click=lambda _: self.form_lancamento()),
                ft.OutlinedButton("Criar uma meta", icon=ft.Icons.SAVINGS_OUTLINED, on_click=lambda _: self.form_meta()),
            ], spacing=12))]

        negativo = r.saldo < 0
        partes = [("Gastos e faturas", r.gastos, ROXO), ("Contas a pagar", r.total_contas_pendentes, AMBAR),
                  ("Guardado nas metas", max(0, r.guardado), LILAS),
                  ("Falta para fechar o mês" if negativo else "Sobra", abs(r.saldo), VERMELHO if negativo else VERDE)]
        controles: list[ft.Control] = [ft.Column(spacing=6, controls=[
            ui.sutil(f"{'Pelo previsto, faltam' if negativo else 'Sobra prevista'} em {R.nome_mes(self.mes, False)}", 14.5),
            ui.numero_texto(self.dinheiro(abs(r.saldo)), 52, ft.FontWeight.W_600, VERMELHO if negativo else None),
            ft.Container(height=6),
            ui.regua(r.total_receitas, partes, self.dinheiro),
            *([ui.sutil(f"Ainda falta pagar {self.dinheiro(r.a_pagar)} este mês, entre faturas e contas.", 13.5)] if r.a_pagar else []),
        ])]
        alertas = self.alertas(r)
        if alertas:
            controles.append(ui.secao("Atenção", [ft.Column([ui.alerta(m, n) for n, m in alertas], spacing=8,
                                                              horizontal_alignment=ft.CrossAxisAlignment.STRETCH)]))

        # Vencimentos do mês (faturas com valor)
        atrasadas = R.faturas_atrasadas(d, r.parcelas) if self.mes == R.comp_atual() else []
        # Uma fatura atrasada do próprio mês já está em r.faturas: não repete.
        ja = {(f.cartao["id"], f.comp) for f in atrasadas}
        faturas = sorted(atrasadas + [f for f in r.faturas if f.total > 0 and (f.cartao["id"], f.comp) not in ja],
                         key=lambda f: f.vencimento)
        venc = [self.linha_fatura(f) for f in faturas] + [self.linha_conta(c) for c in r.contas]
        # Cartões
        cartoes = [self.resumo_limite(c, R.limite_usado(d, c, r.parcelas)) for c in d["cartoes"]]
        # Categorias
        cats = sorted(r.por_categoria.items(), key=lambda x: -x[1])
        maior = cats[0][1] if cats else 1
        categorias = [ft.Column([
            ft.Row([ui.texto(R.categoria(cid)["nome"], 13.5), ui.texto(self.dinheiro(v), 13.5, ft.FontWeight.W_700)],
                   alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ui.barra(v / maior, ROXO)], spacing=4) for cid, v in cats]
        if r.total_compras_credito:
            categorias.insert(0, ui.sutil(f"Inclui {self.dinheiro(r.total_compras_credito)} comprados no crédito este mês.", 12))
        metas = []
        for m in d["metas"]:
            g = R.guardado_na_meta(d, m["id"])
            metas.append(ft.Column([
                ft.Row([ui.bolinha(m.get("cor", ROXO)), ui.texto(m["nome"], 14, ft.FontWeight.W_600, expand=True),
                        ui.sutil(f"{round(g / float(m['alvo']) * 100)}%")]),
                ui.barra(g / float(m["alvo"]), m.get("cor", ROXO)),
                ui.sutil(f"{self.dinheiro(g)} de {self.dinheiro(m['alvo'])}", 12)], spacing=5))

        controles.append(ft.ResponsiveRow(spacing=14, run_spacing=14, controls=[
            ui.secao("Vencimentos", [ui.lista(venc) if venc else ui.vazio("Nada para pagar neste mês.")], col={"xs": 12, "md": 6}),
            ui.secao("Cartões", [ft.Column(cartoes, spacing=14) if cartoes else ui.vazio("Nenhum cartão cadastrado.")],
                     acao=ft.TextButton("Ver faturas", on_click=lambda _: self.ir("cartoes")), col={"xs": 12, "md": 6}),
            ui.secao("Para onde foi o dinheiro", categorias or [ui.vazio("Nenhum gasto neste mês ainda.")], col={"xs": 12, "md": 6}),
            ui.secao("Metas", [ft.Column(metas, spacing=14) if metas else ui.vazio("Nenhuma meta ainda.")],
                     acao=ft.TextButton("Ver metas", on_click=lambda _: self.ir("metas")), col={"xs": 12, "md": 6}),
        ]))
        return controles

    def ir(self, tela: str) -> None:
        self.tela = tela
        self.render()

    def resumo_limite(self, c: dict, usado: float) -> ft.Column:
        limite = float(c["limite"])
        return ft.Column(spacing=6, controls=[
            ft.Row([ui.bolinha(c.get("cor", ROXO)), ui.texto(c["nome"], 14.5, ft.FontWeight.W_700, expand=True),
                    ui.sutil(f"limite {self.dinheiro(limite)}")]),
            ui.barra(usado / limite if limite else 0),
            ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                ft.Column([ui.sutil("Gastei", 11.5), ui.texto(self.dinheiro(usado), 14, ft.FontWeight.W_700)], spacing=0),
                ft.Column([ui.sutil("Disponível", 11.5), ui.texto(self.dinheiro(limite - usado), 14, ft.FontWeight.W_700,
                                                                  VERMELHO if limite - usado < 0 else VERDE)],
                          spacing=0, horizontal_alignment=ft.CrossAxisAlignment.END),
            ]),
        ])

    def chip_vencimento(self, status: str, venc: str) -> ft.Container:
        dias = R.dias_ate(venc)
        if status == "paga":
            return ui.chip("paga", "ok")
        quando = "hoje" if dias == 0 else "amanhã" if dias == 1 else "ontem" if dias == -1 else \
            f"em {dias} dias" if dias > 0 else f"há {-dias} dias"
        if status == "vencida":
            return ui.chip(f"venceu {quando}", "perigo")
        return ui.chip(f"vence {quando}", "aviso" if dias <= 3 else "")

    def linha_fatura(self, f: R.Fatura) -> ft.Container:
        pago = f.status == "paga"
        return ui.linha(
            f"Fatura {f.cartao['nome']}", f"{R.nome_mes(f.comp, False)}, vence {R.data_curta(f.vencimento)}",
            self.dinheiro(f.a_pagar if f.parcial else f.total), detalhe_valor="falta" if f.parcial else "",
            inicio=ui.bolinha(f.cartao.get("cor", ROXO)), riscado=pago,
            abaixo=self.chip_vencimento(f.status, f.vencimento),
            fim=ui.check(pago, lambda _, f=f: self.page.run_task(self.alternar_fatura, f.cartao["id"], f.comp),
                         tooltip="Desmarcar" if pago else "Marcar como paga"))

    def linha_conta(self, c: dict) -> ft.Container:
        pago = bool(c["pagamento"])
        return ui.linha(c["conta"]["descricao"], f"dia {R.data_curta(c['vencimento'])}", self.dinheiro(c["conta"]["valor"]),
                        inicio=ui.bolinha(ROXO), riscado=pago,
                        abaixo=self.chip_vencimento(c["status"], c["vencimento"]),
                        fim=ui.check(pago, lambda _, c=c: self.page.run_task(self.alternar_conta, c["conta"], c["comp"])))

    # ======================================================================
    # Lançamentos
    # ======================================================================
    def lancamento_pago(self, l: dict) -> bool:
        c = self.cartao_de(l.get("cartao_id"))
        if not c:
            return l.get("pago") is True
        return all(R.parcela_quitada(self.d, p) for p in R.parcelas_de(l, c))

    def itens_filtrados(self, r: R.Resumo) -> list[dict]:
        """Tudo o que foi feito no mês, pela data (crédito aparece no mês da compra), com filtro e busca."""
        itens = r.receitas + r.avulsas + r.compras_credito
        if self.filtro == "receitas":
            itens = [l for l in itens if l["tipo"] == "receita"]
        elif self.filtro != "todos":
            itens = [l for l in itens if R.forma_de(l) == self.filtro]
        if self.busca.strip():
            b = self.busca.strip().lower()
            itens = [l for l in itens if b in f"{l['descricao']} {R.categoria(l['categoria'])['nome']}".lower()]
        itens.sort(key=lambda l: (l["data"], str(l.get("created_at", ""))), reverse=True)
        return itens

    def tela_lancamentos(self) -> list[ft.Control]:
        r = R.resumo_mes(self.d, self.mes)
        itens = self.itens_filtrados(r)
        entradas = R.soma(l["valor"] for l in itens if l["tipo"] == "receita")
        saidas = R.soma(l["valor"] for l in itens if l["tipo"] == "despesa")

        def filtrar(f):
            def h(_):
                self.filtro = f
                self.render()
            return h

        def buscar(e):
            self.busca = e.control.value
            lista_ctrl.controls = [self.lista_lancamentos(r)]
            lista_ctrl.update()

        filtros = [("todos", "Tudo"), *[(f["id"], f["nome"]) for f in R.FORMAS], ("receitas", "Entradas")]
        lista_ctrl = ft.Column([self.lista_lancamentos(r)])
        return [ui.cartao(ft.Column(spacing=12, controls=[
            ui.titulo(f"Extrato de {R.nome_mes(self.mes, False)}"),
            ft.Row(wrap=True, spacing=8, run_spacing=8, controls=[
                ft.Chip(label=ft.Text(n), selected=self.filtro == f, on_select=filtrar(f), selected_color=ft.Colors.with_opacity(0.25, ROXO))
                for f, n in filtros]),
            ft.TextField(hint_text="Buscar por descrição ou categoria", value=self.busca, on_change=buscar,
                         prefix_icon=ft.Icons.SEARCH, border_radius=12, dense=True),
            ft.Container(bgcolor=ft.Colors.with_opacity(0.1, ROXO), border_radius=12,
                         padding=ft.Padding.symmetric(horizontal=14, vertical=10),
                         content=ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                             ft.Row([ui.sutil("Entradas", 13), ui.texto(self.dinheiro(entradas), 13.5, ft.FontWeight.W_700, VERDE)], spacing=6),
                             ft.Row([ui.sutil("Saídas", 13), ui.texto(self.dinheiro(saidas), 13.5, ft.FontWeight.W_700)], spacing=6)])),
            lista_ctrl,
        ]))]

    def lista_lancamentos(self, r: R.Resumo) -> ft.Control:
        itens = self.itens_filtrados(r)
        grupos: dict[str, list[dict]] = {}
        for l in itens:
            grupos.setdefault(l["data"], []).append(l)
        linhas = [ui.grupo_dia(self.nome_dia(dia), self.dinheiro(abs(R.soma((1 if l["tipo"] == "receita" else -1) * float(l["valor"]) for l in doDia))),
                               [self.linha_lancamento(l) for l in doDia])
                  for dia, doDia in grupos.items()]
        if not linhas:
            return ui.vazio(f"Nada lançado em {R.nome_mes(self.mes, False)}" + (" com esse filtro." if self.filtro != "todos" or self.busca.strip() else "."))
        antigas = [p for p in r.parcelas_mes if p.lanc["data"][:7] != self.mes]
        extra = []
        if antigas and self.filtro in ("todos", "credito") and not self.busca.strip():
            extra.append(ft.ExpansionTile(
                title=ui.texto(f"Parcelas de compras de outros meses que vencem em {R.nome_mes(self.mes, False)} "
                               f"({self.dinheiro(R.soma(p.valor for p in antigas))})", 13.5, ft.FontWeight.W_600, ROXO),
                controls=[ui.linha(p.lanc["descricao"], f"{p.cartao['nome']}, parcela {p.numero} de {p.total}",
                                   f"− {self.dinheiro(p.valor)}", inicio=ui.bolinha(p.cartao.get("cor", ROXO)),
                                   on_click=lambda _, l=p.lanc: self.form_lancamento(l)) for p in antigas]))
        return ft.Column([*linhas, *extra], spacing=22)

    DIAS_SEMANA = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]

    def nome_dia(self, iso: str) -> str:
        d = date.fromisoformat(iso)
        extenso = f"{d.day} de {R.MESES[d.month - 1]}"
        dias = R.dias_ate(iso)
        if dias == 0:
            return f"Hoje, {extenso}"
        if dias == -1:
            return f"Ontem, {extenso}"
        return f"{self.DIAS_SEMANA[d.weekday()].capitalize()}, {extenso}"

    def linha_lancamento(self, l: dict) -> ft.Container:
        c = self.cartao_de(l.get("cartao_id"))
        detalhe = R.categoria(l["categoria"])["nome"]
        if l["tipo"] == "despesa" and c:
            ps = R.parcelas_de(l, c)
            detalhe = (f"{c['nome']}, {len(ps)}x de {self.dinheiro(ps[-1].valor)} ({R.mes_curto(ps[0].competencia)} a {R.mes_curto(ps[-1].competencia)})"
                       if len(ps) > 1 else f"{c['nome']}, fatura de {R.mes_curto(ps[0].competencia)}")
        elif l["tipo"] == "despesa":
            detalhe += f", {R.nome_forma(R.forma_de(l)).lower()}"
        receita = l["tipo"] == "receita"
        pago = not receita and self.lancamento_pago(l)
        return ui.linha(
            l["descricao"], detalhe, f"{'+' if receita else '−'} {self.dinheiro(l['valor'])}",
            cor_valor=VERDE if receita else None, riscado=pago,
            inicio=ui.bolinha(VERDE) if receita else ui.check(
                pago, lambda _, l=l: self.page.run_task(self.alternar_pago, l), cor=self.cor_lancamento(l),
                tooltip="Desmarcar como pago" if pago else "Marcar como pago"),
            on_click=lambda _, l=l: self.form_lancamento(l))

    # ======================================================================
    # Cartões
    # ======================================================================
    def tela_cartoes(self) -> list[ft.Control]:
        d = self.d
        parcelas = R.todas_parcelas(d)
        ativos = [x for x in R.parcelamentos(d, parcelas) if x["ativo"]]
        topo = ft.Row([ui.titulo(f"Cartões e faturas de {R.nome_mes(self.mes, False)}"),
                       ft.OutlinedButton("Novo cartão", icon=ft.Icons.ADD_ROUNDED, on_click=lambda _: self.form_cartao())],
                      alignment=ft.MainAxisAlignment.SPACE_BETWEEN, wrap=True)
        if not d["cartoes"]:
            return [topo, ui.cartao(ui.vazio("Cadastre seus cartões para acompanhar faturas e limite."))]
        blocos = []
        for c in d["cartoes"]:
            f = R.fatura(d, c, self.mes, parcelas)
            usado, limite = R.limite_usado(d, c, parcelas), float(c["limite"])
            cor = c.get("cor", ROXO)
            botoes = []
            if f.total > 0:
                rot = "Desfazer pagamento" if f.status == "paga" else (
                    f"Pagar o restante ({self.dinheiro(f.a_pagar)})" if f.parcial else "Marcar como paga")
                cls = ft.OutlinedButton if f.status == "paga" else ft.FilledButton
                botoes.append(cls(rot, height=44, on_click=lambda _, c=c: self.page.run_task(self.alternar_fatura, c["id"], self.mes)))
            if f.a_pagar > 0:
                botoes.append(ft.OutlinedButton("Pagar um valor", height=44, on_click=lambda _, c=c: self.form_pagar_valor(c, self.mes)))
            compras = []
            for i in f.itens:
                quitada = R.parcela_quitada(d, i)
                travada = bool(f.pagamento) or i.pre_paga
                compras.append(ui.linha(
                    i.lanc["descricao"], R.data_curta(i.lanc["data"]) + (f", parcela {i.numero} de {i.total}" if i.total > 1 else ", à vista"),
                    self.dinheiro(i.valor), riscado=quitada, on_click=lambda _, l=i.lanc: self.form_lancamento(l),
                    fim=ui.check(quitada, lambda _, i=i: self.page.run_task(self.alternar_item, i.lanc["id"], i.competencia),
                                 cor=cor, desativado=travada, tooltip="Já está paga" if travada else "Marcar esta compra")))
            parcel = [ui.linha(x["lanc"]["descricao"],
                               f"{x['total']}x de {self.dinheiro(x['valor_parcela'])}, {x['pagas']} de {x['total']} pagas, termina em {R.mes_curto(x['ultima'])}",
                               self.dinheiro(x["restante"]), detalhe_valor="falta",
                               on_click=lambda _, l=x["lanc"]: self.form_lancamento(l))
                      for x in ativos if x["cartao"]["id"] == c["id"]]
            avulsos = [ui.linha("Pagamento avulso", R.data_curta(x["data"]) + "/" + x["data"][:4], self.dinheiro(x["valor"]),
                                cor_valor=VERDE, fim=ft.IconButton(ft.Icons.DELETE_OUTLINE_ROUNDED, tooltip="Apagar",
                                                                   on_click=lambda _, x=x: self.page.run_task(self.apagar_avulso, x)))
                       for x in f.avulsos]
            plastico = ft.Container(
                bgcolor=cor, margin=8, border_radius=14, padding=18,
                content=ft.Column(spacing=2, controls=[
                    ft.Row([ui.texto(c["nome"], 16, ft.FontWeight.W_700, ft.Colors.WHITE),
                            ft.IconButton(ft.Icons.EDIT_ROUNDED, icon_color=ft.Colors.WHITE, tooltip="Editar cartão",
                                          on_click=lambda _, c=c: self.form_cartao(c))],
                           alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ui.texto(f"Fatura de {R.nome_mes(self.mes, False)}", 12.5, color=ft.Colors.with_opacity(0.85, ft.Colors.WHITE)),
                    ui.numero_texto(self.dinheiro(f.total), 32, ft.FontWeight.W_600, ft.Colors.WHITE),
                    *([ft.Container(ui.texto(f"Já pago {self.dinheiro(f.pago)}, falta {self.dinheiro(f.a_pagar)}", 12.5,
                                             ft.FontWeight.W_600, ft.Colors.WHITE),
                                    bgcolor=ft.Colors.with_opacity(0.18, ft.Colors.WHITE), border_radius=99,
                                    padding=ft.Padding.symmetric(horizontal=10, vertical=3))] if f.parcial else []),
                    ui.texto(f"Fecha {R.data_curta(f.fechamento)}, vence {R.data_curta(f.vencimento)}", 12.5,
                             color=ft.Colors.with_opacity(0.9, ft.Colors.WHITE)),
                ]))
            status_tipo = {"paga": "ok", "vencida": "perigo", "fechada": "aviso"}.get(f.status, "")
            corpo = ft.Container(padding=16, content=ft.Column(spacing=12, controls=[
                ft.Row([ui.chip(NOME_STATUS[f.status], status_tipo)]),
                *([ft.ResponsiveRow([ft.Container(b, col={"xs": 12, "sm": 6}) for b in botoes], spacing=8, run_spacing=8)] if botoes else []),
                *([ui.lista(avulsos)] if avulsos else []),
                ft.Container(bgcolor=ft.Colors.with_opacity(0.08, ROXO), border_radius=14, padding=12, content=ft.ResponsiveRow([
                    ft.Column([ui.sutil("Limite", 11.5), ui.texto(self.dinheiro(limite), 14.5, ft.FontWeight.W_700)], spacing=0, col=4),
                    ft.Column([ui.sutil("Gastei", 11.5), ui.texto(self.dinheiro(usado), 14.5, ft.FontWeight.W_700)], spacing=0, col=4),
                    ft.Column([ui.sutil("Disponível", 11.5), ui.texto(self.dinheiro(limite - usado), 14.5, ft.FontWeight.W_700,
                                                                     VERMELHO if limite - usado < 0 else VERDE)], spacing=0, col=4),
                ])),
                ui.barra(usado / limite if limite else 0),
                ui.sutil(f"{round(usado / limite * 100) if limite else 0}% do limite em uso. Melhor dia de compra: dia {c['fechamento']}."),
                *([ui.texto("Parcelamentos", 14.5, ft.FontWeight.W_700), ui.lista(parcel)] if parcel else []),
                *([ft.ExpansionTile(title=ui.texto(f"Compras desta fatura ({len(compras)})", 14, ft.FontWeight.W_600, ROXO),
                                    subtitle=ui.sutil("Toque na bolinha de uma compra para marcar só ela como paga."),
                                    expanded=len(compras) <= 6 or f.parcial, controls=[ui.lista(compras)])] if compras else []),
            ]))
            blocos.append(ft.Container(col={"xs": 12, "md": 6}, border_radius=18, bgcolor=ft.Colors.SURFACE_CONTAINER_LOWEST,
                                       border=ft.Border.all(1, ui.BORDA), clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                                       content=ft.Column([plastico, corpo], spacing=0)))
        return [topo, ft.ResponsiveRow(blocos, spacing=14, run_spacing=14)]

    # ======================================================================
    # Simular
    # ======================================================================
    def tela_simular(self) -> list[ft.Control]:
        s, cartoes = self.sim, self.d["cartoes"]
        if cartoes and not any(c["id"] == s["cartao"] for c in cartoes):
            s["cartao"] = cartoes[0]["id"]
        resultado = ft.Column(spacing=12)

        def recalcular(_=None):
            resultado.controls = self.resultado_simulacao()
            resultado.update()

        def campo(nome, redesenhar=False):
            def h(e):
                v = e.control.selected[0] if isinstance(e.control, ft.SegmentedButton) else e.control.value
                s[nome] = v
                self.render() if redesenhar else recalcular()
            return h

        valor = campo_dinheiro("Valor", R.ler_valor(s["valor"]) if s["valor"] else None, on_change=campo("valor"))
        controles: list[ft.Control] = [
            ui.sutil("Veja como ficariam seu limite e seus meses antes de comprar ou pagar. Nada aqui é salvo.", 13.5),
            segmentado([("credito", "Crédito"), ("avista", "Pix/débito"), ("pagamento", "Fatura")], s["tipo"], campo("tipo", True)),
            valor,
        ]
        if s["tipo"] != "pagamento":
            data = campo_data("Data", s["data"])
            data.on_change = lambda e: (s.__setitem__("data", ler_data(e.control) or s["data"]), recalcular())
            controles.append(data)
        if s["tipo"] != "avista":
            if cartoes:
                controles.append(seletor("Cartão", [(c["id"], c["nome"]) for c in cartoes], s["cartao"], campo("cartao", True)))
            else:
                controles.append(ui.alerta("Cadastre um cartão para simular no crédito.", "aviso"))
        if s["tipo"] == "credito" and cartoes:
            controles.append(segmentado([("avista", "À vista"), ("parcelado", "Parcelado")], s["modo"], campo("modo", True)))
            if s["modo"] == "parcelado":
                controles.append(ft.TextField(label="Em quantas parcelas?", value=s["parcelas"], keyboard_type=ft.KeyboardType.NUMBER,
                                              border_radius=12, on_change=campo("parcelas")))
        if s["tipo"] == "pagamento" and cartoes:
            c = self.cartao_de(s["cartao"])
            abertas = self.faturas_em_aberto(c)
            if abertas and s["fatura"] not in [f.comp for f in abertas]:
                s["fatura"] = abertas[0].comp
            controles.append(seletor("Qual fatura", [(f.comp, f"{R.nome_mes(f.comp)} (falta {R.brl(f.a_pagar)})") for f in abertas],
                                     s["fatura"], campo("fatura")) if abertas else ui.alerta("Este cartão não tem fatura a pagar.", "info"))
        resultado.controls = self.resultado_simulacao()
        return [ui.titulo("Simular"), ft.ResponsiveRow(spacing=14, run_spacing=14, controls=[
            ui.cartao(ft.Column(controles, spacing=14, horizontal_alignment=ft.CrossAxisAlignment.STRETCH), col={"xs": 12, "md": 5}),
            ui.cartao(resultado, col={"xs": 12, "md": 7}),
        ])]

    def faturas_em_aberto(self, cartao: dict) -> list[R.Fatura]:
        parcelas = R.todas_parcelas(self.d)
        comps = sorted({p.competencia for p in parcelas if p.cartao["id"] == cartao["id"]})
        fs = [R.fatura(self.d, cartao, k, parcelas) for k in comps]
        return [f for f in fs if f.a_pagar > 0 and f.comp <= R.somar_meses(R.comp_atual(), 2)]

    def resultado_simulacao(self) -> list[ft.Control]:
        d, s = self.d, self.sim
        valor = R.ler_valor(s["valor"]) if s["valor"] else None
        if not valor or valor <= 0:
            return [ui.titulo("Resultado"), ui.vazio("Digite um valor para ver a simulação.")]
        if s["tipo"] == "avista":
            comp = s["data"][:7]
            d2 = {**d, "lancamentos": d["lancamentos"] + [{"id": "__sim", "tipo": "despesa", "descricao": "Simulação", "valor": valor,
                                                           "data": s["data"], "categoria": "outros", "forma": "pix",
                                                           "cartao_id": None, "parcelas": 1}]}
            antes, depois = R.resumo_mes(d, comp).saldo, R.resumo_mes(d2, comp).saldo
            return [ui.titulo("Resultado"), self.mes_simulado(comp, "Com a compra", [("Sobra no mês", antes, depois, False)]),
                    ui.alerta(f"Com essa compra, {R.nome_mes(comp, False)} fecharia no negativo." if depois < 0
                              else f"Ainda sobrariam {self.dinheiro(depois)} no mês.", "perigo" if depois < 0 else "ok")]
        c = self.cartao_de(s["cartao"])
        if not c:
            return [ui.titulo("Resultado"), ui.vazio("Escolha um cartão.")]
        limite = float(c["limite"])
        if s["tipo"] == "credito":
            n = max(2, min(48, int(s["parcelas"] or 2))) if s["modo"] == "parcelado" else 1
            compra = {"id": "__sim", "tipo": "despesa", "descricao": "Simulação", "valor": valor, "data": s["data"],
                      "categoria": "outros", "forma": "credito", "cartao_id": c["id"], "parcelas": n, "parcelas_pagas": 0}
            d2 = {**d, "lancamentos": d["lancamentos"] + [compra]}
            ps = R.parcelas_de(compra, c)
            resumo = (f"{n}x de {self.dinheiro(ps[-1].valor)}, da fatura de {R.mes_curto(ps[0].competencia)} até {R.mes_curto(ps[-1].competencia)}."
                      if n > 1 else f"{self.dinheiro(valor)} à vista, na fatura de {R.mes_curto(ps[0].competencia)}.")
            meses, k = [], R.comp_atual()
            while k <= R.somar_meses(ps[-1].competencia, 1) and len(meses) < 13:
                meses.append(k)
                k = R.somar_meses(k, 1)
            rotulo = "Com a compra"
        else:
            if not s["fatura"]:
                return [ui.titulo("Resultado"), ui.vazio("Este cartão não tem fatura a pagar.")]
            d2 = {**d, "pagamentos_fatura": d.get("pagamentos_fatura", []) + [{"id": "__sim", "cartao_id": c["id"],
                                                                                "competencia": s["fatura"], "valor": valor}]}
            f = R.fatura(d, c, s["fatura"])
            resumo = (f"Paga a fatura de {R.mes_curto(s['fatura'])} inteira (faltavam {self.dinheiro(f.a_pagar)})." if valor >= f.a_pagar
                      else f"Abate {self.dinheiro(valor)} da fatura de {R.mes_curto(s['fatura'])}. Ainda faltariam {self.dinheiro(f.a_pagar - valor)}.")
            meses = [R.somar_meses(R.comp_atual(), i) for i in range(3)]
            rotulo = "Pagando"
        p1, p2 = R.todas_parcelas(d), R.todas_parcelas(d2)
        livre_a, livre_d = limite - R.limite_usado(d, c, p1), limite - R.limite_usado(d2, c, p2)
        controles = [ui.titulo("Resultado"), ui.texto(resumo, 14, ft.FontWeight.W_600),
                     ft.Container(bgcolor=ft.Colors.with_opacity(0.1, ROXO), border_radius=14, padding=14,
                                  content=ft.Column([ui.texto(f"Limite livre no {c['nome']}", 14, ft.FontWeight.W_700, ROXO),
                                                     ui.tabela_comparacao(rotulo, [("Agora", livre_a, livre_d, False)], self.dinheiro)],
                                                    spacing=8))]
        if livre_d < 0:
            controles.append(ui.alerta(f"Passaria do limite em {self.dinheiro(-livre_d)}. O cartão pode recusar a compra.", "perigo"))
        controles.append(ui.texto("Mês a mês", 14.5, ft.FontWeight.W_700))
        controles.append(ft.ResponsiveRow(spacing=10, run_spacing=10, controls=[ft.Container(self.mes_simulado(comp, rotulo, [
            ("Fatura a pagar", R.fatura(d, c, comp, p1).a_pagar, R.fatura(d2, c, comp, p2).a_pagar, True),
            ("Limite livre", limite - R.limite_usado_em(d, c, comp, p1), limite - R.limite_usado_em(d2, c, comp, p2), False),
            ("Sobra no mês", R.resumo_mes(d, comp).saldo, R.resumo_mes(d2, comp).saldo, False),
        ]), col={"xs": 12, "lg": 6}) for comp in meses]))
        controles.append(ui.sutil("“Limite livre” de cada mês considera que as faturas anteriores foram pagas em dia.", 11.5))
        return controles

    def mes_simulado(self, comp: str, rotulo: str, linhas_) -> ft.Container:
        return ft.Container(border=ft.Border.all(1, ui.BORDA), border_radius=14, padding=12, content=ft.Column([
            ui.texto(R.nome_mes(comp).capitalize(), 14, ft.FontWeight.W_700, ROXO),
            ui.tabela_comparacao(rotulo, linhas_, self.dinheiro)], spacing=8))

    # ======================================================================
    # Entradas
    # ======================================================================
    def tela_entradas(self) -> list[ft.Control]:
        d = self.d
        r = R.resumo_mes(d, self.mes)
        lista = sorted(r.receitas, key=lambda l: l["data"], reverse=True)
        por_cat: dict[str, float] = {}
        for l in lista:
            por_cat[l["categoria"]] = R.soma([por_cat.get(l["categoria"]), l["valor"]])
        meses = [R.somar_meses(self.mes, i - 5) for i in range(6)]
        totais = [R.soma(l["valor"] for l in d["lancamentos"] if l["tipo"] == "receita" and l["data"][:7] == k) for k in meses]
        anterior = totais[4]
        comparacao = "Sem entradas no mês anterior para comparar." if not anterior else \
            f"{'+' if r.total_receitas >= anterior else ''}{round((r.total_receitas - anterior) / anterior * 100)}% em relação a {R.nome_mes(meses[4], False)}"
        maior = max(totais + [1])
        colunas = ft.Row(alignment=ft.MainAxisAlignment.SPACE_AROUND, vertical_alignment=ft.CrossAxisAlignment.END, height=150,
                         controls=[ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.END, spacing=4,
                                             controls=[ui.sutil("•••" if self.ocultar else f"{t:,.0f}".replace(",", "."), 10.5),
                                                       ft.Container(width=26, height=max(4, 100 * t / maior), border_radius=8,
                                                                    bgcolor=ROXO if k == self.mes else LILAS),
                                                       ui.texto(R.MESES[int(k[5:]) - 1][:3].capitalize(), 11.5,
                                                                ft.FontWeight.W_700 if k == self.mes else None,
                                                                ROXO if k == self.mes else TEXTO_2)])
                                   for k, t in zip(meses, totais)])
        return [
            ft.Row([ui.titulo(f"Entradas de {R.nome_mes(self.mes, False)}"),
                    ft.FilledButton("Nova entrada", icon=ft.Icons.ADD_ROUNDED, on_click=lambda _: self.form_lancamento(None, "receita"))],
                   alignment=ft.MainAxisAlignment.SPACE_BETWEEN, wrap=True),
            ui.destaque(f"Total que entrou em {R.nome_mes(self.mes, False)}", self.dinheiro(r.total_receitas), comparacao),
            ft.ResponsiveRow(spacing=10, run_spacing=10, controls=[
                ui.numero("Já saiu do que entrou", self.dinheiro(r.total_receitas - r.saldo), col=6),
                ui.numero("Sobra prevista", self.dinheiro(r.saldo), VERMELHO if r.saldo < 0 else VERDE, col=6)]),
            ft.ResponsiveRow(spacing=14, run_spacing=14, controls=[
                ui.secao("Lista", [ui.lista([ui.linha(l["descricao"], f"{R.categoria(l['categoria'])['nome']}, dia {R.data_curta(l['data'])}",
                                                      f"+ {self.dinheiro(l['valor'])}", cor_valor=VERDE, inicio=ui.bolinha(VERDE),
                                                      on_click=lambda _, l=l: self.form_lancamento(l)) for l in lista])
                                   if lista else ui.vazio("Nenhuma entrada neste mês.")], col={"xs": 12, "md": 6}),
                ui.secao("De onde veio", [
                    *[ft.Column([ft.Row([ui.texto(R.categoria(k)["nome"], 13.5), ui.texto(self.dinheiro(v), 13.5, ft.FontWeight.W_700)],
                                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                 ui.barra(v / r.total_receitas if r.total_receitas else 0, VERDE)], spacing=4)
                      for k, v in sorted(por_cat.items(), key=lambda x: -x[1])],
                    ui.texto("Últimos 6 meses", 14, ft.FontWeight.W_700), colunas], col={"xs": 12, "md": 6}),
            ]),
        ]

    # ======================================================================
    # Metas
    # ======================================================================
    def tela_metas(self) -> list[ft.Control]:
        d = self.d
        total = R.soma(R.guardado_na_meta(d, m["id"]) for m in d["metas"])
        topo = ft.Row([ui.titulo("Metas para juntar dinheiro"),
                       ft.FilledButton("Nova meta", icon=ft.Icons.ADD_ROUNDED, on_click=lambda _: self.form_meta())],
                      alignment=ft.MainAxisAlignment.SPACE_BETWEEN, wrap=True)
        if not d["metas"]:
            return [topo, ui.cartao(ui.vazio("Crie uma meta (reserva, viagem, um celular novo…) e o app calcula quanto guardar por mês."))]
        cards = []
        for m in d["metas"]:
            g, alvo, cor = R.guardado_na_meta(d, m["id"]), float(m["alvo"]), m.get("cor", ROXO)
            falta = max(0, alvo - g)
            plano = ""
            if falta == 0:
                plano = "Meta alcançada!"
            elif m.get("prazo"):
                n = R.meses_entre(R.comp_atual(), m["prazo"]) + 1
                plano = (f"Guarde {self.dinheiro(falta / n)} por mês para chegar até {R.mes_curto(m['prazo'])}." if n > 0
                         else f"O prazo ({R.mes_curto(m['prazo'])}) já passou. Faltam {self.dinheiro(falta)}.")
            movs = sorted((x for x in d["metas_movimentos"] if x["meta_id"] == m["id"]), key=lambda x: x["data"], reverse=True)
            cards.append(ui.cartao(ft.Column(spacing=10, controls=[
                ft.Row([ft.Column([ui.titulo(m["nome"], 18),
                                   ui.sutil(f"até {R.mes_curto(m['prazo'])}" if m.get("prazo") else "sem prazo")], spacing=0, expand=True),
                        ft.IconButton(ft.Icons.EDIT_ROUNDED, tooltip="Editar", on_click=lambda _, m=m: self.form_meta(m))]),
                ft.Row([ui.numero_texto(self.dinheiro(g), 30), ui.sutil(f"de {self.dinheiro(alvo)}", 13)],
                       vertical_alignment=ft.CrossAxisAlignment.END),
                ui.barra(g / alvo if alvo else 0, cor),
                ft.Row([ui.sutil(f"{round(g / alvo * 100) if alvo else 0}%"), ui.sutil(f"faltam {self.dinheiro(falta)}" if falta else "completa")],
                       alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                *([ft.Container(ui.texto(plano, 13, ft.FontWeight.W_600, ROXO), bgcolor=ft.Colors.with_opacity(0.1, ROXO),
                                border_radius=12, padding=10)] if plano else []),
                ft.Row([ft.FilledButton("Guardar", icon=ft.Icons.ADD_ROUNDED, expand=True, on_click=lambda _, m=m: self.form_movimento(m, 1)),
                        ft.OutlinedButton("Retirar", expand=True, disabled=g <= 0, on_click=lambda _, m=m: self.form_movimento(m, -1))]),
                *([ft.ExpansionTile(title=ui.texto(f"Histórico ({len(movs)})", 13.5, ft.FontWeight.W_600, ROXO), controls=[ui.lista([
                    ui.linha("Guardou" if x["valor"] > 0 else "Retirou", R.data_curta(x["data"]) + "/" + x["data"][:4],
                             f"{'+' if x['valor'] > 0 else '−'} {self.dinheiro(abs(x['valor']))}", cor_valor=VERDE if x["valor"] > 0 else None,
                             fim=ft.IconButton(ft.Icons.DELETE_OUTLINE_ROUNDED, tooltip="Apagar",
                                               on_click=lambda _, x=x: self.page.run_task(self.apagar_movimento, x)))
                    for x in movs])])] if movs else []),
            ]), col={"xs": 12, "md": 6}, borda_topo=cor))
        return [topo, ft.ResponsiveRow([ui.numero("Total guardado", self.dinheiro(total), ROXO, col=6),
                                        ui.numero(f"Guardado em {R.nome_mes(self.mes, False)}", self.dinheiro(R.guardado_no_mes(d, self.mes)), col=6)],
                                       spacing=10), ft.ResponsiveRow(cards, spacing=14, run_spacing=14)]

    # ======================================================================
    # Ações (pagar, marcar, apagar)
    # ======================================================================
    async def alternar_fatura(self, cartao_id: str, comp: str) -> None:
        c = self.cartao_de(cartao_id)
        f = R.fatura(self.d, c, comp)
        if f.status == "paga":
            if not await self.confirmar("Desfazer o pagamento desta fatura?",
                                        "As compras marcadas e os valores avulsos pagos voltam a ficar pendentes."):
                return
            itens = [x for x in (R.pagamento_item(self.d, i) for i in f.itens) if x]

            async def desfazer():
                if f.pagamento:
                    await self.banco.remover("faturas_pagas", f.pagamento["id"])
                for x in itens:
                    await self.banco.remover("itens_pagos", x["id"])
                for x in f.avulsos:
                    await self.banco.remover("pagamentos_fatura", x["id"])
            await self.executar(desfazer, "Pagamento desfeito")
            return
        await self.executar(lambda: self.banco.inserir("faturas_pagas", {"cartao_id": cartao_id, "competencia": comp, "pago_em": R.hoje()}),
                            "Restante da fatura pago" if f.parcial else "Fatura marcada como paga")

    async def alternar_item(self, lanc_id: str, comp: str) -> None:
        x = next((x for x in self.d["itens_pagos"] if x["lancamento_id"] == lanc_id and x["competencia"] == comp), None)
        await self.executar((lambda: self.banco.remover("itens_pagos", x["id"])) if x else
                            (lambda: self.banco.inserir("itens_pagos", {"lancamento_id": lanc_id, "competencia": comp, "pago_em": R.hoje()})),
                            "Compra voltou para pendente" if x else "Compra marcada como paga")

    async def alternar_pago(self, l: dict) -> None:
        c = self.cartao_de(l.get("cartao_id"))
        pago = self.lancamento_pago(l)
        if not c:
            await self.executar(lambda: self.banco.atualizar("lancamentos", l["id"], {"pago": not pago}),
                                "Desmarcado" if pago else "Marcado como pago")
            return
        ps = R.parcelas_de(l, c)

        async def fn():
            for p in ps:
                x = R.pagamento_item(self.d, p)
                if pago and x:
                    await self.banco.remover("itens_pagos", x["id"])
                elif not pago and not R.parcela_quitada(self.d, p):
                    await self.banco.inserir("itens_pagos", {"lancamento_id": l["id"], "competencia": p.competencia, "pago_em": R.hoje()})
        await self.executar(fn, "Compra voltou para pendente" if pago else "Compra marcada como paga")

    async def alternar_conta(self, conta: dict, comp: str) -> None:
        pago = next((p for p in self.d["contas_pagas"] if p["conta_id"] == conta["id"] and p["competencia"] == comp), None)

        async def fn():
            if pago:
                if pago.get("lancamento_id") and any(l["id"] == pago["lancamento_id"] for l in self.d["lancamentos"]):
                    await self.banco.remover("lancamentos", pago["lancamento_id"])
                else:
                    await self.banco.remover("contas_pagas", pago["id"])
                return
            data = R.hoje() if R.comp_atual() == comp else R.data_no_mes(comp, conta["dia"])
            lanc = await self.banco.inserir("lancamentos", {"tipo": "despesa", "descricao": conta["descricao"], "valor": float(conta["valor"]),
                                                            "data": data, "categoria": conta["categoria"], "forma": "pix",
                                                            "cartao_id": None, "parcelas": 1})
            await self.banco.inserir("contas_pagas", {"conta_id": conta["id"], "competencia": comp, "lancamento_id": lanc["id"]})
        await self.executar(fn, "Pagamento desfeito" if pago else "Conta marcada como paga")

    async def apagar_avulso(self, x: dict) -> None:
        if await self.confirmar("Apagar este pagamento avulso?"):
            await self.executar(lambda: self.banco.remover("pagamentos_fatura", x["id"]), "Pagamento apagado")

    async def apagar_movimento(self, x: dict) -> None:
        if await self.confirmar("Apagar este registro da meta?"):
            await self.executar(lambda: self.banco.remover("metas_movimentos", x["id"]), "Registro apagado")

    # ======================================================================
    # Diálogos e formulários
    # ======================================================================
    async def confirmar(self, pergunta: str, detalhe: str = "") -> bool:
        import asyncio
        resposta = asyncio.get_running_loop().create_future()

        def responder(v):
            def h(_):
                self.page.pop_dialog()
                if not resposta.done():
                    resposta.set_result(v)
            return h

        self.page.show_dialog(ft.AlertDialog(
            modal=True, title=ft.Text(pergunta, size=18, weight=ft.FontWeight.W_700),
            content=ui.sutil(detalhe, 14) if detalhe else None,
            actions=[ft.TextButton("Cancelar", on_click=responder(False)),
                     ft.FilledButton("Confirmar", on_click=responder(True))]))
        return await resposta

    def formulario(self, titulo_: str, campos: list[ft.Control], salvar, excluir=None, rotulo_salvar: str = "Salvar") -> None:
        """Janela de formulário com proteção contra salvar duas vezes."""
        botao = ft.FilledButton(rotulo_salvar)
        janela: ft.AlertDialog | None = None

        def fechar():
            # Fecha ESTA janela (o aviso "salvo" também entra na pilha, então pop_dialog fecharia o aviso).
            janela.open = False
            janela.update()

        async def ao_salvar(_):
            if botao.disabled:
                return
            botao.disabled, botao.content = True, "Salvando…"
            botao.update()
            self.avisos_adiados = []
            try:
                ok = await salvar()
                adiados, self.avisos_adiados = self.avisos_adiados, None
                if ok:
                    fechar()
                    for m in adiados:
                        self.aviso(m)
            finally:
                self.avisos_adiados = None
                if montado(botao):
                    botao.disabled, botao.content = False, rotulo_salvar
                    botao.update()

        async def ao_excluir(_):
            fechar()
            await excluir()

        botao.on_click = ao_salvar
        janela = ft.AlertDialog(
            title=ft.Text(titulo_, size=19, weight=ft.FontWeight.W_700, font_family=ui.FONTE_TITULO), scrollable=True,
            inset_padding=ft.Padding.symmetric(horizontal=16, vertical=24),
            content=ft.Container(ft.Column(campos, spacing=14, tight=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH),
                                 width=self.largura_janela()),
            actions=[*([ft.TextButton("Excluir", style=ft.ButtonStyle(color=VERMELHO), on_click=ao_excluir)] if excluir else []),
                     ft.TextButton("Cancelar", on_click=lambda _: fechar()), botao],
            actions_alignment=ft.MainAxisAlignment.END)
        self.page.show_dialog(janela)

    def form_lancamento(self, l: dict | None = None, tipo_padrao: str = "despesa") -> None:
        d = self.d
        estado = {
            "tipo": (l or {}).get("tipo", tipo_padrao),
            "forma": R.forma_de(l) if l and l["tipo"] == "despesa" else "pix",
            "modo": "parcelado" if l and int(l.get("parcelas") or 1) > 1 else "avista",
        }
        valor = campo_dinheiro("Valor total" if l and int(l.get("parcelas") or 1) > 1 else "Valor", (l or {}).get("valor"),
                               autofocus=l is None, on_change=lambda _: atualizar())
        descricao = ft.TextField(label="Descrição", value=(l or {}).get("descricao", ""), hint_text="Ex.: Mercado do mês",
                                 border_radius=12, max_length=80)
        data = campo_data("Data", (l or {}).get("data") or (R.hoje() if self.mes == R.comp_atual() else f"{self.mes}-01"))
        cats = lambda t: [(c["id"], c["nome"]) for c in R.CATEGORIAS[t]]  # noqa: E731
        categoria = seletor("Categoria", cats(estado["tipo"]), (l or {}).get("categoria") or R.CATEGORIAS[estado["tipo"]][0]["id"])
        cartoes = d["cartoes"]
        cartao = seletor("Cartão", [(c["id"], c["nome"]) for c in cartoes],
                         (l or {}).get("cartao_id") or (cartoes[0]["id"] if cartoes else None), on_select=lambda _: atualizar())
        parcelas = ft.TextField(label="Em quantas parcelas?", value=str((l or {}).get("parcelas") or 2), border_radius=12,
                                keyboard_type=ft.KeyboardType.NUMBER, on_change=lambda _: atualizar(), expand=True)
        ja_pagas = ft.TextField(label="Já paguei quantas?", value=str((l or {}).get("parcelas_pagas") or 0), border_radius=12,
                                keyboard_type=ft.KeyboardType.NUMBER, on_change=lambda _: atualizar(), expand=True)
        resumo = ft.Column(spacing=4)
        so_despesa = ft.Column(spacing=10, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        so_credito = ft.Container(bgcolor=ft.Colors.with_opacity(0.08, ROXO), border_radius=14, padding=12)

        def mudar(chave):
            def h(e):
                estado[chave] = e.control.selected[0]
                if chave == "tipo":
                    categoria.options = [ft.DropdownOption(key=k, text=t) for k, t in cats(estado["tipo"])]
                    categoria.value = R.CATEGORIAS[estado["tipo"]][0]["id"]
                atualizar()
            return h

        def atualizar():
            despesa = estado["tipo"] == "despesa"
            credito = despesa and estado["forma"] == "credito"
            parcelado = estado["modo"] == "parcelado"
            so_despesa.visible, so_credito.visible = despesa, credito
            linha_parcelas.visible = parcelado
            resumo.controls = self.resumo_compra(cartao.value, R.ler_valor(valor.value or ""), ler_data(data) or R.hoje(),
                                                 int(parcelas.value or 2) if parcelado else 1,
                                                 int(ja_pagas.value or 0) if parcelado else 0, (l or {}).get("id"))
            if montado(so_despesa):
                self.page.update()

        linha_parcelas = ft.Row([parcelas, ja_pagas], spacing=10)
        so_credito.content = ft.Column(spacing=10, horizontal_alignment=ft.CrossAxisAlignment.STRETCH, controls=[
            cartao, segmentado([("avista", "À vista"), ("parcelado", "Parcelado")], estado["modo"], mudar("modo")),
            linha_parcelas, resumo]) if cartoes else ui.alerta("Cadastre um cartão para lançar no crédito.", "aviso")
        so_despesa.controls = [ui.sutil("Como pagou?", 13), segmentado([(f["id"], f["nome"]) for f in R.FORMAS], estado["forma"], mudar("forma"))]
        atualizar()

        async def salvar() -> bool:
            v = R.ler_valor(valor.value or "")
            dt = ler_data(data)
            if not v or v <= 0:
                self.aviso("Informe um valor maior que zero.", True)
                return False
            if not dt:
                self.aviso("Data inválida. Use dd/mm/aaaa.", True)
                return False
            if not descricao.value.strip():
                self.aviso("Escreva uma descrição.", True)
                return False
            credito = estado["tipo"] == "despesa" and estado["forma"] == "credito"
            if credito and not cartao.value:
                self.aviso("Cadastre um cartão para lançar no crédito.", True)
                return False
            parcelado = credito and estado["modo"] == "parcelado"
            n = max(2, min(48, int(parcelas.value or 2))) if parcelado else 1
            obj = {"tipo": estado["tipo"], "valor": v, "descricao": descricao.value.strip(), "data": dt,
                   "categoria": categoria.value, "forma": estado["forma"] if estado["tipo"] == "despesa" else None,
                   "cartao_id": cartao.value if credito else None, "parcelas": n,
                   "parcelas_pagas": max(0, min(n - 1, int(ja_pagas.value or 0))) if parcelado else 0}
            if l:
                return await self.executar(lambda: self.banco.atualizar("lancamentos", l["id"], obj), "Lançamento salvo")
            return await self.executar(lambda: self.banco.inserir("lancamentos", obj), "Lançamento salvo")

        async def excluir():
            aviso = f"Excluir “{l['descricao']}” e todas as {l['parcelas']} parcelas?" if int(l.get("parcelas") or 1) > 1 else "Excluir este lançamento?"
            if await self.confirmar(aviso):
                await self.executar(lambda: self.banco.remover("lancamentos", l["id"]), "Lançamento excluído")

        self.formulario("Editar lançamento" if l else ("Nova entrada" if tipo_padrao == "receita" else "Novo lançamento"), [
            segmentado([("despesa", "Gasto"), ("receita", "Entrada")], estado["tipo"], mudar("tipo")),
            valor, descricao, data, categoria, so_despesa, so_credito,
        ], salvar, excluir if l else None)

    def resumo_compra(self, cartao_id, valor, data_iso, n, ja_pagas, editando_id) -> list[ft.Control]:
        c = self.cartao_de(cartao_id)
        if not c:
            return []
        outras = [p for p in R.todas_parcelas(self.d) if p.lanc["id"] != editando_id]
        disponivel = float(c["limite"]) - R.limite_usado(self.d, c, outras)
        linhas = []
        primeira = R.comp_primeira_parcela(data_iso, c)
        if valor:
            ps = R.parcelas_de({"valor": valor, "parcelas": n, "data": data_iso, "parcelas_pagas": ja_pagas}, c)
            linhas.append(ui.texto(f"{n}x de {R.brl(ps[-1].valor)}" if n > 1 else f"{R.brl(valor)} à vista", 16, ft.FontWeight.W_800, ROXO))
            restante = R.soma(p.valor for p in ps if not p.pre_paga)
        else:
            restante = 0
        linhas.append(ui.sutil(
            f"1ª parcela na fatura de {R.mes_curto(primeira)}. Termina de pagar em {R.mes_curto(R.somar_meses(primeira, n - 1))}."
            if n > 1 else f"Entra na fatura de {R.mes_curto(primeira)} (vence {R.data_curta(R.data_no_mes(primeira, c['vencimento']))}).", 13))
        if ja_pagas and valor:
            linhas.append(ui.sutil(f"{ja_pagas} já paga(s): faltam {n - ja_pagas} parcelas ({R.brl(restante)}).", 13))
        linhas.append(ui.sutil(f"Limite disponível no {c['nome']}: {R.brl(disponivel)}", 13))
        if valor:
            depois = disponivel - restante
            linhas.append(ui.texto(f"Depois desta compra: {R.brl(depois)}" + (" (passa do limite)" if depois < 0 else ""), 13,
                                   ft.FontWeight.W_700, VERMELHO if depois < 0 else None))
        return linhas

    def seletor_cor(self, atual: str) -> tuple[ft.Row, dict]:
        escolha = {"cor": atual}
        bolas: list[ft.Container] = []

        def escolher(cor):
            def h(_):
                escolha["cor"] = cor
                for b in bolas:
                    b.border = ft.Border.all(3, ft.Colors.ON_SURFACE if b.data == cor else ft.Colors.TRANSPARENT)
                linha_.update()
            return h

        for cor in ui.CORES_ITENS:
            bolas.append(ft.Container(width=34, height=34, border_radius=34, bgcolor=cor, data=cor, on_click=escolher(cor),
                                      border=ft.Border.all(3, ft.Colors.ON_SURFACE if cor == atual else ft.Colors.TRANSPARENT)))
        linha_ = ft.Row(bolas, wrap=True, spacing=8)
        return linha_, escolha

    def form_cartao(self, c: dict | None = None) -> None:
        nome = ft.TextField(label="Nome do cartão", value=(c or {}).get("nome", ""), hint_text="Ex.: Nubank", border_radius=12, autofocus=c is None)
        limite = campo_dinheiro("Limite total", (c or {}).get("limite"))
        fech = ft.TextField(label="Dia que fecha", value=str((c or {}).get("fechamento", "")), keyboard_type=ft.KeyboardType.NUMBER,
                            border_radius=12, expand=True)
        venc = ft.TextField(label="Dia que vence", value=str((c or {}).get("vencimento", "")), keyboard_type=ft.KeyboardType.NUMBER,
                            border_radius=12, expand=True)
        cores, escolha = self.seletor_cor((c or {}).get("cor") or ui.CORES_ITENS[len(self.d["cartoes"]) % len(ui.CORES_ITENS)])

        async def salvar() -> bool:
            try:
                fe, ve = int(fech.value), int(venc.value)
                assert 1 <= fe <= 31 and 1 <= ve <= 31
            except (ValueError, AssertionError):
                self.aviso("Os dias de fechamento e vencimento vão de 1 a 31.", True)
                return False
            lim = R.ler_valor(limite.value or "0") or 0
            if not nome.value.strip():
                self.aviso("Dê um nome ao cartão.", True)
                return False
            obj = {"nome": nome.value.strip(), "limite": lim, "fechamento": fe, "vencimento": ve, "cor": escolha["cor"]}
            if c:
                return await self.executar(lambda: self.banco.atualizar("cartoes", c["id"], obj), "Cartão salvo")
            return await self.executar(lambda: self.banco.inserir("cartoes", obj), "Cartão salvo")

        async def excluir():
            if await self.confirmar("Excluir este cartão?", "Todas as compras e faturas dele também serão apagadas."):
                await self.executar(lambda: self.banco.remover("cartoes", c["id"]), "Cartão excluído")

        self.formulario("Editar cartão" if c else "Novo cartão", [
            nome, limite, ft.Row([fech, venc], spacing=10), ui.sutil("Cor", 13), cores,
            ui.sutil("O dia de fechamento e o de vencimento aparecem no app do banco ou na fatura.", 12.5),
        ], salvar, excluir if c else None)

    def form_meta(self, m: dict | None = None) -> None:
        nome = ft.TextField(label="Para que você quer juntar?", value=(m or {}).get("nome", ""), border_radius=12,
                            hint_text="Ex.: Viagem, reserva de emergência", autofocus=m is None)
        alvo = campo_dinheiro("Quanto quer juntar", (m or {}).get("alvo"))
        prazo = ft.TextField(label="Até quando (mm/aaaa, opcional)", border_radius=12,
                             value=f"{m['prazo'][5:7]}/{m['prazo'][:4]}" if m and m.get("prazo") else "")
        cores, escolha = self.seletor_cor((m or {}).get("cor") or ui.CORES_ITENS[len(self.d["metas"]) % len(ui.CORES_ITENS)])

        async def salvar() -> bool:
            v = R.ler_valor(alvo.value or "")
            if not nome.value.strip() or not v:
                self.aviso("Preencha o nome e quanto quer juntar.", True)
                return False
            p = None
            if prazo.value.strip():
                try:
                    mm, aa = prazo.value.strip().split("/")
                    p = f"{int(aa):04d}-{int(mm):02d}"
                    assert 1 <= int(mm) <= 12
                except (ValueError, AssertionError):
                    self.aviso("Prazo inválido. Use mm/aaaa, por exemplo 06/2027.", True)
                    return False
            obj = {"nome": nome.value.strip(), "alvo": v, "prazo": p, "cor": escolha["cor"]}
            if m:
                return await self.executar(lambda: self.banco.atualizar("metas", m["id"], obj), "Meta salva")
            return await self.executar(lambda: self.banco.inserir("metas", obj), "Meta salva")

        async def excluir():
            if await self.confirmar("Excluir esta meta e todo o histórico dela?"):
                await self.executar(lambda: self.banco.remover("metas", m["id"]), "Meta excluída")

        self.formulario("Editar meta" if m else "Nova meta", [nome, alvo, prazo, ui.sutil("Cor", 13), cores,
                                                              ui.sutil("Com um prazo, o app mostra quanto guardar por mês.", 12.5)],
                        salvar, excluir if m else None)

    def form_movimento(self, m: dict, sinal: int) -> None:
        guardado = R.guardado_na_meta(self.d, m["id"])
        valor = campo_dinheiro("Valor", autofocus=True)
        data = campo_data("Data", R.hoje())

        async def salvar() -> bool:
            v = R.ler_valor(valor.value or "")
            dt = ler_data(data)
            if not v or v <= 0 or not dt:
                self.aviso("Informe o valor e a data (dd/mm/aaaa).", True)
                return False
            if sinal < 0 and v > guardado:
                self.aviso("Não dá para retirar mais do que está guardado.", True)
                return False
            return await self.executar(lambda: self.banco.inserir("metas_movimentos", {"meta_id": m["id"], "valor": sinal * v, "data": dt}),
                                       "Valor guardado" if sinal > 0 else "Valor retirado")

        self.formulario(f"{'Guardar em' if sinal > 0 else 'Retirar de'} “{m['nome']}”",
                        [ui.sutil(f"Guardado até agora: {R.brl(guardado)}", 13.5), valor, data], salvar,
                        rotulo_salvar="Guardar" if sinal > 0 else "Retirar")

    def form_pagar_valor(self, c: dict, comp: str) -> None:
        f = R.fatura(self.d, c, comp)
        valor = campo_dinheiro("Quanto você pagou", autofocus=True)
        data = campo_data("Quando", R.hoje())

        async def salvar() -> bool:
            v = R.ler_valor(valor.value or "")
            dt = ler_data(data)
            if not v or v <= 0 or not dt:
                self.aviso("Informe o valor e a data (dd/mm/aaaa).", True)
                return False
            if v > f.a_pagar:
                self.aviso(f"O valor é maior do que falta pagar ({R.brl(f.a_pagar)}).", True)
                return False
            return await self.executar(lambda: self.banco.inserir("pagamentos_fatura", {"cartao_id": c["id"], "competencia": comp,
                                                                                         "valor": v, "data": dt}), "Pagamento registrado")

        self.formulario("Pagar um valor da fatura", [
            ui.sutil(f"Fatura {c['nome']} de {R.nome_mes(comp, False)}: falta {R.brl(f.a_pagar)}.", 14), valor, data,
            ui.sutil("O valor abate o que falta da fatura e libera o mesmo valor no limite do cartão.", 12.5),
        ], salvar, rotulo_salvar="Registrar pagamento")

    async def dialogo_seguranca(self) -> None:
        sit = await biometria.situacao(self.page)

        def alternar(e):
            self.prefs.set("trava", bool(e.control.value))
            self.aviso("Trava ligada" if e.control.value else "Trava desligada")

        self.page.show_dialog(ft.AlertDialog(
            title=ft.Text("Segurança", size=19, weight=ft.FontWeight.W_800),
            content=ft.Container(width=self.largura_janela(), content=ft.Column(tight=True, spacing=14, controls=[
                ft.Switch(label="Pedir biometria ao abrir o app", value=bool(self.prefs.get("trava", True)), on_change=alternar,
                          active_color=ROXO),
                ui.alerta(f"{sit.nome}: disponível neste aparelho." if sit.disponivel else
                          f"{sit.nome}: {sit.motivo} Sem biometria, a trava pede a sua senha.", "ok" if sit.disponivel else "aviso"),
                ui.sutil("A biometria é conferida pelo próprio aparelho. O app nunca vê, recebe ou guarda seu rosto, "
                         "sua digital ou qualquer foto: ele só recebe a resposta “é a dona” ou “não é”.", 13),
                ui.sutil("A verificação em duas etapas (código do app autenticador) é ligada pelo site, no escudo do topo.", 12.5),
            ])),
            actions=[ft.FilledButton("Fechar", on_click=lambda _: self.page.pop_dialog())]))


async def main(page: ft.Page) -> None:
    await App(page).iniciar()
