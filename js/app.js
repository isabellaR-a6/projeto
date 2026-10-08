// Interface: telas, formulários e ações.
const $ = (sel, el = document) => el.querySelector(sel);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const BRL = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });

function lerPreferencia(chave, padrao) {
  try { return JSON.parse(localStorage.getItem(chave)) ?? padrao; } catch { return padrao; }
}
function gravarPreferencia(chave, valor) {
  try { localStorage.setItem(chave, JSON.stringify(valor)); } catch { /* sem armazenamento */ }
}

const S = {
  dados: null,
  mes: compAtual(),
  tela: 'inicio',
  ocultar: lerPreferencia('financas-ocultar', false),
  filtro: 'todos',
  busca: '',
  // Campos da aba Simular (nada disso é salvo no banco).
  sim: { tipo: 'credito', valor: '', cartao: '', data: '', modo: 'avista', parcelas: 2, fatura: '' },
};

const dinheiro = (v) => (S.ocultar ? 'R$ ••••' : BRL.format(Number(v) || 0));
const pct = (parte, todo) => (todo > 0 ? Math.min(100, Math.max(0, Math.round((parte / todo) * 100))) : 0);
const corBarra = (p) => (p >= 90 ? 'perigo' : p >= 70 ? 'aviso' : '');

function lerValor(texto) {
  let s = String(texto).trim().replace(/[R$\s]/g, '');
  if (s.includes(',')) s = s.replace(/\./g, '').replace(',', '.');
  else if (/^\d{1,3}(\.\d{3})+$/.test(s)) s = s.replace(/\./g, '');
  const n = Number(s);
  return Number.isFinite(n) ? Math.round(n * 100) / 100 : NaN;
}
const NUMERO = new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const valorParaCampo = (v) => (v ? NUMERO.format(Number(v)) : '');

// Campo de dinheiro estilo app de banco: só digita números e a vírgula entra sozinha (1500 → 15,00).
function mascaraDinheiro(campo) {
  const digitos = campo.value.replace(/\D/g, '').replace(/^0+/, '').slice(0, 11);
  campo.value = digitos ? NUMERO.format(Number(digitos) / 100) : '';
}

function quando(dias) {
  if (dias === 0) return 'hoje';
  if (dias === 1) return 'amanhã';
  if (dias === -1) return 'ontem';
  return dias > 0 ? `em ${dias} dias` : `há ${-dias} dias`;
}

/* ---------- Ícones ---------- */
const ICONES = {
  inicio: '<path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/><path d="M10 21v-6h4v6"/>',
  lancamentos: '<path d="M8 6h13M8 12h13M8 18h13"/><path d="M3 6h.01M3 12h.01M3 18h.01"/>',
  cartoes: '<rect x="2" y="5" width="20" height="14" rx="2.5"/><path d="M2 10h20M6 15h4"/>',
  contas: '<rect x="3" y="4" width="18" height="17" rx="2.5"/><path d="M16 2v4M8 2v4M3 10h18"/><path d="m9 15.5 2 2 4-4"/>',
  metas: '<path d="M19 7V5a2 2 0 0 0-2-2H5a2 2 0 0 0 0 4h15a1 1 0 0 1 1 1v4h-3a2 2 0 0 0 0 4h3a1 1 0 0 0 1-1v-2"/><path d="M3 5v14a2 2 0 0 0 2 2h15a1 1 0 0 0 1-1v-4"/>',
  olho: '<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>',
  olhoFechado: '<path d="M3 3l18 18"/><path d="M10.6 5.1A10.8 10.8 0 0 1 12 5c6.4 0 10 7 10 7a17.6 17.6 0 0 1-3.2 4.1M6.6 6.6C3.7 8.4 2 12 2 12s3.6 7 10 7a10 10 0 0 0 5.4-1.6"/><path d="M9.9 9.9a3 3 0 0 0 4.2 4.2"/>',
  sair: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 17 5-5-5-5M21 12H9"/>',
  mais: '<path d="M12 5v14M5 12h14"/>',
  esquerda: '<path d="m15 18-6-6 6-6"/>',
  direita: '<path d="m9 18 6-6-6-6"/>',
  editar: '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/>',
  check: '<path d="M20 6 9 17l-5-5"/>',
  simular: '<rect x="4" y="2" width="16" height="20" rx="2"/><path d="M8 6h8M8 11h.01M12 11h.01M16 11h.01M8 15h.01M12 15h.01M16 15h.01M8 19h.01M12 19h4"/>',
  entradas: '<path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M4 21h16"/>',
  sino: '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>',
  escudo: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/><path d="m9 12 2 2 4-4"/>',
};
const icone = (nome, cls = 'ic') =>
  `<svg class="${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONES[nome]}</svg>`;

const TELAS = [
  { id: 'inicio', nome: 'Início' },
  { id: 'lancamentos', nome: 'Lançamentos' },
  { id: 'cartoes', nome: 'Cartões' },
  { id: 'simular', nome: 'Simular' },
  { id: 'entradas', nome: 'Entradas' },
  { id: 'metas', nome: 'Metas' },
];

// Cor do marcador de cada lançamento: entrada em verde, crédito na cor do cartão, o resto em roxo.
function corDoLancamento(l) {
  if (l.tipo === 'receita') return 'var(--positivo)';
  const cartao = S.dados.cartoes.find((c) => c.id === l.cartao_id);
  return cartao ? cartao.cor : 'var(--roxo)';
}

/* ---------- Toast ---------- */
let timerToast;
function toast(msg, erro = false) {
  const el = $('#toast');
  el.textContent = msg;
  el.className = `toast visivel${erro ? ' erro' : ''}`;
  clearTimeout(timerToast);
  timerToast = setTimeout(() => { el.className = 'toast'; }, 2800);
}

async function recarregar() { S.dados = await Store.carregarTudo(); }

// Executa uma alteração, recarrega os dados e redesenha.
// Só uma alteração por vez: um segundo toque enquanto a primeira ainda está salvando
// (a internet do celular pode demorar) é ignorado, senão o registro era gravado em dobro.
let salvando = false;
async function executar(fn, sucesso) {
  if (salvando) return false;
  salvando = true;
  document.body.classList.add('salvando');
  try {
    await fn();
    await recarregar();
    render();
    if (sucesso) toast(sucesso);
    return true;
  } catch (e) {
    console.error(e);
    toast(e.message || 'Algo deu errado.', true);
    return false;
  } finally {
    salvando = false;
    document.body.classList.remove('salvando');
  }
}

/* ---------- Login ---------- */
function telaLogin(erro = '') {
  $('#app').innerHTML = `
    <div class="login">
      <form class="login-caixa" id="form-login">
        <h1>Minhas Finanças</h1>
        <p class="sutil">Área particular. Entre com seu e-mail e senha.</p>
        <label>E-mail<input type="email" name="email" autocomplete="email" required></label>
        <label>Senha<input type="password" name="senha" autocomplete="current-password" required></label>
        <p class="erro-login" role="alert">${esc(erro)}</p>
        <button class="btn primario largo" type="submit">Entrar</button>
      </form>
    </div>`;
  $('#form-login').addEventListener('submit', async (e) => {
    e.preventDefault();
    const f = e.target;
    const botao = f.querySelector('button');
    botao.disabled = true;
    botao.textContent = 'Entrando…';
    try {
      await Store.entrar(f.email.value.trim(), f.senha.value);
      if (await Store.precisaCodigo()) telaCodigo();
      else await iniciarApp();
    } catch (err) {
      telaLogin(err.message);
    }
  });
}

const campoCodigo = '<input name="codigo" inputmode="numeric" autocomplete="one-time-code" pattern="[0-9]{6}" maxlength="6" placeholder="000000" class="campo-codigo" required autofocus>';
const lerCodigo = (campo) => campo.value.replace(/\D/g, '');

function telaCodigo(erro = '') {
  $('#app').innerHTML = `
    <div class="login">
      <form class="login-caixa" id="form-codigo">
        <h1>Verificação</h1>
        <p class="sutil">Abra seu app autenticador e digite o código de 6 dígitos de <strong>Minhas Finanças</strong>.</p>
        <label>Código${campoCodigo}</label>
        <p class="erro-login" role="alert">${esc(erro)}</p>
        <button class="btn primario largo" type="submit">Confirmar</button>
        <button class="link" type="button" id="voltar-login">Entrar com outra conta</button>
      </form>
    </div>`;
  $('#form-codigo [name=codigo]').focus();
  $('#voltar-login').addEventListener('click', async () => { await Store.sair(); telaLogin(); });
  $('#form-codigo').addEventListener('submit', async (e) => {
    e.preventDefault();
    const botao = e.target.querySelector('button[type=submit]');
    botao.disabled = true;
    botao.textContent = 'Verificando…';
    try {
      await Store.verificarCodigo(lerCodigo(e.target.codigo));
      await iniciarApp();
    } catch (err) {
      telaCodigo(err.message);
    }
  });
}

/* ---------- Estrutura ---------- */
function render() {
  const avisoTeste = Store.remoto ? '' : `
    <div class="faixa-teste">Modo de teste: os dados ficam só neste navegador. Veja o README para ativar o login e a sincronização.</div>`;
  $('#app').innerHTML = `
    ${avisoTeste}
    <div class="estrutura">
      <aside class="lateral">
        <div class="marca">Minhas Finanças</div>
        <nav class="menu">
          ${TELAS.map((t) => `
            <button class="menu-item${S.tela === t.id ? ' ativo' : ''}" data-acao="tela" data-tela="${t.id}" ${S.tela === t.id ? 'aria-current="page"' : ''}>
              ${icone(t.id)}<span>${t.nome}</span>
            </button>`).join('')}
        </nav>
      </aside>
      <div class="principal">
        <header class="topo">
          <div class="nav-mes">
            <button class="btn-icone" data-acao="mes" data-delta="-1" aria-label="Mês anterior">${icone('esquerda')}</button>
            <button class="mes-atual" data-acao="mes-hoje" title="Voltar para o mês atual">${nomeMes(S.mes)}</button>
            <button class="btn-icone" data-acao="mes" data-delta="1" aria-label="Próximo mês">${icone('direita')}</button>
          </div>
          <div class="topo-acoes">
            <button class="btn-icone" data-acao="ocultar" aria-label="${S.ocultar ? 'Mostrar valores' : 'Esconder valores'}" title="${S.ocultar ? 'Mostrar valores' : 'Esconder valores'}">${icone(S.ocultar ? 'olhoFechado' : 'olho')}</button>
            ${Store.remoto ? `
            <button class="btn-icone" data-acao="avisos" aria-label="Avisos de contas" title="Avisos de contas">${icone('sino')}</button>
            <button class="btn-icone" data-acao="seguranca" aria-label="Segurança" title="Segurança">${icone('escudo')}</button>
            <button class="btn-icone" data-acao="sair" aria-label="Sair" title="Sair">${icone('sair')}</button>` : ''}
          </div>
        </header>
        <main class="conteudo">${renderTela()}</main>
      </div>
    </div>
    ${S.tela === 'simular' ? '' : `<button class="fab" data-acao="novo-lancamento" aria-label="Novo lançamento">${icone('mais')}</button>`}`;
}

function renderTela() {
  switch (S.tela) {
    case 'lancamentos': return telaLancamentos();
    case 'cartoes': return telaCartoes();
    case 'simular': return telaSimular();
    case 'contas': return telaContas();
    case 'entradas': return telaEntradas();
    case 'metas': return telaMetas();
    default: return telaInicio();
  }
}

