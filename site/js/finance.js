// Regras financeiras: datas, faturas, parcelas, limites e resumo do mês.
// "Competência" é o mês no formato AAAA-MM. A fatura de um cartão é identificada pelo mês em que VENCE.

const CATEGORIAS = {
  despesa: [
    { id: 'mercado', nome: 'Mercado' },
    { id: 'alimentacao', nome: 'Restaurante e delivery' },
    { id: 'transporte', nome: 'Transporte' },
    { id: 'casa', nome: 'Casa e aluguel' },
    { id: 'contas', nome: 'Luz, água e internet' },
    { id: 'saude', nome: 'Saúde' },
    { id: 'educacao', nome: 'Educação' },
    { id: 'lazer', nome: 'Lazer' },
    { id: 'compras', nome: 'Compras' },
    { id: 'assinaturas', nome: 'Assinaturas' },
    { id: 'beleza', nome: 'Beleza e cuidados' },
    { id: 'pets', nome: 'Pets' },
    { id: 'outros', nome: 'Outros' },
  ],
  receita: [
    { id: 'salario', nome: 'Salário' },
    { id: 'extra', nome: 'Renda extra' },
    { id: 'investimentos', nome: 'Investimentos' },
    { id: 'outras_receitas', nome: 'Outras entradas' },
  ],
};
const CATEGORIA_POR_ID = Object.fromEntries(
  [...CATEGORIAS.despesa, ...CATEGORIAS.receita].map((c) => [c.id, c]),
);
const categoria = (id) => CATEGORIA_POR_ID[id] || { id, nome: id };

const FORMAS = [
  { id: 'pix', nome: 'Pix' },
  { id: 'debito', nome: 'Débito' },
  { id: 'dinheiro', nome: 'Dinheiro' },
  { id: 'credito', nome: 'Crédito' },
];
const nomeForma = (id) => FORMAS.find((f) => f.id === id)?.nome || '';
// Lançamentos antigos não tinham "forma": deduz pelo cartão.
const formaDe = (l) => (l.tipo !== 'despesa' ? null : l.forma || (l.cartao_id ? 'credito' : 'pix'));

const MESES = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho',
  'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'];

