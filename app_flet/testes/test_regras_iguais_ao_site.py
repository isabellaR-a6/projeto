"""Confere que financas_app/regras.py dá os mesmos números que js/finance.js (o site).

Roda as duas versões com os mesmos dados (o JS pelo Node) e compara campo a campo.
Uso:  python -m pytest testes   (ou)   python testes/test_regras_iguais_ao_site.py
"""
import json
import pathlib
import random
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from financas_app import regras as R  # noqa: E402

FINANCE_JS = RAIZ.parent / "js" / "finance.js"


def dados_de_exemplo(semente: int) -> dict:
    rnd = random.Random(semente)
    hoje = R.hoje()
    cartoes = [
        {"id": "c1", "nome": "Nubank", "limite": 5500, "fechamento": 3, "vencimento": 10},
        {"id": "c2", "nome": "Itaú", "limite": 2000, "fechamento": 25, "vencimento": 5},
        {"id": "c3", "nome": "Inter", "limite": 1200, "fechamento": 31, "vencimento": 7},
    ]
    lanc, itens, pagas, avulsos = [], [], [], []
    for i in range(60):
        data = R.somar_dias(hoje, rnd.randint(-150, 40))
        tipo = "receita" if rnd.random() < 0.2 else "despesa"
        cartao = rnd.choice([None, "c1", "c2", "c3"]) if tipo == "despesa" else None
        n = rnd.choice([1, 1, 1, 2, 3, 6, 10, 12]) if cartao else 1
        lanc.append({
            "id": f"l{i}", "tipo": tipo, "descricao": f"item {i}", "valor": round(rnd.uniform(5, 3000), 2),
            "data": data, "categoria": rnd.choice(["mercado", "lazer", "compras", "salario"]),
            "forma": "credito" if cartao else rnd.choice(["pix", "debito", None]), "cartao_id": cartao,
            "parcelas": n, "parcelas_pagas": rnd.choice([0, 0, 0, 1, 2]) if n > 2 else 0,
            "created_at": f"2026-01-01T00:00:{i:02d}Z",
        })
    for c in ("c1", "c2", "c3"):
        for k in range(-4, 2):
            comp = R.somar_meses(R.comp_atual(), k)
            if rnd.random() < 0.4:
                pagas.append({"id": f"f{c}{k}", "cartao_id": c, "competencia": comp})
            if rnd.random() < 0.4:
                avulsos.append({"id": f"a{c}{k}", "cartao_id": c, "competencia": comp, "valor": round(rnd.uniform(10, 400), 2)})
    for l in lanc:
        if l["cartao_id"] and rnd.random() < 0.3:
            ps = R.parcelas_de(l, next(c for c in cartoes if c["id"] == l["cartao_id"]))
            itens.append({"id": f"i{l['id']}", "lancamento_id": l["id"], "competencia": rnd.choice(ps).competencia})
    contas = [{"id": "k1", "descricao": "Aluguel", "valor": 1200, "dia": 5, "categoria": "casa",
               "desde": R.somar_meses(R.comp_atual(), -3), "ativa": True},
              {"id": "k2", "descricao": "Game Pass", "valor": 59.99, "dia": 31, "categoria": "assinaturas",
               "desde": R.comp_atual(), "ativa": True}]
    contas_pagas = [{"id": "kp1", "conta_id": "k1", "competencia": R.somar_meses(R.comp_atual(), -1)}]
    metas = [{"id": "m1", "nome": "Viagem", "alvo": 8000}]
    movs = [{"id": "mv1", "meta_id": "m1", "valor": 300, "data": hoje},
            {"id": "mv2", "meta_id": "m1", "valor": -50.5, "data": R.somar_dias(hoje, -40)}]
    return {"cartoes": cartoes, "lancamentos": lanc, "faturas_pagas": pagas, "itens_pagos": itens,
            "pagamentos_fatura": avulsos, "contas_fixas": contas, "contas_pagas": contas_pagas,
            "metas": metas, "metas_movimentos": movs}