/* ---------- Início ---------- */
// A régua do mês: tudo o que entrou, dividido em para onde foi (gastos, contas, metas) e o que sobra.
function reguaDoMes(r) {
  const partes = [
    { classe: 'gastos', nome: 'Gastos e faturas', valor: r.gastos },
    { classe: 'contas', nome: 'Contas a pagar', valor: r.totalContasPendentes },
    { classe: 'metas', nome: 'Guardado nas metas', valor: Math.max(0, r.guardado) },
    { classe: 'sobra', nome: r.saldo < 0 ? 'Falta para fechar o mês' : 'Sobra', valor: Math.abs(r.saldo) },
  ].filter((p) => p.valor > 0);
  const negativo = r.saldo < 0;
  const descricao = partes.map((p) => `${p.nome}: ${dinheiro(p.valor)}`).join(', ');
  return `
    <section class="mes-resumo">
      <p class="mes-rotulo">${negativo ? 'Pelo previsto, faltam' : 'Sobra prevista'} em ${nomeMes(S.mes, false)}</p>
      <p class="mes-saldo${negativo ? ' negativo' : ''}">${dinheiro(Math.abs(r.saldo))}</p>
      <div class="regua${negativo ? ' estourou' : ''}" role="img" aria-label="Entrou ${dinheiro(r.totalReceitas)}. ${esc(descricao)}">
        ${partes.map((p) => `<span class="seg ${p.classe}${negativo && p.classe === 'sobra' ? ' falta' : ''}" style="flex-grow:${Math.round(p.valor * 100)}"></span>`).join('')}
      </div>
      <dl class="regua-legenda">
        <div><dt><i class="amostra entrou"></i>Entrou</dt><dd>${dinheiro(r.totalReceitas)}</dd></div>
        ${partes.map((p) => `<div><dt><i class="amostra ${p.classe}${negativo && p.classe === 'sobra' ? ' falta' : ''}"></i>${p.nome}</dt><dd>${dinheiro(p.valor)}</dd></div>`).join('')}
      </dl>
      ${r.aPagar ? `<p class="mes-nota">Ainda falta pagar <strong>${dinheiro(r.aPagar)}</strong> este mês, entre faturas e contas.</p>` : ''}
    </section>`;
}

function gerarAlertas(r) {
  const d = S.dados;
  const lista = [];
  for (const f of faturasAtrasadas(d, r.parcelas)) {
    lista.push({ nivel: 'perigo', texto: `Fatura ${esc(f.cartao.nome)} de ${nomeMes(f.comp, false)} venceu ${quando(diasAte(f.vencimento))}: faltam ${dinheiro(f.aPagar)}` });
  }
  for (const k of [somarMeses(compAtual(), -1), compAtual(), somarMeses(compAtual(), 1)]) {
    for (const c of d.cartoes) {
      const f = fatura(d, c, k, r.parcelas);
      const dias = diasAte(f.vencimento);
      if (f.aPagar > 0 && dias >= 0 && dias <= 5) {
        lista.push({ nivel: 'aviso', texto: `Fatura ${esc(c.nome)} vence ${quando(dias)}: faltam ${dinheiro(f.aPagar)}` });
      }
    }
  }
  for (const k of [somarMeses(compAtual(), -1), compAtual()]) {
    for (const x of contasDoMes(d, k)) {
      const dias = diasAte(x.vencimento);
      if (x.status === 'vencida') lista.push({ nivel: 'perigo', texto: `${esc(x.conta.descricao)} venceu ${quando(dias)} e não foi marcada como paga` });
      else if (!x.pagamento && dias <= 3) lista.push({ nivel: 'aviso', texto: `${esc(x.conta.descricao)} vence ${quando(dias)}: ${dinheiro(x.conta.valor)}` });
    }
  }
  for (const c of d.cartoes) {
    const usado = limiteUsado(d, c, r.parcelas);
    const p = pct(usado, Number(c.limite));
    if (p >= 80) lista.push({ nivel: p >= 100 ? 'perigo' : 'aviso', texto: `Você já usou ${p}% do limite do ${esc(c.nome)}. Restam ${dinheiro(Number(c.limite) - usado)}` });
  }
  if (r.saldo < 0) lista.push({ nivel: 'perigo', texto: `Pelo previsto, ${nomeMes(r.comp, false)} fecha no negativo` });
  return lista;
}

function telaInicio() {
  const d = S.dados;
  const r = resumoMes(d, S.mes);
  const vazio = !d.lancamentos.length && !d.cartoes.length && !d.contas_fixas.length && !d.metas.length;
  if (vazio) {
    return `
      <section class="boas-vindas cartao-base">
        <h2>Vamos começar</h2>
        <p class="sutil">Alguns passos e o painel já começa a te mostrar para onde vai o dinheiro.</p>
        <ol class="passos">
          <li><button class="link" data-acao="novo-cartao">Cadastre seus cartões</button> com limite, dia de fechamento e de vencimento.</li>
          <li><button class="link" data-acao="novo-lancamento">Lance seu salário e seus gastos</button> pelo botão <strong>+</strong>.</li>
          <li><button class="link" data-acao="nova-meta">Crie uma meta</button> para juntar dinheiro: viagem, reserva, um objetivo seu.</li>
        </ol>
      </section>`;
  }

  const alertas = gerarAlertas(r);
  const atrasadas = S.mes === compAtual() ? faturasAtrasadas(d, r.parcelas) : [];
  const vencimentos = [
    ...atrasadas.map((f) => ({ tipo: 'fatura', data: f.vencimento, item: f })),
    // Uma fatura atrasada do próprio mês já veio em "atrasadas": não repete.
    ...r.faturas.filter((f) => f.total > 0 && !atrasadas.some((x) => x.cartao.id === f.cartao.id && x.comp === f.comp))
      .map((f) => ({ tipo: 'fatura', data: f.vencimento, item: f })),
    ...r.contas.map((c) => ({ tipo: 'conta', data: c.vencimento, item: c })),
  ].sort((a, b) => a.data.localeCompare(b.data));

  const categorias = Object.entries(r.porCategoria).sort((a, b) => b[1] - a[1]);
  const maiorGasto = categorias[0]?.[1] || 0;
  return `
    ${reguaDoMes(r)}

    ${alertas.length ? `
    <section class="bloco">
      <h2>Atenção</h2>
      <ul class="alertas">${alertas.map((a) => `<li class="alerta ${a.nivel}">${a.texto}</li>`).join('')}</ul>
    </section>` : ''}

    <div class="grade-2">
      <section class="bloco">
        <div class="bloco-topo"><h2>Vencimentos</h2></div>
        ${vencimentos.length ? `<ul class="lista">${vencimentos.map(linhaVencimento).join('')}</ul>`
    : '<p class="vazio">Nada para pagar neste mês.</p>'}
      </section>

      <section class="bloco">
        <div class="bloco-topo"><h2>Cartões</h2><button class="link" data-acao="tela" data-tela="cartoes">Ver faturas</button></div>
        ${d.cartoes.length ? d.cartoes.map((c) => resumoLimite(c, limiteUsado(d, c, r.parcelas))).join('')
    : '<p class="vazio">Nenhum cartão. <button class="link" data-acao="novo-cartao">Cadastrar</button></p>'}
      </section>
    </div>

    <div class="grade-2">
      <section class="bloco">
        <h2>Para onde foi o dinheiro</h2>
        ${r.totalComprasCredito ? `<p class="sutil pequeno">Inclui ${dinheiro(r.totalComprasCredito)} comprados no crédito este mês (eles são pagos nas faturas do cartão).</p>` : ''}
        ${categorias.length ? `<ul class="categorias">${categorias.map(([id, valor]) => `
          <li>
            <div class="cat-linha"><span>${esc(categoria(id).nome)}</span><strong>${dinheiro(valor)}</strong></div>
            <div class="barra"><span style="width:${pct(valor, maiorGasto)}%"></span></div>
          </li>`).join('')}</ul>` : '<p class="vazio">Nenhum gasto neste mês ainda.</p>'}
      </section>

      <section class="bloco">
        <div class="bloco-topo"><h2>Metas</h2><button class="link" data-acao="tela" data-tela="metas">Ver metas</button></div>
        ${d.metas.length ? d.metas.map((m) => {
    const guardado = guardadoNaMeta(d, m.id);
    const p = pct(guardado, Number(m.alvo));
    return `
          <div class="mini-cartao">
            <div class="mini-topo"><span class="bolinha" style="background:${esc(m.cor)}"></span><strong>${esc(m.nome)}</strong><span class="sutil">${p}%</span></div>
            <div class="barra"><span style="width:${p}%; background:${esc(m.cor)}"></span></div>
            <div class="mini-rodape sutil"><span>${dinheiro(guardado)} de ${dinheiro(m.alvo)}</span><span>${guardado >= m.alvo ? 'alcançada' : `faltam ${dinheiro(m.alvo - guardado)}`}</span></div>
          </div>`;
  }).join('') : '<p class="vazio">Nenhuma meta ainda. <button class="link" data-acao="nova-meta">Criar meta</button></p>'}
      </section>
    </div>`;
}

// Limite total, quanto já gastou e quanto sobra, num formato só, usado no início e nos cartões.
function resumoLimite(c, usado) {
  const limite = Number(c.limite);
  const p = pct(usado, limite);
  return `
    <div class="mini-cartao">
      <div class="mini-topo"><span class="bolinha" style="background:${esc(c.cor)}"></span><strong>${esc(c.nome)}</strong><span class="sutil">limite ${dinheiro(limite)}</span></div>
      <div class="barra"><span class="${corBarra(p)}" style="width:${p}%"></span></div>
      <div class="limite-numeros">
        <div><span class="rotulo">Gastei</span><strong>${dinheiro(usado)}</strong></div>
        <div><span class="rotulo">Disponível</span><strong class="${limite - usado < 0 ? 'perigo-texto' : 'positivo'}">${dinheiro(limite - usado)}</strong></div>
      </div>
    </div>`;
}

function linhaVencimento({ tipo, item }) {
  const dias = diasAte(item.vencimento);
  const pago = item.status === 'paga';
  const chip = pago ? '<span class="chip ok">paga</span>'
    : item.status === 'vencida' ? `<span class="chip perigo">venceu ${quando(dias)}</span>`
      : `<span class="chip ${dias <= 3 ? 'aviso' : ''}">vence ${quando(dias)}</span>`;
  const rotuloBotao = pago ? 'Desmarcar pagamento' : tipo === 'fatura' && item.parcial ? 'Pagar o restante' : 'Marcar como paga';
  if (tipo === 'fatura') {
    return `
      <li class="linha${pago ? ' feito' : ''}">
        <span class="bolinha" style="background:${esc(item.cartao.cor)}"></span>
        <div class="linha-texto"><strong>Fatura ${esc(item.cartao.nome)}</strong><span class="sutil">${nomeMes(item.comp, false)}, dia ${dataCurta(item.vencimento)} ${chip}${item.parcial ? ` já pago ${dinheiro(item.pago)}` : ''}</span></div>
        <div class="linha-valor direita"><strong>${dinheiro(item.parcial ? item.aPagar : item.total)}</strong>${item.parcial ? '<span class="sutil pequeno">falta</span>' : ''}</div>
        <button class="btn-check${pago ? ' marcado' : ''}" data-acao="pagar-fatura" data-cartao="${item.cartao.id}" data-comp="${item.comp}" aria-label="${rotuloBotao}" title="${rotuloBotao}">${icone('check')}</button>
      </li>`;
  }
  return `
    <li class="linha clicavel${pago ? ' feito' : ''}" data-acao="editar-conta" data-id="${item.conta.id}" tabindex="0" role="button">
      <span class="bolinha" style="background:var(--roxo)"></span>
      <div class="linha-texto"><strong>${esc(item.conta.descricao)}</strong><span class="sutil">dia ${dataCurta(item.vencimento)} ${chip}</span></div>
      <strong class="linha-valor">${dinheiro(item.conta.valor)}</strong>
      <button class="btn-check${pago ? ' marcado' : ''}" data-acao="pagar-conta" data-conta="${item.conta.id}" data-comp="${item.comp}" aria-label="${rotuloBotao}" title="${rotuloBotao}">${icone('check')}</button>
    </li>`;
}

