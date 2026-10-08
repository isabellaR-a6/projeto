"""Regras financeiras: datas, faturas, parcelas, limites e resumo do mês.

Tradução fiel de site/js/finance.js (o site), para os dois apps darem os mesmos valores.
"Competência" é o mês no formato AAAA-MM. A fatura de um cartão é identificada pelo mês em que VENCE.
Os registros (`d`) são os mesmos dicionários que vêm do Supabase: d["cartoes"], d["lancamentos"], ...
"""
from __future__ import annotations

import calendar
import math
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

CATEGORIAS = {
    "despesa": [
        {"id": "mercado", "nome": "Mercado"},
        {"id": "alimentacao", "nome": "Restaurante e delivery"},
        {"id": "transporte", "nome": "Transporte"},
        {"id": "casa", "nome": "Casa e aluguel"},
        {"id": "contas", "nome": "Luz, água e internet"},
        {"id": "saude", "nome": "Saúde"},
        {"id": "educacao", "nome": "Educação"},
        {"id": "lazer", "nome": "Lazer"},
        {"id": "compras", "nome": "Compras"},
        {"id": "assinaturas", "nome": "Assinaturas"},
        {"id": "beleza", "nome": "Beleza e cuidados"},
        {"id": "pets", "nome": "Pets"},
        {"id": "outros", "nome": "Outros"},
    ],
    "receita": [
        {"id": "salario", "nome": "Salário"},
        {"id": "extra", "nome": "Renda extra"},
        {"id": "investimentos", "nome": "Investimentos"},
        {"id": "outras_receitas", "nome": "Outras entradas"},
    ],
}
_CATEGORIA_POR_ID = {c["id"]: c for c in CATEGORIAS["despesa"] + CATEGORIAS["receita"]}


def categoria(cid: str) -> dict:
    return _CATEGORIA_POR_ID.get(cid, {"id": cid, "nome": cid})


FORMAS = [
    {"id": "pix", "nome": "Pix"},
    {"id": "debito", "nome": "Débito"},
    {"id": "dinheiro", "nome": "Dinheiro"},
    {"id": "credito", "nome": "Crédito"},
]


def nome_forma(fid: str | None) -> str:
    return next((f["nome"] for f in FORMAS if f["id"] == fid), "")


def forma_de(l: dict) -> str | None:
    """Lançamentos antigos não tinham "forma": deduz pelo cartão."""
    if l.get("tipo") != "despesa":
        return None
    return l.get("forma") or ("credito" if l.get("cartao_id") else "pix")


MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]

# ---------- Datas (texto AAAA-MM-DD / AAAA-MM, como no banco) ----------
# Horário de Brasília (o Brasil não tem horário de verão desde 2019).
_BRASILIA = timezone(timedelta(hours=-3))


def hoje() -> str:
    return datetime.now(_BRASILIA).strftime("%Y-%m-%d")


def comp_de(ano: int, mes: int) -> str:
    """Aceita mês fora de 1..12 (13 = janeiro do ano seguinte), como o Date do JS."""
    ano += (mes - 1) // 12
    mes = (mes - 1) % 12 + 1
    return f"{ano:04d}-{mes:02d}"


def _am(comp: str) -> tuple[int, int]:
    a, m = comp[:7].split("-")
    return int(a), int(m)


def somar_meses(comp: str, n: int) -> str:
    a, m = _am(comp)
    return comp_de(a, m + n)


def data_no_mes(comp: str, dia: int) -> str:
    """Dia "dia" dentro do mês, ajustando 31 → último dia (ex.: 28/02)."""
    a, m = _am(comp)
    ultimo = calendar.monthrange(a, m)[1]
    return f"{comp}-{min(int(dia), ultimo):02d}"


def comp_atual() -> str:
    return hoje()[:7]


def para_data(s: str) -> date:
    return date.fromisoformat(s[:10])


def somar_dias(s: str, n: int) -> str:
    return (para_data(s) + timedelta(days=n)).isoformat()


def dias_ate(s: str) -> int:
    return (para_data(s) - para_data(hoje())).days


def nome_mes(comp: str, com_ano: bool = True) -> str:
    a, m = _am(comp)
    return f"{MESES[m - 1]} {a}" if com_ano else MESES[m - 1]


def data_curta(s: str) -> str:
    return f"{s[8:10]}/{s[5:7]}"


def mes_curto(comp: str) -> str:
    a, m = _am(comp)
    return f"{MESES[m - 1][:3]}/{a}"


def meses_entre(de: str, ate: str) -> int:
    a1, m1 = _am(de)
    a2, m2 = _am(ate)
    return (a2 - a1) * 12 + (m2 - m1)


