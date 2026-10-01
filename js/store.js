// Camada de dados: Supabase quando configurado, localStorage no modo de teste.
const TABELAS = ['cartoes', 'lancamentos', 'faturas_pagas', 'itens_pagos', 'pagamentos_fatura', 'contas_fixas', 'contas_pagas', 'metas', 'metas_movimentos'];

// Mesmas regras de "on delete cascade" do schema.sql, para o modo de teste.
const CASCATA = {
  cartoes: [['lancamentos', 'cartao_id'], ['faturas_pagas', 'cartao_id'], ['pagamentos_fatura', 'cartao_id']],
  contas_fixas: [['contas_pagas', 'conta_id']],
  lancamentos: [['contas_pagas', 'lancamento_id'], ['itens_pagos', 'lancamento_id']],
  metas: [['metas_movimentos', 'meta_id']],
};

const Store = (() => {
  const cfg = window.CONFIG || {};
  const remoto = Boolean(cfg.SUPABASE_URL && cfg.SUPABASE_ANON_KEY && window.supabase);
  const sb = remoto ? window.supabase.createClient(cfg.SUPABASE_URL, cfg.SUPABASE_ANON_KEY) : null;
  const CHAVE = 'financas-modo-teste';

  const novoId = () => (crypto.randomUUID
    ? crypto.randomUUID()
    : '10000000-1000-4000-8000-100000000000'.replace(/[018]/g, (c) =>
      (c ^ (crypto.getRandomValues(new Uint8Array(1))[0] & (15 >> (c / 4)))).toString(16)));

  function lerLocal() {
    try { return JSON.parse(localStorage.getItem(CHAVE)) || {}; } catch { return {}; }
  }
  function gravarLocal(db) { localStorage.setItem(CHAVE, JSON.stringify(db)); }
  function removerLocal(db, tabela, id) {
    db[tabela] = (db[tabela] || []).filter((r) => r.id !== id);
    for (const [filha, coluna] of CASCATA[tabela] || []) {
      for (const r of (db[filha] || []).filter((r) => r[coluna] === id)) removerLocal(db, filha, r.id);
    }
  }

  function falha(error) {
    if (!error) return;
    const msg = {
      'Invalid login credentials': 'E-mail ou senha incorretos.',
      'Email not confirmed': 'Confirme seu e-mail antes de entrar.',
      'Invalid TOTP code entered': 'Código incorreto. Confira no app autenticador e tente de novo.',
    }[error.message];
    throw new Error(msg || error.message);
  }

  return {
    remoto,

    async usuario() {
      if (!remoto) return { email: 'modo de teste' };
      const { data } = await sb.auth.getSession();
      return data.session?.user || null;
    },
    async entrar(email, senha) {
      const { error } = await sb.auth.signInWithPassword({ email, password: senha });
      falha(error);
    },
    async sair() { if (remoto) await sb.auth.signOut(); },

    /* Avisos no celular (Web Push). */
    async salvarInscricaoPush(inscricao) {
      const { endpoint, keys } = inscricao.toJSON();
      const { error } = await sb.from('push_inscricoes').upsert(
        { endpoint, p256dh: keys.p256dh, auth: keys.auth, aparelho: navigator.userAgent.slice(0, 200) },
        { onConflict: 'endpoint' },
      );
      falha(error);
    },
    async removerInscricaoPush(endpoint) {
      falha((await sb.from('push_inscricoes').delete().eq('endpoint', endpoint)).error);
    },
    async enviarAvisoTeste() {
      const { data, error } = await sb.functions.invoke('avisos', { body: { teste: true } });
      if (error) throw new Error('O servidor de avisos não respondeu. Ele já foi configurado?');
      return data;
    },

    /* Verificação em duas etapas (código do app autenticador). */
    async precisaCodigo() {
      if (!remoto) return false;
      const { data, error } = await sb.auth.mfa.getAuthenticatorAssuranceLevel();
      falha(error);
      return data.nextLevel === 'aal2' && data.currentLevel !== 'aal2';
    },
    async doisFatoresAtivo() {
      const { data, error } = await sb.auth.mfa.listFactors();
      falha(error);
      return data.totp.length > 0; // "totp" lista só os já confirmados
    },
    async verificarCodigo(codigo) {
      const { data, error } = await sb.auth.mfa.listFactors();
      falha(error);
      const fator = data.totp[0];
      if (!fator) throw new Error('Verificação em duas etapas não está ativa.');
      falha((await sb.auth.mfa.challengeAndVerify({ factorId: fator.id, code: codigo })).error);
    },
    async iniciarDoisFatores() {
      // Remove tentativas anteriores que não chegaram a ser confirmadas.
      const { data: lista } = await sb.auth.mfa.listFactors();
      for (const f of (lista?.all || []).filter((f) => f.status === 'unverified')) {
        await sb.auth.mfa.unenroll({ factorId: f.id });
      }
      const { data, error } = await sb.auth.mfa.enroll({ factorType: 'totp', friendlyName: `Minhas Finanças ${Date.now()}` });
      falha(error);
      return { id: data.id, qr: data.totp.qr_code, segredo: data.totp.secret };
    },
    async confirmarDoisFatores(factorId, codigo) {
      falha((await sb.auth.mfa.challengeAndVerify({ factorId, code: codigo })).error);
    },
    async desativarDoisFatores() {
      const { data, error } = await sb.auth.mfa.listFactors();
      falha(error);
      for (const f of data.all) falha((await sb.auth.mfa.unenroll({ factorId: f.id })).error);
    },
    aoSair(fn) {
      if (remoto) sb.auth.onAuthStateChange((evento) => { if (evento === 'SIGNED_OUT') fn(); });
    },

    async carregarTudo() {
      if (!remoto) {
        const db = lerLocal();
        return Object.fromEntries(TABELAS.map((t) => [t, db[t] || []]));
      }
      const respostas = await Promise.all(TABELAS.map((t) => sb.from(t).select('*')));
      const dados = {};
      respostas.forEach(({ data, error }, i) => {
        // Tabela nova que ainda não foi criada no banco (script SQL pendente): trata como vazia.
        if (error && (error.code === 'PGRST205' || error.code === '42P01')) {
          console.warn(`Tabela ${TABELAS[i]} não existe ainda no banco.`);
          dados[TABELAS[i]] = [];
          return;
        }
        falha(error);
        dados[TABELAS[i]] = data;
      });
      return dados;
    },

    async inserir(tabela, obj) {
      if (remoto) {
        const { data, error } = await sb.from(tabela).insert(obj).select().single();
        falha(error);
        return data;
      }
      const db = lerLocal();
      const linha = { id: novoId(), created_at: new Date().toISOString(), ...obj };
      (db[tabela] ||= []).push(linha);
      gravarLocal(db);
      return linha;
    },

    async atualizar(tabela, id, obj) {
      if (remoto) { const { error } = await sb.from(tabela).update(obj).eq('id', id); falha(error); return; }
      const db = lerLocal();
      db[tabela] = (db[tabela] || []).map((r) => (r.id === id ? { ...r, ...obj } : r));
      gravarLocal(db);
    },

    async remover(tabela, id) {
      if (remoto) { const { error } = await sb.from(tabela).delete().eq('id', id); falha(error); return; }
      const db = lerLocal();
      removerLocal(db, tabela, id);
      gravarLocal(db);
    },

    // Importa um backup (gerado pelo próprio app) mantendo os ids, sem duplicar o que já existe.
    async importar(backup) {
      for (const t of TABELAS) {
        const linhas = (backup[t] || []).map(({ user_id, created_at, ...resto }) => resto);
        if (!linhas.length) continue;
        if (remoto) {
          const { error } = await sb.from(t).upsert(linhas);
          falha(error);
        } else {
          const db = lerLocal();
          const porId = new Map((db[t] || []).map((r) => [r.id, r]));
          for (const l of linhas) porId.set(l.id, { ...porId.get(l.id), ...l });
          db[t] = [...porId.values()];
          gravarLocal(db);
        }
      }
    },
  };
})();