/* ---------- Lançamentos ---------- */
function telaLancamentos() {
  const d = S.dados;
  const r = resumoMes(d, S.mes);
  // Tudo o que foi feito neste mês, pela data. Compras no cartão aparecem no mês da compra,
  // com a fatura em que caem; parcelas de compras de outros meses ficam numa lista à parte.
  let itens = [...r.receitas, ...r.avulsas, ...r.comprasCredito]
    .map((l) => ({ lanc: l, valor: Number(l.valor), data: l.data }));
  const parcelasAntigas = r.parcelasMes.filter((p) => p.lanc.data.slice(0, 7) !== S.mes);
  if (S.filtro === 'receitas') itens = itens.filter((i) => i.lanc.tipo === 'receita');
  else if (S.filtro !== 'todos') itens = itens.filter((i) => formaDe(i.lanc) === S.filtro);
  const busca = S.busca.trim().toLowerCase();
  if (busca) itens = itens.filter((i) => `${i.lanc.descricao} ${categoria(i.lanc.categoria).nome}`.toLowerCase().includes(busca));
  itens.sort((a, b) => b.data.localeCompare(a.data) || String(b.lanc.created_at).localeCompare(String(a.lanc.created_at)));

  const entradas = soma(itens.filter((i) => i.lanc.tipo === 'receita').map((i) => i.valor));
  const saidas = soma(itens.filter((i) => i.lanc.tipo === 'despesa').map((i) => i.valor));
  const filtros = [['todos', 'Tudo'], ...FORMAS.map((f) => [f.id, f.nome]), ['receitas', 'Entradas']];

  return `
    <section class="bloco">
      <div class="bloco-topo"><h2>Lançamentos de ${nomeMes(S.mes, false)}</h2></div>
      <div class="filtros">
        ${filtros.map(([id, nome]) => `<button class="filtro${S.filtro === id ? ' ativo' : ''}" data-acao="filtro" data-filtro="${id}">${nome}</button>`).join('')}
      </div>
      <input class="busca" type="search" placeholder="Buscar por descrição ou categoria" value="${esc(S.busca)}" data-campo="busca" aria-label="Buscar">
      <div class="totais"><span>Entradas <strong class="positivo">${dinheiro(entradas)}</strong></span><span>Saídas <strong>${dinheiro(saidas)}</strong></span></div>
      ${itens.length ? `<div class="dias">${porDia(itens).map(([dia, doDia]) => `
        <section class="dia">
          <h3 class="dia-titulo"><span>${nomeDia(dia)}</span><span class="dia-total">${dinheiro(Math.abs(soma(doDia.map((i) => (i.lanc.tipo === 'receita' ? 1 : -1) * i.valor))))}</span></h3>
          <ul class="lista">${doDia.map(linhaLancamento).join('')}</ul>
        </section>`).join('')}</div>` : `<p class="vazio">Nada lançado em ${nomeMes(S.mes, false)}${S.filtro !== 'todos' || busca ? ' com esse filtro' : ''}. <button class="link" data-acao="novo-lancamento">Lançar agora</button></p>`}
      ${parcelasAntigas.length && ['todos', 'credito'].includes(S.filtro) && !busca ? `
      <details class="parcelas-antigas">
        <summary>Parcelas de compras de outros meses que vencem em ${nomeMes(S.mes, false)} (${dinheiro(soma(parcelasAntigas.map((p) => p.valor)))})</summary>
        <ul class="lista compacta">${parcelasAntigas.map((p) => `
          <li class="linha clicavel" data-acao="editar-lancamento" data-id="${p.lanc.id}" tabindex="0" role="button">
            <span class="bolinha" style="background:${esc(p.cartao.cor)}"></span>
            <div class="linha-texto"><strong>${esc(p.lanc.descricao)}</strong><span class="sutil">${esc(p.cartao.nome)}, parcela ${p.numero} de ${p.total}, comprado em ${dataCurta(p.lanc.data)}/${p.lanc.data.slice(2, 4)}</span></div>
            <strong class="linha-valor">− ${dinheiro(p.valor)}</strong>
          </li>`).join('')}
        </ul>
      </details>` : ''}
    </section>`;
}

/* ---------- Marcar gasto como pago ---------- */
// Pix/débito/dinheiro: marcação simples (coluna "pago").
// Crédito: pago quando todas as parcelas estão quitadas na fatura.
function lancamentoPago(l) {
  const cartao = S.dados.cartoes.find((c) => c.id === l.cartao_id);
  if (!cartao) return l.pago === true;
  return parcelasDe(l, cartao).every((p) => parcelaQuitada(S.dados, p));
}

function bolinhaPago(l) {
  const pago = lancamentoPago(l);
  const rotulo = pago ? 'Desmarcar como pago' : 'Marcar como pago';
  return `<button class="btn-check pequeno${pago ? ' marcado' : ''}" style="--cor-check:${esc(corDoLancamento(l))}" data-acao="marcar-lancamento" data-id="${l.id}" aria-label="${rotulo}" title="${rotulo}">${icone('check')}</button>`;
}

async function alternarPagoLancamento(id) {
  const d = S.dados;
  const l = d.lancamentos.find((x) => x.id === id);
  if (!l) return;
  const cartao = d.cartoes.find((c) => c.id === l.cartao_id);
  const pago = lancamentoPago(l);
  if (!cartao) {
    await executar(() => Store.atualizar('lancamentos', id, { pago: !pago }), pago ? 'Desmarcado' : 'Marcado como pago');
    return;
  }
  const parcelas = parcelasDe(l, cartao);
  await executar(async () => {
    if (pago) {
      // Desfaz só o que foi marcado compra a compra (fatura inteira paga continua paga).
      for (const p of parcelas) {
        const x = pagamentoItem(d, p);
        if (x) await Store.remover('itens_pagos', x.id);
      }
    } else {
      for (const p of parcelas) {
        if (!parcelaQuitada(d, p)) await Store.inserir('itens_pagos', { lancamento_id: id, competencia: p.competencia, pago_em: hoje() });
      }
    }
  }, pago ? 'Compra voltou para pendente' : 'Compra marcada como paga');
}

/* ---------- Entradas ---------- */
function telaEntradas() {
  const d = S.dados;
  const r = resumoMes(d, S.mes);
  const lista = [...r.receitas].sort((a, b) => b.data.localeCompare(a.data));
  const porCategoria = {};
  for (const l of lista) porCategoria[l.categoria] = soma([porCategoria[l.categoria], l.valor]);
  const categorias = Object.entries(porCategoria).sort((a, b) => b[1] - a[1]);
  // Últimos 6 meses, para comparar.
  const meses = Array.from({ length: 6 }, (_, i) => somarMeses(S.mes, i - 5));
  const totais = meses.map((comp) => soma(d.lancamentos.filter((l) => l.tipo === 'receita' && l.data.slice(0, 7) === comp).map((l) => l.valor)));
  const maior = Math.max(...totais, 1);
  const anterior = totais[4];
  const variacao = anterior ? Math.round(((r.totalReceitas - anterior) / anterior) * 100) : null;

  return `
    <div class="bloco-topo"><h2>Entradas de ${nomeMes(S.mes, false)}</h2><button class="btn" data-acao="nova-entrada">${icone('mais')} Nova entrada</button></div>
    <section class="destaque entrada">
      <span class="rotulo">Total que entrou em ${nomeMes(S.mes, false)}</span>
      <strong class="valor-grande">${dinheiro(r.totalReceitas)}</strong>
      <span class="conta-saldo">${variacao === null ? 'Sem entradas no mês anterior para comparar.' : `${variacao >= 0 ? '+' : ''}${variacao}% em relação a ${nomeMes(meses[4], false)} (${dinheiro(anterior)})`}</span>
    </section>
    <section class="numeros dois">
      <div class="numero"><span class="rotulo">Já saiu do que entrou</span><strong>${dinheiro(soma([r.totalReceitas, -r.saldo]))}</strong></div>
      <div class="numero"><span class="rotulo">Sobra prevista</span><strong class="${r.saldo < 0 ? 'perigo-texto' : 'positivo'}">${dinheiro(r.saldo)}</strong></div>
    </section>
    <div class="grade-2">
      <section class="bloco">
        <h2>Lista</h2>
        ${lista.length ? `<ul class="lista">${lista.map((l) => `
          <li class="linha clicavel" data-acao="editar-lancamento" data-id="${l.id}" tabindex="0" role="button">
            <span class="bolinha" style="background:var(--positivo)"></span>
            <div class="linha-texto"><strong>${esc(l.descricao)}</strong><span class="sutil">${esc(categoria(l.categoria).nome)}, dia ${dataCurta(l.data)}</span></div>
            <strong class="linha-valor positivo">+ ${dinheiro(l.valor)}</strong>
          </li>`).join('')}</ul>` : `<p class="vazio">Nenhuma entrada em ${nomeMes(S.mes, false)}. <button class="link" data-acao="nova-entrada">Lançar uma entrada</button></p>`}
      </section>
      <section class="bloco">
        <h2>De onde veio</h2>
        ${categorias.length ? `<ul class="categorias">${categorias.map(([id, valor]) => `
          <li>
            <div class="cat-linha"><span>${esc(categoria(id).nome)}</span><strong>${dinheiro(valor)}</strong></div>
            <div class="barra"><span class="verde" style="width:${pct(valor, r.totalReceitas)}%"></span></div>
          </li>`).join('')}</ul>` : '<p class="vazio">Nada por aqui ainda.</p>'}
        <h3 class="subtitulo">Últimos 6 meses</h3>
        <ul class="colunas-meses">${meses.map((comp, i) => `
          <li class="${comp === S.mes ? 'atual' : ''}">
            <span class="coluna-valor">${S.ocultar ? '•••' : NUMERO.format(totais[i]).replace(/,\d\d$/, '')}</span>
            <span class="coluna" style="height:${Math.max(4, Math.round((totais[i] / maior) * 100))}%"></span>
            <span class="coluna-mes">${MESES[Number(comp.slice(5)) - 1].slice(0, 3)}</span>
          </li>`).join('')}
        </ul>
      </section>
    </div>`;
}

// Agrupa por dia, do mais recente para o mais antigo.
function porDia(itens) {
  const grupos = new Map();
  for (const i of itens) {
    if (!grupos.has(i.data)) grupos.set(i.data, []);
    grupos.get(i.data).push(i);
  }
  return [...grupos.entries()];
}

const DIAS_SEMANA = ['domingo', 'segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado'];
function nomeDia(iso) {
  const dias = diasAte(iso);
  const [a, m, d] = iso.split('-').map(Number);
  const extenso = `${d} de ${MESES[m - 1]}`;
  if (dias === 0) return `Hoje, ${extenso}`;
  if (dias === -1) return `Ontem, ${extenso}`;
  const semana = DIAS_SEMANA[new Date(a, m - 1, d).getDay()];
  return `${semana[0].toUpperCase()}${semana.slice(1)}, ${extenso}`;
}

function linhaLancamento(i) {
  const l = i.lanc;
  const cartao = S.dados.cartoes.find((c) => c.id === l.cartao_id);
  let detalhe = categoria(l.categoria).nome;
  if (l.tipo === 'despesa' && cartao) {
    const ps = parcelasDe(l, cartao);
    detalhe = ps.length > 1
      ? `${cartao.nome}, ${ps.length}x de ${dinheiro(ps[ps.length - 1].valor)} (${mesCurto(ps[0].competencia)} a ${mesCurto(ps[ps.length - 1].competencia)})`
      : `${cartao.nome}, fatura de ${mesCurto(ps[0].competencia)}`;
  } else if (l.tipo === 'despesa') detalhe += `, ${nomeForma(formaDe(l)).toLowerCase()}`;
  const receita = l.tipo === 'receita';
  return `
    <li class="linha clicavel${!receita && lancamentoPago(l) ? ' feito' : ''}" data-acao="editar-lancamento" data-id="${l.id}" tabindex="0" role="button">
      ${receita ? `<span class="bolinha" style="background:${esc(corDoLancamento(l))}"></span>` : bolinhaPago(l)}
      <div class="linha-texto"><strong>${esc(l.descricao)}</strong><span class="sutil">${esc(detalhe)}</span></div>
      <strong class="linha-valor ${receita ? 'positivo' : ''}">${receita ? '+' : '−'} ${dinheiro(i.valor)}</strong>
    </li>`;
}