def _arred(x: float) -> float:
    """Arredonda para centavos igual ao Math.round do JS (meio para cima)."""
    return math.floor(x * 100 + 0.5) / 100


def soma(valores) -> float:
    return _arred(sum(float(v or 0) for v in valores))


# ---------- Cartões, faturas e parcelas ----------
def comp_primeira_parcela(data: str, cartao: dict) -> str:
    """Compra feita no dia do fechamento ou depois já cai na fatura seguinte."""
    a, m, d = (int(x) for x in data[:10].split("-"))
    dia_fechamento = int(data_no_mes(comp_de(a, m), cartao["fechamento"])[8:])
    mes = m + (1 if d >= dia_fechamento else 0)
    if int(cartao["vencimento"]) <= int(cartao["fechamento"]):
        mes += 1  # vence no mês seguinte ao fechamento
    return comp_de(a, mes)


@dataclass
class Parcela:
    competencia: str
    valor: float
    numero: int
    total: int
    pre_paga: bool  # informada como já paga ao lançar uma compra antiga
    lanc: dict = field(repr=False)
    cartao: dict = field(repr=False)


def parcelas_de(lanc: dict, cartao: dict) -> list[Parcela]:
    n = int(lanc.get("parcelas") or 1)
    centavos = round(float(lanc["valor"]) * 100)
    base = centavos // n
    resto = centavos - base * n
    primeira = comp_primeira_parcela(lanc["data"], cartao)
    ja_pagas = min(n, int(lanc.get("parcelas_pagas") or 0))
    return [
        Parcela(
            competencia=somar_meses(primeira, i),
            valor=(base + (resto if i == 0 else 0)) / 100,
            numero=i + 1,
            total=n,
            pre_paga=i < ja_pagas,
            lanc=lanc,
            cartao=cartao,
        )
        for i in range(n)
    ]


def todas_parcelas(d: dict) -> list[Parcela]:
    cartoes = {c["id"]: c for c in d["cartoes"]}
    return [
        p
        for l in d["lancamentos"]
        if l["tipo"] == "despesa" and l.get("cartao_id") in cartoes
        for p in parcelas_de(l, cartoes[l["cartao_id"]])
    ]


def pagamento_fatura(d: dict, cartao_id: str, comp: str) -> dict | None:
    return next((f for f in d["faturas_pagas"] if f["cartao_id"] == cartao_id and f["competencia"] == comp), None)


def pagamento_item(d: dict, p: Parcela) -> dict | None:
    """Compra específica marcada como paga dentro de uma fatura (pagamento parcial)."""
    return next((x for x in d["itens_pagos"]
                 if x["lancamento_id"] == p.lanc["id"] and x["competencia"] == p.competencia), None)


def pagamentos_avulsos(d: dict, cartao_id: str, comp: str) -> list[dict]:
    """Valores soltos pagos na fatura ("sobrou dinheiro e paguei R$ 50")."""
    return [x for x in d.get("pagamentos_fatura", []) if x["cartao_id"] == cartao_id and x["competencia"] == comp]


def parcela_quitada(d: dict, p: Parcela) -> bool:
    return p.pre_paga or bool(pagamento_fatura(d, p.cartao["id"], p.competencia)) or bool(pagamento_item(d, p))


@dataclass
class Fatura:
    cartao: dict
    comp: str
    itens: list[Parcela]
    avulsos: list[dict]
    total_avulso: float
    total: float
    a_pagar: float
    pago: float
    parcial: bool
    vencimento: str
    fechamento: str
    pagamento: dict | None
    status: str  # aberta | fechada | vencida | paga | vazia


def fatura(d: dict, cartao: dict, comp: str, parcelas: list[Parcela] | None = None) -> Fatura:
    if parcelas is None:
        parcelas = todas_parcelas(d)
    itens = sorted((p for p in parcelas if p.cartao["id"] == cartao["id"] and p.competencia == comp),
                   key=lambda p: p.lanc["data"], reverse=True)
    total = soma(i.valor for i in itens)
    vencimento = data_no_mes(comp, cartao["vencimento"])
    comp_fechamento = comp if int(cartao["vencimento"]) > int(cartao["fechamento"]) else somar_meses(comp, -1)
    fechamento = data_no_mes(comp_fechamento, cartao["fechamento"])
    pagamento = pagamento_fatura(d, cartao["id"], comp)
    # O que falta: tira as compras pagas uma a uma, as parcelas informadas como pagas e os valores avulsos.
    avulsos = pagamentos_avulsos(d, cartao["id"], comp)
    total_avulso = soma(x["valor"] for x in avulsos)
    pendente_itens = soma(i.valor for i in itens if not parcela_quitada(d, i))
    a_pagar = 0 if pagamento else max(0, soma([pendente_itens, -total_avulso]))
    pago = soma([total, -a_pagar])
    h = hoje()
    if pagamento:
        status = "paga"
    elif total == 0:
        status = "vazia"
    elif a_pagar == 0:
        status = "paga"
    elif h > vencimento:
        status = "vencida"
    elif h >= fechamento:
        status = "fechada"
    else:
        status = "aberta"
    return Fatura(cartao, comp, itens, avulsos, total_avulso, total, a_pagar, pago,
                  pago > 0 and a_pagar > 0, vencimento, fechamento, pagamento, status)