SCRIPT_JS = r"""
const fs = require('fs'); const vm = require('vm');
const ctx = {}; vm.createContext(ctx);
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8') + `;this.R = { resumoMes, fatura, limiteUsado, limiteUsadoEm,
  parcelamentos, faturasAtrasadas, compAtual, somarMeses, guardadoNaMeta, compPrimeiraParcela };`, ctx);
const R = ctx.R; const d = JSON.parse(fs.readFileSync(0, 'utf8'));
const meses = [-4, -3, -2, -1, 0, 1, 2, 3].map((k) => R.somarMeses(R.compAtual(), k));
const out = { resumos: {}, faturas: {}, limites: {}, limitesEm: {} };
for (const comp of meses) {
  const r = R.resumoMes(d, comp);
  out.resumos[comp] = { totalReceitas: r.totalReceitas, gastos: r.gastos, guardado: r.guardado, aPagar: r.aPagar,
    saldo: r.saldo, limiteUsado: r.limiteUsado, totalComprasCredito: r.totalComprasCredito,
    totalContasPendentes: r.totalContasPendentes, porCategoria: r.porCategoria };
  for (const c of d.cartoes) {
    const f = R.fatura(d, c, comp);
    out.faturas[`${c.id}|${comp}`] = { total: f.total, aPagar: f.aPagar, pago: f.pago, status: f.status,
      vencimento: f.vencimento, fechamento: f.fechamento, itens: f.itens.length };
    out.limitesEm[`${c.id}|${comp}`] = R.limiteUsadoEm(d, c, comp);
  }
}
for (const c of d.cartoes) out.limites[c.id] = R.limiteUsado(d, c);
out.parcelamentos = R.parcelamentos(d).map((p) => [p.lanc.id, p.pagas, p.restante, p.primeira, p.ultima, p.ativo]);
out.atrasadas = R.faturasAtrasadas(d).map((f) => `${f.cartao.id}|${f.comp}`);
out.guardado = R.guardadoNaMeta(d, 'm1');
out.primeira = ['2026-02-28', '2026-03-31', '2026-01-03', '2026-01-02'].map((x) => d.cartoes.map((c) => R.compPrimeiraParcela(x, c)));
process.stdout.write(JSON.stringify(out));
"""


def resultado_python(d: dict) -> dict:
    meses = [R.somar_meses(R.comp_atual(), k) for k in (-4, -3, -2, -1, 0, 1, 2, 3)]
    out = {"resumos": {}, "faturas": {}, "limites": {}, "limitesEm": {}}
    for comp in meses:
        r = R.resumo_mes(d, comp)
        out["resumos"][comp] = {
            "totalReceitas": r.total_receitas, "gastos": r.gastos, "guardado": r.guardado, "aPagar": r.a_pagar,
            "saldo": r.saldo, "limiteUsado": r.limite_usado, "totalComprasCredito": r.total_compras_credito,
            "totalContasPendentes": r.total_contas_pendentes, "porCategoria": r.por_categoria}
        for c in d["cartoes"]:
            f = R.fatura(d, c, comp)
            out["faturas"][f"{c['id']}|{comp}"] = {
                "total": f.total, "aPagar": f.a_pagar, "pago": f.pago, "status": f.status,
                "vencimento": f.vencimento, "fechamento": f.fechamento, "itens": len(f.itens)}
            out["limitesEm"][f"{c['id']}|{comp}"] = R.limite_usado_em(d, c, comp)
    for c in d["cartoes"]:
        out["limites"][c["id"]] = R.limite_usado(d, c)
    out["parcelamentos"] = [[p["lanc"]["id"], p["pagas"], p["restante"], p["primeira"], p["ultima"], p["ativo"]]
                            for p in R.parcelamentos(d)]
    out["atrasadas"] = [f"{f.cartao['id']}|{f.comp}" for f in R.faturas_atrasadas(d)]
    out["guardado"] = R.guardado_na_meta(d, "m1")
    out["primeira"] = [[R.comp_primeira_parcela(x, c) for c in d["cartoes"]]
                       for x in ("2026-02-28", "2026-03-31", "2026-01-03", "2026-01-02")]
    return out


def resultado_js(d: dict) -> dict:
    proc = subprocess.run(["node", "-e", SCRIPT_JS, str(FINANCE_JS)], input=json.dumps(d),
                          capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def _normalizar(x):
    """Números iguais (1 e 1.0) e floats arredondados a centavos."""
    if isinstance(x, dict):
        return {k: _normalizar(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_normalizar(v) for v in x]
    if isinstance(x, bool) or x is None or isinstance(x, str):
        return x
    return round(float(x), 2)


def test_python_igual_ao_site():
    for semente in range(8):
        d = dados_de_exemplo(semente)
        js, py = _normalizar(resultado_js(d)), _normalizar(resultado_python(d))
        for chave in js:
            assert py[chave] == js[chave], f"semente {semente}, '{chave}' diferente"


def test_formatos():
    assert R.brl(1234.5) == "R$ 1.234,50"
    assert R.brl(-765.34) == "-R$ 765,34"
    assert R.brl(0) == "R$ 0,00"
    assert R.ler_valor("1.234,56") == 1234.56
    assert R.ler_valor("1.500") == 1500
    assert R.ler_valor("12,5") == 12.5
    assert R.ler_valor("1.5") == 1.5
    assert R.ler_valor("abc") is None
    assert R.data_no_mes("2026-02", 31) == "2026-02-28"
    assert R.somar_meses("2026-11", 3) == "2027-02"
    assert R.somar_meses("2026-01", -1) == "2025-12"


if __name__ == "__main__":
    test_formatos()
    test_python_igual_ao_site()
    print("OK: as regras em Python dão os mesmos resultados do site.")