/* ---------- Cartões ---------- */
const NOME_STATUS = { aberta: 'aberta', fechada: 'fechada', vencida: 'vencida', paga: 'paga', vazia: 'sem gastos' };

function telaCartoes() {
  const d = S.dados;
  const parcelas = todasParcelas(d);
  const todosParcelamentos = parcelamentos(d, parcelas).filter((p) => p.ativo);
  return `
    <div class="bloco-topo"><h2>Cartões e faturas de ${nomeMes(S.mes, false)}</h2><button class="btn" data-acao="novo-cartao">${icone('mais')} Novo cartão</button></div>
    ${d.cartoes.length ? `<div class="grade-cartoes">${d.cartoes.map((c) => {
    const f = fatura(d, c, S.mes, parcelas);
    const usado = limiteUsado(d, c, parcelas);
    const limite = Number(c.limite);
    const p = pct(usado, limite);
    const doCartao = todosParcelamentos.filter((x) => x.cartao.id === c.id);
    const chipStatus = { paga: 'ok', vencida: 'perigo', fechada: 'aviso' }[f.status] || '';
    return `
      <article class="cartao-fatura">
        <div class="plastico" style="--cor:${esc(c.cor)}">
          <div class="plastico-topo"><strong>${esc(c.nome)}</strong><button class="btn-icone claro" data-acao="editar-cartao" data-id="${c.id}" aria-label="Editar cartão">${icone('editar')}</button></div>
          <span class="rotulo">Fatura de ${nomeMes(S.mes, false)}</span>
          <strong class="valor-grande">${dinheiro(f.total)}</strong>
          ${f.parcial ? `<span class="plastico-pago">Já pago ${dinheiro(f.pago)}, falta ${dinheiro(f.aPagar)}</span>` : ''}
          <span class="plastico-datas">Fecha ${dataCurta(f.fechamento)}, vence ${dataCurta(f.vencimento)}</span>
        </div>
        <div class="fatura-corpo">
          <div class="fatura-status">
            <span class="chip ${chipStatus}">${NOME_STATUS[f.status]}</span>
            ${f.total > 0 ? `<button class="btn ${f.status === 'paga' ? '' : 'primario'}" data-acao="pagar-fatura" data-cartao="${c.id}" data-comp="${S.mes}">${f.status === 'paga' ? 'Desfazer pagamento' : f.parcial ? `Pagar o restante (${dinheiro(f.aPagar)})` : 'Marcar como paga'}</button>` : ''}
            ${f.aPagar > 0 ? `<button class="btn" data-acao="pagar-valor" data-cartao="${c.id}" data-comp="${S.mes}">Pagar um valor</button>` : ''}
          </div>
          ${f.avulsos.length ? `
          <ul class="lista compacta avulsos">${f.avulsos.map((x) => `
            <li class="linha">
              <div class="linha-texto"><strong>Pagamento avulso</strong><span class="sutil">${dataCurta(x.data)}/${x.data.slice(0, 4)}</span></div>
              <strong class="linha-valor positivo">${dinheiro(x.valor)}</strong>
              <button class="link perigo-texto" data-acao="excluir-avulso" data-id="${x.id}">apagar</button>
            </li>`).join('')}
          </ul>` : ''}
          <div class="limite-tres">
            <div><span class="rotulo">Limite</span><strong>${dinheiro(limite)}</strong></div>
            <div><span class="rotulo">Gastei</span><strong>${dinheiro(usado)}</strong></div>
            <div><span class="rotulo">Disponível</span><strong class="${limite - usado < 0 ? 'perigo-texto' : 'positivo'}">${dinheiro(limite - usado)}</strong></div>
          </div>
          <div class="barra"><span class="${corBarra(p)}" style="width:${p}%"></span></div>
          <p class="sutil pequeno">${p}% do limite em uso. Melhor dia de compra: dia ${c.fechamento}.</p>

          ${doCartao.length ? `
          <h3 class="subtitulo">Parcelamentos</h3>
          <ul class="lista compacta">${doCartao.map((x) => `
            <li class="linha clicavel" data-acao="editar-lancamento" data-id="${x.lanc.id}" tabindex="0" role="button">
              <div class="linha-texto">
                <strong>${esc(x.lanc.descricao)}</strong>
                <span class="sutil">${x.total}x de ${dinheiro(x.valorParcela)}, ${x.pagas} de ${x.total} pagas, termina em ${mesCurto(x.ultima)}</span>
              </div>
              <div class="linha-valor direita"><strong>${dinheiro(x.restante)}</strong><span class="sutil pequeno">falta</span></div>
            </li>`).join('')}
          </ul>` : ''}

          ${f.itens.length ? `
          <details ${f.itens.length <= 8 || f.parcial ? 'open' : ''}>
            <summary>Compras desta fatura (${f.itens.length})</summary>
            <p class="sutil pequeno">Toque no ✓ de uma compra para marcar só ela como paga.</p>
            <ul class="lista compacta">${f.itens.map((i) => {
    const quitada = parcelaQuitada(d, i);
    const travada = Boolean(f.pagamento) || i.prePaga; // paga pela fatura inteira ou informada no lançamento
    const rotulo = quitada ? 'Desmarcar esta compra' : 'Marcar esta compra como paga';
    return `
              <li class="linha clicavel${quitada ? ' feito' : ''}" data-acao="editar-lancamento" data-id="${i.lanc.id}" tabindex="0" role="button">
                <div class="linha-texto"><strong>${esc(i.lanc.descricao)}</strong><span class="sutil">${dataCurta(i.lanc.data)}, ${i.total > 1 ? `parcela ${i.numero} de ${i.total}` : 'à vista'}</span></div>
                <strong class="linha-valor">${dinheiro(i.valor)}</strong>
                <button class="btn-check pequeno${quitada ? ' marcado' : ''}" data-acao="pagar-item" data-lanc="${i.lanc.id}" data-comp="${i.competencia}" aria-label="${rotulo}" title="${travada ? 'Já está paga' : rotulo}" ${travada ? 'disabled' : ''}>${icone('check')}</button>
              </li>`;
  }).join('')}
            </ul>
            ${f.parcial ? `<div class="totais"><span>Pago <strong class="positivo">${dinheiro(f.pago)}</strong></span><span>Falta <strong class="alerta-texto">${dinheiro(f.aPagar)}</strong></span></div>` : ''}
          </details>` : ''}
        </div>
      </article>`;
  }).join('')}</div>` : '<section class="bloco"><p class="vazio">Cadastre seus cartões para acompanhar faturas e limite.</p></section>'}`;
}

/* ---------- Simular ---------- */
// Faturas do cartão que ainda têm valor a pagar (atrasadas e dos próximos meses).
function faturasEmAberto(cartao) {
  const parcelas = todasParcelas(S.dados);
  const comps = new Set(parcelas.filter((p) => p.cartao.id === cartao.id).map((p) => p.competencia));
  return [...comps].sort()
    .map((comp) => fatura(S.dados, cartao, comp, parcelas))
    .filter((f) => f.aPagar > 0 && f.comp <= somarMeses(compAtual(), 2));
}

function normalizarSimulacao() {
  const sim = S.sim;
  const cartoes = S.dados.cartoes;
  if (!cartoes.some((c) => c.id === sim.cartao)) sim.cartao = cartoes[0]?.id || '';
  if (!sim.data) sim.data = hoje();
  if (sim.tipo === 'pagamento' && sim.cartao) {
    const abertas = faturasEmAberto(cartoes.find((c) => c.id === sim.cartao));
    if (!abertas.some((f) => f.comp === sim.fatura)) sim.fatura = abertas[0]?.comp || '';
  }
}

function telaSimular() {
  normalizarSimulacao();
  const sim = S.sim;
  const cartoes = S.dados.cartoes;
  const usaCartao = sim.tipo !== 'avista';
  const cartao = cartoes.find((c) => c.id === sim.cartao);
  const abertas = sim.tipo === 'pagamento' && cartao ? faturasEmAberto(cartao) : [];
  return `
    <div class="bloco-topo"><h2>Simular</h2></div>
    <section class="bloco">
      <p class="sutil">Veja como ficariam seu limite e seus meses <strong>antes</strong> de comprar ou pagar. Nada aqui é salvo.</p>
      <form class="form form-sim" data-sim onsubmit="return false">
        ${segmentado('tipo', [['credito', 'Crédito'], ['avista', 'Pix/débito'], ['pagamento', 'Pagar fatura']], sim.tipo, 'O que simular')}
        <div class="duas">
          <label>Valor<input name="valor" inputmode="numeric" data-dinheiro placeholder="0,00" value="${esc(sim.valor)}"></label>
          ${sim.tipo === 'pagamento' ? '' : `<label>Data<input type="date" name="data" value="${esc(sim.data)}"></label>`}
        </div>
        ${usaCartao ? (cartoes.length ? `
        <label>Cartão<select name="cartao">
          ${cartoes.map((c) => `<option value="${c.id}" ${c.id === sim.cartao ? 'selected' : ''}>${esc(c.nome)}</option>`).join('')}
        </select></label>` : '<p class="dica">Cadastre um cartão para simular no crédito.</p>') : ''}
        ${sim.tipo === 'credito' && cartoes.length ? `
        ${segmentado('modo', [['avista', 'À vista'], ['parcelado', 'Parcelado']], sim.modo, 'À vista ou parcelado')}
        ${sim.modo === 'parcelado' ? `<label>Em quantas parcelas?<input type="number" name="parcelas" min="2" max="48" value="${esc(sim.parcelas)}"></label>` : ''}` : ''}
        ${sim.tipo === 'pagamento' && cartao ? (abertas.length ? `
        <label>Qual fatura<select name="fatura">
          ${abertas.map((f) => `<option value="${f.comp}" ${f.comp === sim.fatura ? 'selected' : ''}>${nomeMes(f.comp)} (falta ${BRL.format(f.aPagar)})</option>`).join('')}
        </select></label>` : '<p class="dica">Este cartão não tem fatura com valor a pagar.</p>') : ''}
      </form>
    </section>
    <section class="bloco" data-sim-resultado>${resultadoSimulacao()}</section>`;
}

// Uma linha da tabela da simulação: rótulo | hoje | depois (colorido se mudou).
function linhaSim(rotulo, antes, depois, { inverter = false } = {}) {
  const mudou = Math.abs(antes - depois) >= 0.005;
  const piorou = inverter ? depois > antes : depois < antes;
  const cor = !mudou ? '' : piorou ? (depois < 0 ? 'perigo-texto' : 'alerta-texto') : 'positivo';
  return `<span class="sim-rotulo">${rotulo}</span>
    <span class="sim-valor sutil">${dinheiro(antes)}</span>
    <strong class="sim-valor ${cor}">${dinheiro(depois)}</strong>`;
}
const tabelaSim = (rotuloDepois, linhas) => `
  <div class="sim-tabela">
    <span></span><span class="sim-cab">Hoje</span><span class="sim-cab">${rotuloDepois}</span>
    ${linhas}
  </div>`;