def pendentes_por_mes(d: dict, cartao: dict, parcelas: list[Parcela] | None = None) -> dict[str, float]:
    """Quanto falta pagar em cada fatura do cartão (parcelas não pagas menos os valores avulsos)."""
    if parcelas is None:
        parcelas = todas_parcelas(d)
    pendente: dict[str, float] = {}
    for p in parcelas:
        if p.cartao["id"] != cartao["id"] or parcela_quitada(d, p):
            continue
        pendente[p.competencia] = soma([pendente.get(p.competencia), p.valor])
    return {comp: max(0, soma([v, -soma(x["valor"] for x in pagamentos_avulsos(d, cartao["id"], comp))]))
            for comp, v in pendente.items()}


def limite_usado(d: dict, cartao: dict, parcelas: list[Parcela] | None = None) -> float:
    """Limite comprometido = todas as parcelas ainda não pagas (inclusive as futuras)."""
    return soma(pendentes_por_mes(d, cartao, parcelas).values())


def limite_usado_em(d: dict, cartao: dict, comp: str, parcelas: list[Parcela] | None = None) -> float:
    """Limite em uso no começo de um mês futuro, supondo que as faturas anteriores foram pagas em dia."""
    if comp <= comp_atual():
        return limite_usado(d, cartao, parcelas)
    return soma(v for k, v in pendentes_por_mes(d, cartao, parcelas).items() if k >= comp)


def faturas_atrasadas(d: dict, parcelas: list[Parcela] | None = None) -> list[Fatura]:
    """Faturas com valor de meses anteriores que ficaram sem pagar."""
    if parcelas is None:
        parcelas = todas_parcelas(d)
    vistas, lista = set(), []
    for p in parcelas:
        chave = (p.cartao["id"], p.competencia)
        if chave in vistas:
            continue
        vistas.add(chave)
        f = fatura(d, p.cartao, p.competencia, parcelas)
        if f.status == "vencida":
            lista.append(f)
    return sorted(lista, key=lambda f: f.vencimento)


def contas_do_mes(d: dict, comp: str) -> list[dict]:
    h = hoje()
    lista = []
    for conta in d["contas_fixas"]:
        if conta.get("ativa") is False or conta["desde"] > comp:
            continue
        pagamento = next((p for p in d["contas_pagas"] if p["conta_id"] == conta["id"] and p["competencia"] == comp), None)
        vencimento = data_no_mes(comp, conta["dia"])
        status = "paga" if pagamento else ("vencida" if h > vencimento else "pendente")
        lista.append({"conta": conta, "comp": comp, "vencimento": vencimento, "pagamento": pagamento, "status": status})
    return sorted(lista, key=lambda x: x["vencimento"])


def parcelamentos(d: dict, parcelas: list[Parcela] | None = None) -> list[dict]:
    """Compras parceladas no cartão: quantas já foram pagas, quanto falta e quando termina."""
    if parcelas is None:
        parcelas = todas_parcelas(d)
    por_compra: dict[str, list[Parcela]] = {}
    for p in parcelas:
        if p.total >= 2:
            por_compra.setdefault(p.lanc["id"], []).append(p)
    lista = []
    for ps in por_compra.values():
        pagas = [p for p in ps if parcela_quitada(d, p)]
        lista.append({
            "lanc": ps[0].lanc, "cartao": ps[0].cartao, "total": len(ps),
            "valor_parcela": ps[-1].valor, "pagas": len(pagas),
            "restante": soma(p.valor for p in ps if p not in pagas),
            "primeira": ps[0].competencia, "ultima": ps[-1].competencia,
            "ativo": len(pagas) < len(ps),
        })
    return sorted(lista, key=lambda x: x["ultima"])


# ---------- Metas ----------
def guardado_na_meta(d: dict, meta_id: str) -> float:
    """Depósitos (positivos) e retiradas (negativos) somados."""
    return soma(m["valor"] for m in d["metas_movimentos"] if m["meta_id"] == meta_id)


