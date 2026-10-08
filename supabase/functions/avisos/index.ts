// Função "avisos": manda notificação no celular do que vence hoje ou amanhã.
// - Chamada pelo agendamento diário (pg_cron, 8h de Brasília) com o cabeçalho x-cron-secret.
// - Chamada pelo app com o login da usuária para mandar uma notificação de teste.
// finance.mjs é uma cópia de site/js/finance.js gerada por scripts/publicar-avisos.ps1 (mesmas regras do app).
import { createClient } from 'npm:@supabase/supabase-js@2';
import webpush from 'npm:web-push@3.6.7';
import { compAtual, contasDoMes, fatura, hoje, somarDias, somarMeses, todasParcelas } from './finance.mjs';

const TABELAS = ['cartoes', 'lancamentos', 'faturas_pagas', 'itens_pagos', 'pagamentos_fatura', 'contas_fixas', 'contas_pagas'];
const BRL = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });
const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};
const resposta = (corpo: unknown, status = 200) =>
  new Response(JSON.stringify(corpo), { status, headers: { ...CORS, 'Content-Type': 'application/json' } });

webpush.setVapidDetails(
  'https://minhas-financas-isa.netlify.app',
  Deno.env.get('VAPID_PUBLIC')!,
  Deno.env.get('VAPID_PRIVATE')!,
);

// deno-lint-ignore no-explicit-any
type Admin = any;

async function contasAVencer(admin: Admin, userId: string) {
  const d: Record<string, unknown[]> = {};
  for (const t of TABELAS) {
    const { data, error } = await admin.from(t).select('*').eq('user_id', userId);
    if (error) throw error;
    d[t] = data ?? [];
  }
  const dia = hoje();
  const amanha = somarDias(dia, 1);
  const quando = (data: string) => (data === dia ? 'hoje' : data === amanha ? 'amanhã' : null);
  const meses = [compAtual(), somarMeses(compAtual(), 1)];
  const parcelas = todasParcelas(d);
  const itens: { quando: string; nome: string; valor: number }[] = [];

  for (const comp of meses) {
    for (const x of contasDoMes(d, comp)) {
      const q = quando(x.vencimento);
      if (q && !x.pagamento) itens.push({ quando: q, nome: x.conta.descricao, valor: Number(x.conta.valor) });
    }
    for (const c of d.cartoes as { nome: string }[]) {
      const f = fatura(d, c, comp, parcelas);
      const q = quando(f.vencimento);
      if (q && f.aPagar > 0) itens.push({ quando: q, nome: `Fatura ${c.nome}`, valor: f.aPagar });
    }
  }
  return itens.sort((a, b) => (a.quando === b.quando ? 0 : a.quando === 'hoje' ? -1 : 1));
}

function montarAviso(itens: { quando: string; nome: string; valor: number }[]) {
  if (itens.length === 1) {
    const [x] = itens;
    return { titulo: `Vence ${x.quando}: ${x.nome}`, corpo: `${BRL.format(x.valor)}. Toque para abrir o app.` };
  }
  const total = itens.reduce((s, x) => s + x.valor, 0);
  return {
    titulo: `${itens.length} contas para pagar (${BRL.format(total)})`,
    corpo: itens.map((x) => `${x.quando === 'hoje' ? 'Hoje' : 'Amanhã'}: ${x.nome} — ${BRL.format(x.valor)}`).join('\n'),
  };
}

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: CORS });
  const admin = createClient(Deno.env.get('SUPABASE_URL')!, Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!);

  // Quem está chamando: o agendamento (todas as usuárias) ou o app (teste só para quem está logada).
  let somenteUsuario: string | null = null;
  const segredo = Deno.env.get('CRON_SECRET');
  if (!(segredo && req.headers.get('x-cron-secret') === segredo)) {
    const jwt = (req.headers.get('Authorization') ?? '').replace(/^Bearer\s+/i, '');
    const { data } = await admin.auth.getUser(jwt);
    if (!data?.user) return resposta({ erro: 'não autorizado' }, 401);
    somenteUsuario = data.user.id;
  }

  let consulta = admin.from('push_inscricoes').select('*');
  if (somenteUsuario) consulta = consulta.eq('user_id', somenteUsuario);
  const { data: inscricoes, error } = await consulta;
  if (error) return resposta({ erro: error.message }, 500);

  const porUsuario = new Map<string, typeof inscricoes>();
  for (const i of inscricoes ?? []) porUsuario.set(i.user_id, [...(porUsuario.get(i.user_id) ?? []), i]);

  let enviados = 0;
  for (const [userId, lista] of porUsuario) {
    const aviso = somenteUsuario
      ? { titulo: 'Avisos ativados', corpo: 'Tudo certo! Às 8h você recebe o que vence hoje e amanhã.' }
      : null;
    const itens = aviso ? [] : await contasAVencer(admin, userId);
    const conteudo = aviso ?? (itens.length ? montarAviso(itens) : null);
    if (!conteudo) continue;

    const payload = JSON.stringify({ ...conteudo, tag: `avisos-${hoje()}`, url: './' });
    for (const i of lista!) {
      try {
        await webpush.sendNotification({ endpoint: i.endpoint, keys: { p256dh: i.p256dh, auth: i.auth } }, payload);
        enviados++;
      } catch (e) {
        // Inscrição que não existe mais (app desinstalado, permissão revogada): apaga.
        const status = (e as { statusCode?: number }).statusCode;
        if (status === 404 || status === 410) await admin.from('push_inscricoes').delete().eq('id', i.id);
        else console.error('falha ao enviar', status, (e as Error).message);
      }
    }
  }
  return resposta({ enviados });
});