function resultadoSimulacao() {
  const d = S.dados;
  const sim = S.sim;
  const valor = lerValor(sim.valor);
  if (!(valor > 0)) return '<p class="vazio">Digite um valor para ver a simulação.</p>';
  const cartao = d.cartoes.find((c) => c.id === sim.cartao);

  if (sim.tipo === 'avista') {
    const comp = (sim.data || hoje()).slice(0, 7);
    const d2 = { ...d, lancamentos: [...d.lancamentos, { id: '__simulacao', tipo: 'despesa', descricao: 'Simulação', valor, data: sim.data || hoje(), categoria: 'outros', forma: 'pix', cartao_id: null, parcelas: 1 }] };
    const antes = resumoMes(d, comp).saldo;
    const depois = resumoMes(d2, comp).saldo;
    return `
      <h2>Resultado</h2>
      <div class="sim-mes">
        <strong class="sim-mes-nome">${nomeMes(comp)}</strong>
        ${tabelaSim('Com a compra', linhaSim('Sobra no mês', antes, depois))}
      </div>
      ${depois < 0 ? `<p class="alerta perigo">Com essa compra, ${nomeMes(comp, false)} fecharia no negativo.</p>` : `<p class="alerta ok">Ainda sobrariam ${dinheiro(depois)} no mês.</p>`}`;
  }

  if (!cartao) return '<p class="vazio">Escolha um cartão.</p>';
  const limite = Number(cartao.limite);
  let d2;
  let resumo = '';
  let meses = [];
  let rotuloDepois = 'Com a compra';
  if (sim.tipo === 'credito') {
    const n = sim.modo === 'parcelado' ? Math.max(2, Math.min(48, Number(sim.parcelas) || 2)) : 1;
    const compra = { id: '__simulacao', tipo: 'despesa', descricao: 'Simulação', valor, data: sim.data || hoje(), categoria: 'outros', forma: 'credito', cartao_id: cartao.id, parcelas: n, parcelas_pagas: 0 };
    d2 = { ...d, lancamentos: [...d.lancamentos, compra] };
    const ps = parcelasDe(compra, cartao);
    const primeira = ps[0].competencia;
    const ultima = ps[ps.length - 1].competencia;
    resumo = n > 1
      ? `<strong>${n}x de ${dinheiro(ps[ps.length - 1].valor)}</strong>, da fatura de ${mesCurto(primeira)} até ${mesCurto(ultima)}.`
      : `<strong>${dinheiro(valor)} à vista</strong>, na fatura de ${mesCurto(primeira)}.`;
    const fim = somarMeses(ultima, 1);
    for (let k = compAtual(); k <= fim && meses.length < 13; k = somarMeses(k, 1)) meses.push(k);
  } else {
    if (!sim.fatura) return '<p class="vazio">Este cartão não tem fatura com valor a pagar.</p>';
    rotuloDepois = 'Pagando';
    d2 = { ...d, pagamentos_fatura: [...(d.pagamentos_fatura || []), { id: '__simulacao', cartao_id: cartao.id, competencia: sim.fatura, valor, data: hoje() }] };
    const f = fatura(d, cartao, sim.fatura);
    resumo = valor >= f.aPagar
      ? `Paga a fatura de ${mesCurto(sim.fatura)} inteira (faltavam ${dinheiro(f.aPagar)}).`
      : `Abate ${dinheiro(valor)} da fatura de ${mesCurto(sim.fatura)}. Ainda faltariam <strong>${dinheiro(f.aPagar - valor)}</strong>.`;
    meses = [compAtual(), somarMeses(compAtual(), 1), somarMeses(compAtual(), 2)];
  }

  const p1 = todasParcelas(d);
  const p2 = todasParcelas(d2);
  const livreAgora = soma([limite, -limiteUsado(d, cartao, p1)]);
  const livreDepois = soma([limite, -limiteUsado(d2, cartao, p2)]);
  return `
    <h2>Resultado</h2>
    <p class="sim-resumo">${resumo}</p>
    <div class="sim-destaque">
      <strong class="sim-titulo">Limite livre no ${esc(cartao.nome)}</strong>
      ${tabelaSim(rotuloDepois, linhaSim('Agora', livreAgora, livreDepois))}
    </div>
    ${livreDepois < 0 ? `<p class="alerta perigo">Passaria do limite em ${dinheiro(-livreDepois)}. O cartão pode recusar a compra.</p>` : ''}
    <h3 class="subtitulo">Mês a mês</h3>
    <ul class="sim-meses">${meses.map((comp) => `
      <li class="sim-mes">
        <strong class="sim-mes-nome">${nomeMes(comp)}</strong>
        ${tabelaSim(rotuloDepois, [
    linhaSim('Fatura a pagar', fatura(d, cartao, comp, p1).aPagar, fatura(d2, cartao, comp, p2).aPagar, { inverter: true }),
    linhaSim('Limite livre', soma([limite, -limiteUsadoEm(d, cartao, comp, p1)]), soma([limite, -limiteUsadoEm(d2, cartao, comp, p2)])),
    linhaSim('Sobra no mês', resumoMes(d, comp).saldo, resumoMes(d2, comp).saldo),
  ].join(''))}
      </li>`).join('')}</ul>
    <p class="sutil pequeno">"Limite livre" de cada mês considera que as faturas anteriores foram pagas em dia. "Sobra no mês" é o saldo previsto: entradas menos gastos, faturas, contas e metas.</p>`;
}

function atualizarSimulacao(form, recriar) {
  const sim = S.sim;
  for (const campo of ['tipo', 'valor', 'cartao', 'data', 'modo', 'parcelas', 'fatura']) {
    const el = form.elements[campo];
    if (el) sim[campo] = el.value;
  }
  if (recriar) {
    render();
    return;
  }
  const alvo = $('[data-sim-resultado]');
  if (alvo) alvo.innerHTML = resultadoSimulacao();
}

/* ---------- Contas fixas ---------- */
function telaContas() {
  const contas = contasDoMes(S.dados, S.mes);
  const pagas = soma(contas.filter((c) => c.pagamento).map((c) => c.conta.valor));
  const pendentes = soma(contas.filter((c) => !c.pagamento).map((c) => c.conta.valor));
  const inativas = S.dados.contas_fixas.filter((c) => c.ativa === false);
  return `
    <div class="bloco-topo"><h2>Contas fixas de ${nomeMes(S.mes, false)}</h2><button class="btn" data-acao="nova-conta">${icone('mais')} Nova conta</button></div>
    <section class="bloco">
      <div class="totais"><span>Pagas <strong class="positivo">${dinheiro(pagas)}</strong></span><span>Falta pagar <strong class="${pendentes ? 'alerta-texto' : ''}">${dinheiro(pendentes)}</strong></span></div>
      ${contas.length ? `<ul class="lista">${contas.map((c) => linhaVencimento({ tipo: 'conta', item: c })).join('')}</ul>`
    : '<p class="vazio">Cadastre aqui o que você paga todo mês: aluguel, internet, academia, celular…</p>'}
      <p class="sutil pequeno">Ao marcar uma conta como paga, ela entra nos lançamentos do mês. Toque na conta para editar.</p>
    </section>
    ${inativas.length ? `
    <section class="bloco">
      <h2>Pausadas</h2>
      <ul class="lista">${inativas.map((c) => `
        <li class="linha clicavel feito" data-acao="editar-conta" data-id="${c.id}" tabindex="0" role="button">
          <div class="linha-texto"><strong>${esc(c.descricao)}</strong><span class="sutil">dia ${c.dia}</span></div>
          <strong class="linha-valor">${dinheiro(c.valor)}</strong>
        </li>`).join('')}</ul>
    </section>` : ''}`;
}

/* ---------- Metas de economia ---------- */
function infoMeta(m) {
  const guardado = guardadoNaMeta(S.dados, m.id);
  const alvo = Number(m.alvo);
  const falta = Math.max(0, soma([alvo, -guardado]));
  let plano = '';
  if (falta === 0) plano = 'Meta alcançada!';
  else if (m.prazo) {
    const meses = mesesEntre(compAtual(), m.prazo) + 1;
    plano = meses > 0
      ? `Guarde ${dinheiro(falta / meses)} por mês para chegar até ${mesCurto(m.prazo)} (${meses} ${meses === 1 ? 'mês' : 'meses'}).`
      : `O prazo (${mesCurto(m.prazo)}) já passou. Faltam ${dinheiro(falta)}.`;
  }
  return { guardado, alvo, falta, plano, p: pct(guardado, alvo) };
}

function telaMetas() {
  const d = S.dados;
  const totalGuardado = soma(d.metas.map((m) => guardadoNaMeta(d, m.id)));
  return `
    <div class="bloco-topo"><h2>Metas para juntar dinheiro</h2><button class="btn" data-acao="nova-meta">${icone('mais')} Nova meta</button></div>
    ${d.metas.length ? `
    <section class="numeros dois">
      <div class="numero"><span class="rotulo">Total guardado</span><strong class="roxo-texto">${dinheiro(totalGuardado)}</strong></div>
      <div class="numero"><span class="rotulo">Guardado em ${nomeMes(S.mes, false)}</span><strong>${dinheiro(guardadoNoMes(d, S.mes))}</strong></div>
    </section>
    <div class="grade-cartoes">${d.metas.map((m) => {
    const x = infoMeta(m);
    const movimentos = d.metas_movimentos.filter((mv) => mv.meta_id === m.id)
      .sort((a, b) => b.data.localeCompare(a.data) || String(b.created_at).localeCompare(String(a.created_at)));
    return `
      <article class="meta-cartao" style="--cor:${esc(m.cor)}">
        <div class="meta-topo">
          <div><strong class="meta-nome">${esc(m.nome)}</strong><span class="sutil pequeno">${m.prazo ? `até ${mesCurto(m.prazo)}` : 'sem prazo'}</span></div>
          <button class="btn-icone" data-acao="editar-meta" data-id="${m.id}" aria-label="Editar meta">${icone('editar')}</button>
        </div>
        <div class="meta-valores"><strong>${dinheiro(x.guardado)}</strong><span class="sutil">de ${dinheiro(x.alvo)}</span></div>
        <div class="barra grossa"><span style="width:${x.p}%; background:var(--cor)"></span></div>
        <div class="mini-rodape sutil"><span>${x.p}%</span><span>${x.falta ? `faltam ${dinheiro(x.falta)}` : 'completa'}</span></div>
        ${x.plano ? `<p class="meta-plano">${x.plano}</p>` : ''}
        <div class="botoes">
          <button class="btn primario" data-acao="guardar" data-id="${m.id}">Guardar</button>
          <button class="btn" data-acao="retirar" data-id="${m.id}" ${x.guardado > 0 ? '' : 'disabled'}>Retirar</button>
        </div>
        ${movimentos.length ? `
        <details>
          <summary>Histórico (${movimentos.length})</summary>
          <ul class="lista compacta">${movimentos.map((mv) => `
            <li class="linha">
              <div class="linha-texto"><strong>${mv.valor > 0 ? 'Guardou' : 'Retirou'}</strong><span class="sutil">${dataCurta(mv.data)}/${mv.data.slice(0, 4)}</span></div>
              <strong class="linha-valor ${mv.valor > 0 ? 'positivo' : ''}">${mv.valor > 0 ? '+' : '−'} ${dinheiro(Math.abs(mv.valor))}</strong>
              <button class="link perigo-texto" data-acao="excluir-movimento" data-id="${mv.id}">apagar</button>
            </li>`).join('')}
          </ul>
        </details>` : ''}
      </article>`;
  }).join('')}</div>` : `
    <section class="bloco">
      <p class="vazio">Crie uma meta (reserva de emergência, viagem, um celular novo…), diga quanto quer juntar e até quando. O app calcula quanto guardar por mês.</p>
      <button class="btn primario" data-acao="nova-meta">Criar primeira meta</button>
    </section>`}

    <section class="bloco">
      <h2>Backup</h2>
      <p class="sutil">Baixe uma cópia dos seus dados ou importe uma cópia (por exemplo, para levar o que lançou no modo de teste para a sua conta).</p>
      <div class="botoes">
        <button class="btn" data-acao="exportar">Baixar backup</button>
        <label class="btn">Importar backup<input type="file" accept="application/json,.json" data-campo="importar" hidden></label>
      </div>
    </section>`;
}

/* ---------- Formulários ---------- */
const modal = () => $('#modal');

function abrirModal(html) {
  const m = modal();
  m.innerHTML = html;
  m.showModal();
  m.querySelector('[autofocus]')?.focus();
}

function opcoesCategoria(tipo, atual) {
  return CATEGORIAS[tipo].map((c) => `<option value="${c.id}" ${c.id === atual ? 'selected' : ''}>${c.nome}</option>`).join('');
}