const pad = (n) => String(n).padStart(2, '0');
function compDe(ano, mes) {
  const d = new Date(ano, mes - 1, 1);
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}`;
}
function somarMeses(comp, n) {
  const [a, m] = comp.split('-').map(Number);
  return compDe(a, m + n);
}
// Dia "dia" dentro do mês, ajustando 31 → último dia (ex.: 28/02).
function dataNoMes(comp, dia) {
  const [a, m] = comp.split('-').map(Number);
  const ultimo = new Date(a, m, 0).getDate();
  return `${comp}-${pad(Math.min(dia, ultimo))}`;
}
// Sempre no horário de Brasília, inclusive no servidor que manda os avisos (que roda em UTC).
const FORMATO_DIA = new Intl.DateTimeFormat('en-CA', {
  timeZone: 'America/Sao_Paulo', year: 'numeric', month: '2-digit', day: '2-digit',
});
const hoje = () => FORMATO_DIA.format(new Date());
function somarDias(s, n) {
  const [a, m, d] = s.split('-').map(Number);
  const x = new Date(a, m - 1, d + n);
  return `${x.getFullYear()}-${pad(x.getMonth() + 1)}-${pad(x.getDate())}`;
}
const compAtual = () => hoje().slice(0, 7);
function paraData(s) {
  const [a, m, d] = s.split('-').map(Number);
  return new Date(a, m - 1, d);
}
const diasAte = (s) => Math.round((paraData(s) - paraData(hoje())) / 86400000);
function nomeMes(comp, comAno = true) {
  const [a, m] = comp.split('-').map(Number);
  return comAno ? `${MESES[m - 1]} ${a}` : MESES[m - 1];
}
const dataCurta = (s) => `${s.slice(8, 10)}/${s.slice(5, 7)}`;
function mesCurto(comp) {
  const [a, m] = comp.split('-').map(Number);
  return `${MESES[m - 1].slice(0, 3)}/${a}`;
}
function mesesEntre(de, ate) {
  const [a1, m1] = de.split('-').map(Number);
  const [a2, m2] = ate.split('-').map(Number);
  return (a2 - a1) * 12 + (m2 - m1);
}

const soma = (valores) => Math.round(valores.reduce((s, v) => s + Number(v || 0), 0) * 100) / 100;

// Compra feita no dia do fechamento ou depois já cai na fatura seguinte.
function compPrimeiraParcela(data, cartao) {
  const [a, m, d] = data.split('-').map(Number);
  const diaFechamento = Number(dataNoMes(compDe(a, m), cartao.fechamento).slice(8));
  let mes = m + (d >= diaFechamento ? 1 : 0);
  if (cartao.vencimento <= cartao.fechamento) mes += 1; // vence no mês seguinte ao fechamento
  return compDe(a, mes);
}

function parcelasDe(lanc, cartao) {
  const n = Number(lanc.parcelas) || 1;
  const centavos = Math.round(Number(lanc.valor) * 100);
  const base = Math.floor(centavos / n);
  const resto = centavos - base * n;
  const primeira = compPrimeiraParcela(lanc.data, cartao);
  const jaPagas = Math.min(n, Number(lanc.parcelas_pagas) || 0);
  return Array.from({ length: n }, (_, i) => ({
    competencia: somarMeses(primeira, i),
    valor: (base + (i === 0 ? resto : 0)) / 100,
    numero: i + 1,
    total: n,
    // Parcela que você informou como já paga ao lançar uma compra antiga.
    prePaga: i < jaPagas,
    lanc,
    cartao,
  }));
}

function todasParcelas(d) {
  const cartoes = Object.fromEntries(d.cartoes.map((c) => [c.id, c]));
  return d.lancamentos
    .filter((l) => l.tipo === 'despesa' && cartoes[l.cartao_id])
    .flatMap((l) => parcelasDe(l, cartoes[l.cartao_id]));
}

const pagamentoFatura = (d, cartaoId, comp) =>
  d.faturas_pagas.find((f) => f.cartao_id === cartaoId && f.competencia === comp);
// Compra específica marcada como paga dentro de uma fatura (pagamento parcial).
const pagamentoItem = (d, p) =>
  d.itens_pagos.find((x) => x.lancamento_id === p.lanc.id && x.competencia === p.competencia);
// Valores soltos pagos na fatura ("sobrou dinheiro e paguei R$ 50").
const pagamentosAvulsos = (d, cartaoId, comp) =>
  (d.pagamentos_fatura || []).filter((x) => x.cartao_id === cartaoId && x.competencia === comp);
const parcelaQuitada = (d, p) =>
  p.prePaga || Boolean(pagamentoFatura(d, p.cartao.id, p.competencia)) || Boolean(pagamentoItem(d, p));

function fatura(d, cartao, comp, parcelas = todasParcelas(d)) {
  const itens = parcelas
    .filter((p) => p.cartao.id === cartao.id && p.competencia === comp)
    .sort((a, b) => b.lanc.data.localeCompare(a.lanc.data));
  const total = soma(itens.map((i) => i.valor));
  const vencimento = dataNoMes(comp, cartao.vencimento);
  const compFechamento = cartao.vencimento > cartao.fechamento ? comp : somarMeses(comp, -1);
  const fechamento = dataNoMes(compFechamento, cartao.fechamento);
  const pagamento = pagamentoFatura(d, cartao.id, comp);
  // O que ainda falta pagar: tira as compras já pagas uma a uma, as parcelas informadas como pagas
  // e os valores avulsos pagos nesta fatura.
  const avulsos = pagamentosAvulsos(d, cartao.id, comp);
  const totalAvulso = soma(avulsos.map((x) => x.valor));
  const pendenteItens = soma(itens.filter((i) => !parcelaQuitada(d, i)).map((i) => i.valor));
  const aPagar = pagamento ? 0 : Math.max(0, soma([pendenteItens, -totalAvulso]));
  const pago = soma([total, -aPagar]);
  const h = hoje();
  let status = 'aberta';
  if (pagamento) status = 'paga';
  else if (total === 0) status = 'vazia';
  else if (aPagar === 0) status = 'paga';
  else if (h > vencimento) status = 'vencida';
  else if (h >= fechamento) status = 'fechada';
  return { cartao, comp, itens, avulsos, totalAvulso, total, aPagar, pago, parcial: pago > 0 && aPagar > 0, vencimento, fechamento, pagamento, status };
}

// Quanto falta pagar em cada fatura do cartão (parcelas não pagas menos os valores avulsos).
function pendentesPorMes(d, cartao, parcelas = todasParcelas(d)) {
  const pendente = {};
  for (const p of parcelas) {
    if (p.cartao.id !== cartao.id || parcelaQuitada(d, p)) continue;
    pendente[p.competencia] = soma([pendente[p.competencia], p.valor]);
  }
  return Object.fromEntries(Object.entries(pendente).map(([comp, valor]) =>
    [comp, Math.max(0, soma([valor, -soma(pagamentosAvulsos(d, cartao.id, comp).map((x) => x.valor))]))]));
}

// Limite comprometido = todas as parcelas ainda não pagas (inclusive as futuras).
function limiteUsado(d, cartao, parcelas = todasParcelas(d)) {
  return soma(Object.values(pendentesPorMes(d, cartao, parcelas)));
}

// Limite em uso no começo de um mês futuro, supondo que as faturas anteriores foram pagas em dia.
function limiteUsadoEm(d, cartao, comp, parcelas = todasParcelas(d)) {
  if (comp <= compAtual()) return limiteUsado(d, cartao, parcelas);
  return soma(Object.entries(pendentesPorMes(d, cartao, parcelas))
    .filter(([k]) => k >= comp).map(([, valor]) => valor));
}

// Faturas com valor de meses anteriores que ficaram sem pagar.
function faturasAtrasadas(d, parcelas = todasParcelas(d)) {
  const vistas = new Set();
  const lista = [];
  for (const p of parcelas) {
    const chave = `${p.cartao.id}|${p.competencia}`;
    if (vistas.has(chave)) continue;
    vistas.add(chave);
    const f = fatura(d, p.cartao, p.competencia, parcelas);
    if (f.status === 'vencida') lista.push(f);
  }
  return lista.sort((a, b) => a.vencimento.localeCompare(b.vencimento));
}

function contasDoMes(d, comp) {
  const h = hoje();
  return d.contas_fixas
    .filter((c) => c.ativa !== false && c.desde <= comp)
    .map((conta) => {
      const pagamento = d.contas_pagas.find((p) => p.conta_id === conta.id && p.competencia === comp);
      const vencimento = dataNoMes(comp, conta.dia);
      const status = pagamento ? 'paga' : h > vencimento ? 'vencida' : 'pendente';
      return { conta, comp, vencimento, pagamento, status };
    })
    .sort((a, b) => a.vencimento.localeCompare(b.vencimento));
}

// Compras parceladas no cartão: quantas já foram pagas, quanto falta e quando termina.
function parcelamentos(d, parcelas = todasParcelas(d)) {
  const porCompra = new Map();
  for (const p of parcelas) {
    if (p.total < 2) continue;
    if (!porCompra.has(p.lanc.id)) porCompra.set(p.lanc.id, []);
    porCompra.get(p.lanc.id).push(p);
  }
  return [...porCompra.values()].map((ps) => {
    const pagas = ps.filter((p) => parcelaQuitada(d, p));
    return {
      lanc: ps[0].lanc,
      cartao: ps[0].cartao,
      total: ps.length,
      valorParcela: ps[ps.length - 1].valor,
      pagas: pagas.length,
      restante: soma(ps.filter((p) => !pagas.includes(p)).map((p) => p.valor)),
      primeira: ps[0].competencia,
      ultima: ps[ps.length - 1].competencia,
      ativo: pagas.length < ps.length,
    };
  }).sort((a, b) => a.ultima.localeCompare(b.ultima));
}

// Metas de economia: o valor guardado é a soma dos depósitos (positivos) e retiradas (negativos).
const guardadoNaMeta = (d, metaId) =>
  soma(d.metas_movimentos.filter((m) => m.meta_id === metaId).map((m) => m.valor));
const guardadoNoMes = (d, comp) =>
  soma(d.metas_movimentos.filter((m) => m.data.slice(0, 7) === comp).map((m) => m.valor));

// Visão de caixa do mês: compras no cartão contam no mês em que a fatura vence.
function resumoMes(d, comp) {
  const parcelas = todasParcelas(d);
  const doMes = (l) => l.data.slice(0, 7) === comp;
  const receitas = d.lancamentos.filter((l) => l.tipo === 'receita' && doMes(l));
  const avulsas = d.lancamentos.filter((l) => l.tipo === 'despesa' && !l.cartao_id && doMes(l));
  // Compras no cartão feitas neste mês (valor total), mesmo que a fatura vença no mês seguinte.
  const idsCartoes = new Set(d.cartoes.map((c) => c.id));
  const comprasCredito = d.lancamentos.filter((l) => l.tipo === 'despesa' && idsCartoes.has(l.cartao_id) && doMes(l));
  const parcelasMes = parcelas.filter((p) => p.competencia === comp);
  const faturas = d.cartoes.map((c) => fatura(d, c, comp, parcelas));
  const contas = contasDoMes(d, comp);

  const totalReceitas = soma(receitas.map((l) => l.valor));
  const totalAvulsas = soma(avulsas.map((l) => l.valor));
  const totalFaturas = soma(faturas.map((f) => f.total));
  const contasPendentes = contas.filter((c) => !c.pagamento);
  const totalContasPendentes = soma(contasPendentes.map((c) => c.conta.valor));
  const faturasPendentes = faturas.filter((f) => f.aPagar > 0);

  const porCategoria = {};
  for (const l of avulsas) porCategoria[l.categoria] = soma([porCategoria[l.categoria], l.valor]);
  for (const l of comprasCredito) porCategoria[l.categoria] = soma([porCategoria[l.categoria], l.valor]);

  const gastos = soma([totalAvulsas, totalFaturas]);
  const guardado = guardadoNoMes(d, comp);
  return {
    comp, parcelas, receitas, avulsas, comprasCredito, parcelasMes,
    totalComprasCredito: soma(comprasCredito.map((l) => l.valor)), faturas, contas, porCategoria,
    totalReceitas,
    totalContasPendentes,
    gastos,
    guardado,
    aPagar: soma([...faturasPendentes.map((f) => f.aPagar), totalContasPendentes]),
    saldo: soma([totalReceitas, -gastos, -totalContasPendentes, -guardado]),
    limiteTotal: soma(d.cartoes.map((c) => c.limite)),
    limiteUsado: soma(d.cartoes.map((c) => limiteUsado(d, c, parcelas))),
  };
}