def guardado_no_mes(d: dict, comp: str) -> float:
    return soma(m["valor"] for m in d["metas_movimentos"] if m["data"][:7] == comp)


# ---------- Resumo do mês ----------
@dataclass
class Resumo:
    comp: str
    parcelas: list[Parcela]
    receitas: list[dict]
    avulsas: list[dict]
    compras_credito: list[dict]
    parcelas_mes: list[Parcela]
    total_compras_credito: float
    faturas: list[Fatura]
    contas: list[dict]
    por_categoria: dict[str, float]
    total_receitas: float
    total_contas_pendentes: float
    gastos: float
    guardado: float
    a_pagar: float
    saldo: float
    limite_total: float
    limite_usado: float


def resumo_mes(d: dict, comp: str) -> Resumo:
    """Visão de caixa do mês: compras no cartão contam no mês em que a fatura vence."""
    parcelas = todas_parcelas(d)
    do_mes = lambda l: l["data"][:7] == comp  # noqa: E731
    receitas = [l for l in d["lancamentos"] if l["tipo"] == "receita" and do_mes(l)]
    avulsas = [l for l in d["lancamentos"] if l["tipo"] == "despesa" and not l.get("cartao_id") and do_mes(l)]
    # Compras no cartão feitas neste mês (valor total), mesmo que a fatura vença no mês seguinte.
    ids_cartoes = {c["id"] for c in d["cartoes"]}
    compras_credito = [l for l in d["lancamentos"]
                       if l["tipo"] == "despesa" and l.get("cartao_id") in ids_cartoes and do_mes(l)]
    parcelas_mes = [p for p in parcelas if p.competencia == comp]
    faturas = [fatura(d, c, comp, parcelas) for c in d["cartoes"]]
    contas = contas_do_mes(d, comp)

    total_receitas = soma(l["valor"] for l in receitas)
    total_avulsas = soma(l["valor"] for l in avulsas)
    total_faturas = soma(f.total for f in faturas)
    total_contas_pendentes = soma(c["conta"]["valor"] for c in contas if not c["pagamento"])

    por_categoria: dict[str, float] = {}
    for l in avulsas + compras_credito:
        por_categoria[l["categoria"]] = soma([por_categoria.get(l["categoria"]), l["valor"]])

    gastos = soma([total_avulsas, total_faturas])
    guardado = guardado_no_mes(d, comp)
    return Resumo(
        comp=comp, parcelas=parcelas, receitas=receitas, avulsas=avulsas, compras_credito=compras_credito,
        parcelas_mes=parcelas_mes, total_compras_credito=soma(l["valor"] for l in compras_credito),
        faturas=faturas, contas=contas, por_categoria=por_categoria,
        total_receitas=total_receitas, total_contas_pendentes=total_contas_pendentes,
        gastos=gastos, guardado=guardado,
        a_pagar=soma([*(f.a_pagar for f in faturas if f.a_pagar > 0), total_contas_pendentes]),
        saldo=soma([total_receitas, -gastos, -total_contas_pendentes, -guardado]),
        limite_total=soma(c["limite"] for c in d["cartoes"]),
        limite_usado=soma(limite_usado(d, c, parcelas) for c in d["cartoes"]),
    )


# ---------- Validações com expressões regulares (REGEX) ----------
# E-mail: parte local (letras, números, ponto, sinal de mais, hífen ou sublinhado), um "@",
# um domínio e pelo menos uma extensão de 2 letras ou mais (ex.: nome@exemplo.com.br).
REGEX_EMAIL = re.compile(r"^[\w.+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$")
# Código da verificação em duas etapas: exatamente 6 números.
REGEX_CODIGO = re.compile(r"^\d{6}$")


def email_valido(texto: str) -> bool:
    return bool(REGEX_EMAIL.fullmatch(texto.strip()))


def codigo_valido(texto: str) -> bool:
    return bool(REGEX_CODIGO.fullmatch(texto.strip()))


# ---------- Valores em reais ----------
def brl(valor: float) -> str:
    """1234.5 → 'R$ 1.234,50' (formato brasileiro, sinal antes do R$)."""
    v = _arred(float(valor or 0))
    texto = f"{abs(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"-R$ {texto}" if v < 0 else f"R$ {texto}"


def ler_valor(texto: str) -> float | None:
    """Aceita '1.234,56', '1234,56', '1234.56' e '1.500' (milhar)."""
    s = str(texto).strip().replace("R$", "").replace(" ", "")
    if not s:
        return None
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif s.count(".") >= 1 and all(len(g) == 3 for g in s.split(".")[1:]) and len(s.split(".")[0]) <= 3:
        s = s.replace(".", "")
    try:
        return _arred(float(s))
    except ValueError:
        return None