const segmentado = (nome, opcoes, atual, rotulo) => `
  <div class="segmentado" style="--n:${opcoes.length}" role="radiogroup" aria-label="${rotulo}">
    ${opcoes.map(([valor, texto]) => `<label><input type="radio" name="${nome}" value="${valor}" ${valor === atual ? 'checked' : ''}><span>${texto}</span></label>`).join('')}
  </div>`;

// l = lançamento existente (edição); padrao = valores iniciais de um novo (ex.: { tipo: 'receita' }).
function formLancamento(l, padrao = {}) {
  const tipo = l?.tipo || padrao.tipo || 'despesa';
  const forma = l ? formaDe(l) || 'pix' : 'pix';
  const parcelado = (l?.parcelas || 1) > 1;
  const cartoes = S.dados.cartoes;
  const dataPadrao = S.mes === compAtual() ? hoje() : `${S.mes}-01`;
  abrirModal(`
    <form class="form" data-form="lancamento" data-id="${l?.id || ''}">
      <h2>${l ? 'Editar lançamento' : padrao.tipo === 'receita' ? 'Nova entrada' : 'Novo lançamento'}</h2>
      ${segmentado('tipo', [['despesa', 'Gasto'], ['receita', 'Entrada']], tipo, 'Tipo')}
      <label>Valor${l?.parcelas > 1 ? ' total da compra' : ''}<input name="valor" inputmode="numeric" data-dinheiro placeholder="0,00" value="${valorParaCampo(l?.valor)}" required autofocus></label>
      <label>Descrição<input name="descricao" placeholder="Ex.: Mercado do mês" value="${esc(l?.descricao)}" maxlength="80" required></label>
      <div class="duas">
        <label>Data<input type="date" name="data" value="${l?.data || dataPadrao}" required></label>
        <label>Categoria<select name="categoria">${opcoesCategoria(tipo, l?.categoria)}</select></label>
      </div>

      <div class="so-despesa">
        <span class="rotulo-campo">Como pagou?</span>
        ${segmentado('forma', FORMAS.map((f) => [f.id, f.nome]), forma, 'Forma de pagamento')}
      </div>

      <div class="so-credito grupo-credito">
        ${cartoes.length ? `
        <label>Cartão<select name="cartao_id">
          ${cartoes.map((c) => `<option value="${c.id}" ${c.id === l?.cartao_id ? 'selected' : ''}>${esc(c.nome)}</option>`).join('')}
        </select></label>
        <span class="rotulo-campo">À vista ou parcelado?</span>
        ${segmentado('modo', [['avista', 'À vista'], ['parcelado', 'Parcelado']], parcelado ? 'parcelado' : 'avista', 'À vista ou parcelado')}
        <div class="duas so-parcelado">
          <label>Em quantas parcelas?<input type="number" name="parcelas" min="2" max="48" value="${parcelado ? l.parcelas : 2}"></label>
          <label>Já paguei quantas?<input type="number" name="parcelas_pagas" min="0" max="47" value="${parcelado ? l.parcelas_pagas || 0 : 0}"></label>
        </div>
        <div class="resumo-compra" data-resumo></div>
        ` : `<p class="dica">Você ainda não tem cartões. <button type="button" class="link" data-acao="novo-cartao">Cadastre um cartão</button> para lançar no crédito.</p>`}
      </div>

      <div class="form-acoes">
        ${l ? '<button type="button" class="btn perigo-texto" data-acao="excluir-lancamento">Excluir</button>' : ''}
        <button type="button" class="btn" data-acao="fechar">Cancelar</button>
        <button type="submit" class="btn primario">Salvar</button>
      </div>
    </form>`);
  atualizarFormLancamento();
}

// Mostra/esconde os campos conforme as escolhas e recalcula parcelas e limite em tempo real.
function atualizarFormLancamento() {
  const f = modal().querySelector('[data-form="lancamento"]');
  if (!f) return;
  const despesa = f.tipo.value === 'despesa';
  const credito = despesa && f.forma.value === 'credito';
  f.querySelector('.so-despesa').hidden = !despesa;
  f.querySelector('.so-credito').hidden = !credito;
  const resumo = f.querySelector('[data-resumo]');
  if (!credito || !resumo) return;

  const parcelado = f.modo.value === 'parcelado';
  f.querySelector('.so-parcelado').hidden = !parcelado;
  const cartao = S.dados.cartoes.find((c) => c.id === f.cartao_id.value);
  const valor = lerValor(f.valor.value);
  const n = parcelado ? Math.max(2, Math.min(48, Number(f.parcelas.value) || 2)) : 1;
  const jaPagas = parcelado ? Math.max(0, Math.min(n - 1, Number(f.parcelas_pagas.value) || 0)) : 0;
  if (!cartao || !f.data.value) { resumo.innerHTML = ''; return; }

  // Não conta a própria compra quando estiver editando.
  const outras = todasParcelas(S.dados).filter((p) => p.lanc.id !== f.dataset.id);
  const disponivel = soma([cartao.limite, -limiteUsado(S.dados, cartao, outras)]);
  const primeira = compPrimeiraParcela(f.data.value, cartao);
  const ultima = somarMeses(primeira, n - 1);
  const linhas = [];
  if (valor > 0) {
    const ps = parcelasDe({ valor, parcelas: n, data: f.data.value }, cartao);
    const valorParcela = ps[ps.length - 1].valor;
    const diferente = ps[0].valor !== valorParcela;
    linhas.push(n > 1
      ? `<strong>${n}x de ${BRL.format(valorParcela)}</strong>${diferente ? ` <span class="sutil">(a 1ª fica ${BRL.format(ps[0].valor)} por causa dos centavos)</span>` : ''}`
      : `<strong>${BRL.format(valor)} à vista</strong>`);
  }
  linhas.push(n > 1
    ? `1ª parcela na fatura de ${mesCurto(primeira)} (vence ${dataCurta(dataNoMes(primeira, cartao.vencimento))}). <strong>Termina de pagar em ${mesCurto(ultima)}.</strong>`
    : `Entra na fatura de ${mesCurto(primeira)} (vence ${dataCurta(dataNoMes(primeira, cartao.vencimento))}).`);
  linhas.push(`Limite disponível no ${esc(cartao.nome)}: <strong>${BRL.format(disponivel)}</strong>`);
  // Parcelas que ainda vão ocupar o limite (tira as informadas como já pagas).
  const restante = valor > 0
    ? soma(parcelasDe({ valor, parcelas: n, data: f.data.value, parcelas_pagas: jaPagas }, cartao).filter((p) => !p.prePaga).map((p) => p.valor))
    : 0;
  if (jaPagas > 0 && valor > 0) {
    linhas.push(`${jaPagas} já ${jaPagas === 1 ? 'paga' : 'pagas'}: faltam <strong>${n - jaPagas} parcelas (${BRL.format(restante)})</strong>.`);
  }
  if (valor > 0) {
    const depois = soma([disponivel, -restante]);
    linhas.push(`Depois desta compra: <strong class="${depois < 0 ? 'perigo-texto' : ''}">${BRL.format(depois)}</strong>${depois < 0 ? ' (passa do limite)' : ''}`);
  }
  resumo.innerHTML = linhas.map((x) => `<p>${x}</p>`).join('');
}

const CORES = ['#7c3aed', '#a21caf', '#db2777', '#4f46e5', '#6d28d9', '#1e1b4b', '#0e7490', '#ea580c'];
const seletorCores = (atual) => `
  <fieldset class="cores"><legend>Cor</legend>
    ${CORES.map((k) => `<label><input type="radio" name="cor" value="${k}" ${k === atual ? 'checked' : ''}><span style="background:${k}"></span></label>`).join('')}
  </fieldset>`;

function formCartao(c) {
  abrirModal(`
    <form class="form" data-form="cartao" data-id="${c?.id || ''}">
      <h2>${c ? 'Editar cartão' : 'Novo cartão'}</h2>
      <label>Nome do cartão<input name="nome" placeholder="Ex.: Nubank" value="${esc(c?.nome)}" maxlength="40" required autofocus></label>
      <label>Limite total<input name="limite" inputmode="numeric" data-dinheiro placeholder="0,00" value="${valorParaCampo(c?.limite)}" required></label>
      <div class="duas">
        <label>Dia que fecha<input type="number" name="fechamento" min="1" max="31" value="${c?.fechamento || ''}" required></label>
        <label>Dia que vence<input type="number" name="vencimento" min="1" max="31" value="${c?.vencimento || ''}" required></label>
      </div>
      ${seletorCores(c?.cor || CORES[S.dados.cartoes.length % CORES.length])}
      <p class="dica">O dia de fechamento e o de vencimento aparecem no app do banco ou na fatura.</p>
      <div class="form-acoes">
        ${c ? '<button type="button" class="btn perigo-texto" data-acao="excluir-cartao">Excluir</button>' : ''}
        <button type="button" class="btn" data-acao="fechar">Cancelar</button>
        <button type="submit" class="btn primario">Salvar</button>
      </div>
    </form>`);
}

function formConta(c) {
  abrirModal(`
    <form class="form" data-form="conta" data-id="${c?.id || ''}">
      <h2>${c ? 'Editar conta fixa' : 'Nova conta fixa'}</h2>
      <label>Descrição<input name="descricao" placeholder="Ex.: Internet" value="${esc(c?.descricao)}" maxlength="60" required autofocus></label>
      <div class="duas">
        <label>Valor por mês<input name="valor" inputmode="numeric" data-dinheiro placeholder="0,00" value="${valorParaCampo(c?.valor)}" required></label>
        <label>Dia que vence<input type="number" name="dia" min="1" max="31" value="${c?.dia || ''}" required></label>
      </div>
      <label>Categoria<select name="categoria">${opcoesCategoria('despesa', c?.categoria || 'contas')}</select></label>
      ${c ? `<label class="check"><input type="checkbox" name="ativa" ${c.ativa !== false ? 'checked' : ''}> Ativa (desmarque para pausar sem apagar o histórico)</label>` : ''}
      <div class="form-acoes">
        ${c ? '<button type="button" class="btn perigo-texto" data-acao="excluir-conta">Excluir</button>' : ''}
        <button type="button" class="btn" data-acao="fechar">Cancelar</button>
        <button type="submit" class="btn primario">Salvar</button>
      </div>
    </form>`);
}

function formMeta(m) {
  abrirModal(`
    <form class="form" data-form="meta" data-id="${m?.id || ''}">
      <h2>${m ? 'Editar meta' : 'Nova meta'}</h2>
      <label>Para que você quer juntar?<input name="nome" placeholder="Ex.: Viagem, reserva de emergência" value="${esc(m?.nome)}" maxlength="50" required autofocus></label>
      <div class="duas">
        <label>Quanto quer juntar<input name="alvo" inputmode="numeric" data-dinheiro placeholder="0,00" value="${valorParaCampo(m?.alvo)}" required></label>
        <label>Até quando (opcional)<input type="month" name="prazo" value="${m?.prazo || ''}" min="${compAtual()}"></label>
      </div>
      ${seletorCores(m?.cor || CORES[S.dados.metas.length % CORES.length])}
      <p class="dica">Com um prazo, o app mostra quanto guardar por mês.</p>
      <div class="form-acoes">
        ${m ? '<button type="button" class="btn perigo-texto" data-acao="excluir-meta">Excluir</button>' : ''}
        <button type="button" class="btn" data-acao="fechar">Cancelar</button>
        <button type="submit" class="btn primario">Salvar</button>
      </div>
    </form>`);
}

function formMovimento(meta, sinal) {
  const guardado = guardadoNaMeta(S.dados, meta.id);
  abrirModal(`
    <form class="form" data-form="movimento" data-meta="${meta.id}" data-sinal="${sinal}">
      <h2>${sinal > 0 ? 'Guardar em' : 'Retirar de'} "${esc(meta.nome)}"</h2>
      <p class="sutil">Guardado até agora: ${BRL.format(guardado)}</p>
      <div class="duas">
        <label>Valor<input name="valor" inputmode="numeric" data-dinheiro placeholder="0,00" required autofocus></label>
        <label>Data<input type="date" name="data" value="${hoje()}" required></label>
      </div>
      <div class="form-acoes">
        <button type="button" class="btn" data-acao="fechar">Cancelar</button>
        <button type="submit" class="btn primario">${sinal > 0 ? 'Guardar' : 'Retirar'}</button>
      </div>
    </form>`);
}

/* ---------- Avisos no celular (Web Push) ---------- */
const suportaPush = () => 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window;
const ehIphone = () => /iphone|ipad|ipod/i.test(navigator.userAgent);
const instalado = () => window.matchMedia('(display-mode: standalone)').matches || navigator.standalone === true;

function chaveVapid() {
  const base64 = window.CONFIG.VAPID_PUBLIC_KEY.replace(/-/g, '+').replace(/_/g, '/');
  const bruto = atob(base64 + '='.repeat((4 - (base64.length % 4)) % 4));
  return Uint8Array.from(bruto, (c) => c.charCodeAt(0));
}

async function inscricaoAtual() {
  const reg = await navigator.serviceWorker.ready;
  return reg.pushManager.getSubscription();
}

async function abrirAvisos() {
  const rodape = (botoes) => `<div class="form-acoes">${botoes}</div>`;
  const explicacao = '<p class="sutil">Todo dia às 8h, se alguma conta fixa ou fatura vencer <strong>hoje ou amanhã</strong>, chega uma notificação como: <em>"Amanhã vence: Game Pass — R$ 59,99"</em>.</p>';

  if (!suportaPush()) {
    abrirModal(`<div class="form"><h2>Avisos de contas</h2>${explicacao}
      <p class="alerta aviso">${ehIphone() && !instalado()
    ? 'No iPhone, primeiro adicione o app à tela de início (Safari → Compartilhar → Adicionar à Tela de Início), abra por lá e volte aqui. Precisa do iOS 16.4 ou mais novo.'
    : 'Este navegador não aceita notificações. Tente pelo Chrome (Android ou computador) ou pelo app instalado na tela de início.'}</p>
      ${rodape('<button type="button" class="btn primario" data-acao="fechar">Entendi</button>')}</div>`);
    return;
  }

  const inscricao = await inscricaoAtual();
  const bloqueado = Notification.permission === 'denied';
  abrirModal(`<div class="form"><h2>Avisos de contas</h2>
    ${inscricao ? `<p class="status-seguranca ativo">${icone('sino')} Ativados neste aparelho</p>` : '<p class="status-seguranca">Desativados neste aparelho</p>'}
    ${explicacao}
    <p class="sutil pequeno">Cada aparelho (celular, notebook) é ativado separadamente.</p>
    ${bloqueado ? '<p class="alerta aviso">As notificações deste site estão bloqueadas no navegador. Libere nas configurações do site (cadeado ao lado do endereço) e tente de novo.</p>' : ''}
    ${rodape(inscricao
    ? `<button type="button" class="btn perigo-texto" data-acao="desativar-avisos">Desativar</button>
         <button type="button" class="btn" data-acao="testar-avisos">Enviar teste</button>
         <button type="button" class="btn primario" data-acao="fechar">Fechar</button>`
    : `<button type="button" class="btn" data-acao="fechar">Agora não</button>
         <button type="button" class="btn primario" data-acao="ativar-avisos" ${bloqueado ? 'disabled' : ''}>Ativar neste aparelho</button>`)}
  </div>`);
}

async function ativarAvisos() {
  try {
    const permissao = await Notification.requestPermission();
    if (permissao !== 'granted') return toast('Sem permissão, não dá para mandar os avisos.', true);
    const reg = await navigator.serviceWorker.ready;
    const inscricao = await reg.pushManager.getSubscription()
      || await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: chaveVapid() });
    await Store.salvarInscricaoPush(inscricao);
    toast('Avisos ativados neste aparelho');
    abrirAvisos();
  } catch (e) {
    console.error(e);
    toast(e.message || 'Não consegui ativar os avisos.', true);
  }
}

async function desativarAvisos() {
  try {
    const inscricao = await inscricaoAtual();
    if (inscricao) {
      await Store.removerInscricaoPush(inscricao.endpoint);
      await inscricao.unsubscribe();
    }
    toast('Avisos desativados neste aparelho');
    abrirAvisos();
  } catch (e) {
    toast(e.message, true);
  }
}

async function testarAvisos() {
  try {
    await Store.enviarAvisoTeste();
    toast('Teste enviado. A notificação deve chegar em alguns segundos.');
  } catch (e) {
    toast(e.message, true);
  }
}

/* ---------- Segurança: verificação em duas etapas ---------- */
async function abrirSeguranca() {
  abrirModal('<div class="form"><h2>Segurança</h2><p class="sutil">Carregando…</p></div>');
  try {
    const ativo = await Store.doisFatoresAtivo();
    abrirModal(`
      <div class="form">
        <h2>Verificação em duas etapas</h2>
        ${ativo ? `
          <p class="status-seguranca ativo">${icone('escudo')} Ativada</p>
          <p class="sutil">Para entrar, além da senha, o app pede o código do seu app autenticador. Sem ele, o banco recusa o acesso aos seus dados.</p>
          <div class="form-acoes">
            <button type="button" class="btn perigo-texto" data-acao="desativar-2fa">Desativar</button>
            <button type="button" class="btn primario" data-acao="fechar">Fechar</button>
          </div>` : `
          <p class="status-seguranca">Desativada</p>
          <p class="sutil">Com ela ligada, quem descobrir sua senha ainda não consegue entrar: o login também pede um código que muda a cada 30 segundos, gerado no seu celular.</p>
          <p class="sutil">Você vai precisar de um app autenticador, como <strong>Google Authenticator</strong> ou <strong>Microsoft Authenticator</strong> (grátis na loja do celular).</p>
          <div class="form-acoes">
            <button type="button" class="btn" data-acao="fechar">Agora não</button>
            <button type="button" class="btn primario" data-acao="ativar-2fa">Ativar</button>
          </div>`}
      </div>`);
  } catch (e) {
    modal().close();
    toast(e.message, true);
  }
}

async function ativarDoisFatores() {
  try {
    const { id, qr, segredo } = await Store.iniciarDoisFatores();
    abrirModal(`
      <form class="form" data-form="ativar-2fa" data-fator="${esc(id)}">
        <h2>Ativar verificação</h2>
        <ol class="passos">
          <li>Abra o app autenticador e toque em <strong>+</strong> (adicionar conta).</li>
          <li>Escaneie o QR code:
            <div class="qr"><img src="${esc(qr)}" alt="QR code para o app autenticador" width="180" height="180"></div>
            <span class="sutil pequeno">Está no celular e não dá para escanear? Escolha "inserir chave" no app e digite:</span>
            <code class="segredo">${esc(segredo)}</code>
          </li>
          <li>Digite o código de 6 dígitos que apareceu no app:</li>
        </ol>
        <label class="sem-rotulo">${campoCodigo}</label>
        <div class="form-acoes">
          <button type="button" class="btn" data-acao="fechar">Cancelar</button>
          <button type="submit" class="btn primario">Confirmar e ativar</button>
        </div>
      </form>`);
  } catch (e) {
    toast(e.message, true);
  }
}

async function salvarForm(f) {
  if (f.dataset.form === 'avulso') {
    const valor = lerValor(f.valor.value);
    if (!(valor > 0)) return toast('Informe um valor maior que zero.', true);
    const cartao = S.dados.cartoes.find((c) => c.id === f.dataset.cartao);
    const falta = fatura(S.dados, cartao, f.dataset.comp).aPagar;
    if (valor > falta) return toast(`O valor é maior do que falta pagar (${BRL.format(falta)}).`, true);
    const ok = await executar(() => Store.inserir('pagamentos_fatura', {
      cartao_id: f.dataset.cartao, competencia: f.dataset.comp, valor, data: f.data.value,
    }), 'Pagamento registrado');
    if (ok) modal().close();
    return;
  }

  if (f.dataset.form === 'ativar-2fa') {
    try {
      await Store.confirmarDoisFatores(f.dataset.fator, lerCodigo(f.codigo));
      modal().close();
      toast('Verificação em duas etapas ativada');
    } catch (e) {
      toast(e.message, true);
    }
    return;
  }

  const id = f.dataset.id;
  const salvar = async (tabela, obj, msg) => {
    if (await executar(() => (id ? Store.atualizar(tabela, id, obj) : Store.inserir(tabela, obj)), msg)) modal().close();
  };

  if (f.dataset.form === 'lancamento') {
    const tipo = f.tipo.value;
    const valor = lerValor(f.valor.value);
    if (!(valor > 0)) return toast('Informe um valor maior que zero.', true);
    const forma = tipo === 'despesa' ? f.forma.value : null;
    const credito = forma === 'credito';
    if (credito && !f.cartao_id) return toast('Cadastre um cartão para lançar no crédito.', true);
    const parcelado = credito && f.modo.value === 'parcelado';
    return salvar('lancamentos', {
      tipo,
      valor,
      descricao: f.descricao.value.trim(),
      data: f.data.value,
      categoria: f.categoria.value,
      forma,
      cartao_id: credito ? f.cartao_id.value : null,
      parcelas: parcelado ? Math.max(2, Math.min(48, Number(f.parcelas.value) || 2)) : 1,
      parcelas_pagas: parcelado ? Math.max(0, Math.min(Number(f.parcelas.value) - 1, Number(f.parcelas_pagas.value) || 0)) : 0,
    }, 'Lançamento salvo');
  }

  if (f.dataset.form === 'cartao') {
    const limite = lerValor(f.limite.value);
    if (!(limite >= 0)) return toast('Informe o limite do cartão.', true);
    return salvar('cartoes', {
      nome: f.nome.value.trim(),
      limite,
      fechamento: Number(f.fechamento.value),
      vencimento: Number(f.vencimento.value),
      cor: f.cor.value,
    }, 'Cartão salvo');
  }

  if (f.dataset.form === 'conta') {
    const valor = lerValor(f.valor.value);
    if (!(valor > 0)) return toast('Informe um valor maior que zero.', true);
    const obj = { descricao: f.descricao.value.trim(), valor, dia: Number(f.dia.value), categoria: f.categoria.value };
    if (id) obj.ativa = f.ativa.checked;
    else obj.desde = S.mes < compAtual() ? S.mes : compAtual();
    return salvar('contas_fixas', obj, 'Conta salva');
  }

  if (f.dataset.form === 'meta') {
    const alvo = lerValor(f.alvo.value);
    if (!(alvo > 0)) return toast('Informe quanto quer juntar.', true);
    return salvar('metas', { nome: f.nome.value.trim(), alvo, prazo: f.prazo.value || null, cor: f.cor.value }, 'Meta salva');
  }

  if (f.dataset.form === 'movimento') {
    const valor = lerValor(f.valor.value);
    if (!(valor > 0)) return toast('Informe um valor maior que zero.', true);
    const sinal = Number(f.dataset.sinal);
    if (sinal < 0 && valor > guardadoNaMeta(S.dados, f.dataset.meta)) return toast('Não dá para retirar mais do que está guardado.', true);
    if (await executar(() => Store.inserir('metas_movimentos', { meta_id: f.dataset.meta, valor: sinal * valor, data: f.data.value }), sinal > 0 ? 'Valor guardado' : 'Valor retirado')) modal().close();
  }
}

/* ---------- Pagamentos ---------- */
async function alternarFatura(cartaoId, comp) {
  const d = S.dados;
  const cartao = d.cartoes.find((c) => c.id === cartaoId);
  const f = fatura(d, cartao, comp);
  if (f.status === 'paga') {
    // Desfaz tudo: o pagamento da fatura inteira, as compras marcadas uma a uma e os valores avulsos.
    if (!confirm('Desfazer o pagamento desta fatura? As compras marcadas e os valores avulsos pagos voltam a ficar pendentes.')) return;
    const itensPagos = f.itens.map((i) => pagamentoItem(d, i)).filter(Boolean);
    await executar(async () => {
      if (f.pagamento) await Store.remover('faturas_pagas', f.pagamento.id);
      for (const x of itensPagos) await Store.remover('itens_pagos', x.id);
      for (const x of f.avulsos) await Store.remover('pagamentos_fatura', x.id);
    }, 'Pagamento desfeito');
    return;
  }
  await executar(
    () => Store.inserir('faturas_pagas', { cartao_id: cartaoId, competencia: comp, pago_em: hoje() }),
    f.parcial ? 'Restante da fatura pago' : 'Fatura marcada como paga',
  );
}

function formPagarValor(cartaoId, comp) {
  const cartao = S.dados.cartoes.find((c) => c.id === cartaoId);
  const f = fatura(S.dados, cartao, comp);
  abrirModal(`
    <form class="form" data-form="avulso" data-cartao="${cartaoId}" data-comp="${comp}">
      <h2>Pagar um valor da fatura</h2>
      <p class="sutil">Fatura ${esc(cartao.nome)} de ${nomeMes(comp, false)}: falta <strong>${BRL.format(f.aPagar)}</strong>.</p>
      <div class="duas">
        <label>Quanto você pagou<input name="valor" inputmode="numeric" data-dinheiro placeholder="0,00" required autofocus></label>
        <label>Quando<input type="date" name="data" value="${hoje()}" required></label>
      </div>
      <p class="dica">O valor abate o que falta da fatura e libera o mesmo valor no limite do cartão.</p>
      <div class="form-acoes">
        <button type="button" class="btn" data-acao="fechar">Cancelar</button>
        <button type="submit" class="btn primario">Registrar pagamento</button>
      </div>
    </form>`);
}

async function alternarItem(lancamentoId, comp) {
  const existente = S.dados.itens_pagos.find((x) => x.lancamento_id === lancamentoId && x.competencia === comp);
  await executar(
    () => (existente ? Store.remover('itens_pagos', existente.id) : Store.inserir('itens_pagos', { lancamento_id: lancamentoId, competencia: comp, pago_em: hoje() })),
    existente ? 'Compra voltou para pendente' : 'Compra marcada como paga',
  );
}

async function alternarConta(contaId, comp) {
  const d = S.dados;
  const pago = d.contas_pagas.find((p) => p.conta_id === contaId && p.competencia === comp);
  const conta = d.contas_fixas.find((c) => c.id === contaId);
  await executar(async () => {
    if (pago) {
      if (pago.lancamento_id && d.lancamentos.some((l) => l.id === pago.lancamento_id)) await Store.remover('lancamentos', pago.lancamento_id);
      else await Store.remover('contas_pagas', pago.id);
      return;
    }
    const data = hoje().slice(0, 7) === comp ? hoje() : dataNoMes(comp, conta.dia);
    const lanc = await Store.inserir('lancamentos', {
      tipo: 'despesa', descricao: conta.descricao, valor: Number(conta.valor), data, categoria: conta.categoria, forma: 'pix', cartao_id: null, parcelas: 1,
    });
    await Store.inserir('contas_pagas', { conta_id: contaId, competencia: comp, lancamento_id: lanc.id });
  }, pago ? 'Pagamento desfeito' : 'Conta marcada como paga');
}

function exportar() {
  const blob = new Blob([JSON.stringify({ app: 'minhas-financas', versao: 2, gerado_em: new Date().toISOString(), ...S.dados }, null, 2)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `financas-backup-${hoje()}.json`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

async function importar(arquivo) {
  try {
    const backup = JSON.parse(await arquivo.text());
    if (backup.app !== 'minhas-financas') throw new Error('Esse arquivo não é um backup deste app.');
    if (!confirm('Importar esse backup? Os registros dele serão somados aos que você já tem.')) return;
    await executar(() => Store.importar(backup), 'Backup importado');
  } catch (e) {
    toast(e.message || 'Não consegui ler o arquivo.', true);
  }
}

/* ---------- Eventos ---------- */
const encontrar = (tabela, id) => S.dados[tabela].find((x) => x.id === id);

document.addEventListener('click', async (e) => {
  const el = e.target.closest('[data-acao]');
  if (!el) return;
  const { acao } = el.dataset;
  const form = el.closest('form[data-form]');

  switch (acao) {
    case 'tela': S.tela = el.dataset.tela; render(); window.scrollTo(0, 0); break;
    case 'mes': S.mes = somarMeses(S.mes, Number(el.dataset.delta)); render(); break;
    case 'mes-hoje': S.mes = compAtual(); render(); break;
    case 'ocultar': S.ocultar = !S.ocultar; gravarPreferencia('financas-ocultar', S.ocultar); render(); break;
    case 'sair': await Store.sair(); telaLogin(); break;
    case 'filtro': S.filtro = el.dataset.filtro; render(); break;
    case 'novo-lancamento': formLancamento(); break;
    case 'novo-cartao': formCartao(); break;
    case 'nova-conta': formConta(); break;
    case 'nova-entrada': formLancamento(null, { tipo: 'receita' }); break;
    case 'nova-meta': formMeta(); break;
    case 'editar-lancamento': formLancamento(encontrar('lancamentos', el.dataset.id)); break;
    case 'editar-cartao': formCartao(encontrar('cartoes', el.dataset.id)); break;
    case 'editar-conta': formConta(encontrar('contas_fixas', el.dataset.id)); break;
    case 'editar-meta': formMeta(encontrar('metas', el.dataset.id)); break;
    case 'guardar': formMovimento(encontrar('metas', el.dataset.id), 1); break;
    case 'retirar': formMovimento(encontrar('metas', el.dataset.id), -1); break;
    case 'fechar': modal().close(); break;
    case 'pagar-fatura': alternarFatura(el.dataset.cartao, el.dataset.comp); break;
    case 'exportar': exportar(); break;
    case 'seguranca': abrirSeguranca(); break;
    case 'avisos': abrirAvisos(); break;
    case 'ativar-avisos': ativarAvisos(); break;
    case 'desativar-avisos': desativarAvisos(); break;
    case 'testar-avisos': testarAvisos(); break;
    case 'pagar-valor': formPagarValor(el.dataset.cartao, el.dataset.comp); break;
    case 'excluir-avulso':
      if (confirm('Apagar este pagamento avulso?')) executar(() => Store.remover('pagamentos_fatura', el.dataset.id), 'Pagamento apagado');
      break;
    case 'ativar-2fa': ativarDoisFatores(); break;
    case 'desativar-2fa':
      if (!confirm('Desativar a verificação em duas etapas? O login volta a pedir só a senha.')) break;
      try {
        await Store.desativarDoisFatores();
        modal().close();
        toast('Verificação em duas etapas desativada');
      } catch (err) {
        toast(err.message, true);
      }
      break;
    case 'excluir-movimento':
      if (confirm('Apagar este registro da meta?')) executar(() => Store.remover('metas_movimentos', el.dataset.id), 'Registro apagado');
      break;
    case 'excluir-lancamento': {
      const l = encontrar('lancamentos', form.dataset.id);
      const aviso = l?.parcelas > 1 ? `Excluir "${l.descricao}" e todas as ${l.parcelas} parcelas?` : 'Excluir este lançamento?';
      if (confirm(aviso) && await executar(() => Store.remover('lancamentos', form.dataset.id), 'Lançamento excluído')) modal().close();
      break;
    }
    case 'excluir-cartao':
      if (confirm('Excluir este cartão? Todas as compras e faturas dele também serão apagadas.')
        && await executar(() => Store.remover('cartoes', form.dataset.id), 'Cartão excluído')) modal().close();
      break;
    case 'excluir-conta':
      if (confirm('Excluir esta conta fixa? Os pagamentos já lançados continuam nos lançamentos. Para só parar de cobrar, desmarque "Ativa".')
        && await executar(() => Store.remover('contas_fixas', form.dataset.id), 'Conta excluída')) modal().close();
      break;
    case 'excluir-meta':
      if (confirm('Excluir esta meta e todo o histórico dela?')
        && await executar(() => Store.remover('metas', form.dataset.id), 'Meta excluída')) modal().close();
      break;
    default: break;
  }
});

// Os botões de check ficam dentro de linhas clicáveis: o clique neles não pode abrir a edição.
document.addEventListener('click', (e) => {
  const check = e.target.closest('.btn-check');
  if (!check) return;
  e.stopImmediatePropagation();
  if (check.disabled) return;
  if (check.dataset.acao === 'pagar-fatura') alternarFatura(check.dataset.cartao, check.dataset.comp);
  else if (check.dataset.acao === 'pagar-item') alternarItem(check.dataset.lanc, check.dataset.comp);
  else if (check.dataset.acao === 'marcar-lancamento') alternarPagoLancamento(check.dataset.id);
  else alternarConta(check.dataset.conta, check.dataset.comp);
}, true);

document.addEventListener('keydown', (e) => {
  if ((e.key === 'Enter' || e.key === ' ') && e.target.matches('.clicavel[data-acao]')) {
    e.preventDefault();
    e.target.click();
  }
});

// Fase de captura: formata o valor antes de qualquer outro listener ler o campo.
document.addEventListener('input', (e) => {
  if (e.target.matches('input[data-dinheiro]')) mascaraDinheiro(e.target);
}, true);

document.addEventListener('input', (e) => {
  if (e.target.dataset.campo === 'busca') {
    S.busca = e.target.value;
    const pos = e.target.selectionStart;
    render();
    const campo = $('[data-campo="busca"]');
    campo.focus();
    campo.setSelectionRange(pos, pos);
  }
  if (e.target.closest('[data-form="lancamento"]')) atualizarFormLancamento();
  const sim = e.target.closest('[data-sim]');
  if (sim && e.target.matches('input:not([type=radio])')) atualizarSimulacao(sim, false);
});

document.addEventListener('change', (e) => {
  const f = e.target.closest('[data-form="lancamento"]');
  if (f && e.target.name === 'tipo') f.categoria.innerHTML = opcoesCategoria(e.target.value);
  if (f) atualizarFormLancamento();
  if (e.target.dataset.campo === 'importar' && e.target.files[0]) importar(e.target.files[0]);
  const sim = e.target.closest('[data-sim]');
  if (sim && e.target.matches('select, input[type=radio]')) atualizarSimulacao(sim, true);
});

document.addEventListener('submit', async (e) => {
  const f = e.target.closest('form[data-form]');
  if (!f) return;
  e.preventDefault();
  if (f.dataset.enviando) return; // já está salvando este formulário
  f.dataset.enviando = '1';
  const botao = f.querySelector('button[type=submit]');
  const texto = botao?.textContent;
  if (botao) { botao.disabled = true; botao.textContent = 'Salvando…'; }
  try {
    await salvarForm(f);
  } finally {
    delete f.dataset.enviando;
    if (botao?.isConnected) { botao.disabled = false; botao.textContent = texto; }
  }
});

// Fecha o formulário ao tocar fora dele.
modal().addEventListener('click', (e) => { if (e.target === modal()) modal().close(); });

/* ---------- Início do app ---------- */
async function iniciarApp() {
  $('#app').innerHTML = '<div class="carregando">Carregando…</div>';
  try {
    await recarregar();
    render();
  } catch (e) {
    console.error(e);
    $('#app').innerHTML = `<div class="carregando">Não foi possível carregar seus dados.<br><span class="sutil">${esc(e.message)}</span></div>`;
  }
}

// O service worker recebe as notificações; só funciona em https (ou localhost).
if ('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js').catch((e) => console.warn('Service worker:', e));

(async () => {
  Store.aoSair(() => telaLogin());
  try {
    if (!(await Store.usuario())) telaLogin();
    else if (await Store.precisaCodigo()) telaCodigo();
    else iniciarApp();
  } catch (e) {
    console.error(e);
    telaLogin();
  }
})();
