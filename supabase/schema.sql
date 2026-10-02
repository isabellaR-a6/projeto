-- Minhas Finanças — estrutura do banco
-- Cole tudo isto no Supabase em: SQL Editor → New query → Run.
-- Cada tabela tem RLS: só o dono (o usuário logado) enxerga e altera as próprias linhas.

create table if not exists public.cartoes (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users on delete cascade,
  nome text not null,
  limite numeric(12,2) not null default 0,
  fechamento smallint not null check (fechamento between 1 and 31),
  vencimento smallint not null check (vencimento between 1 and 31),
  cor text not null default '#7c3aed',
  created_at timestamptz not null default now()
);

create table if not exists public.lancamentos (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users on delete cascade,
  tipo text not null check (tipo in ('receita', 'despesa')),
  descricao text not null,
  valor numeric(12,2) not null check (valor > 0),
  data date not null,
  categoria text not null,
  forma text check (forma in ('pix', 'debito', 'dinheiro', 'credito')),
  cartao_id uuid references public.cartoes on delete cascade,
  parcelas smallint not null default 1 check (parcelas between 1 and 48),
  parcelas_pagas smallint not null default 0 check (parcelas_pagas >= 0),
  pago boolean not null default false,
  created_at timestamptz not null default now()
);

create table if not exists public.faturas_pagas (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users on delete cascade,
  cartao_id uuid not null references public.cartoes on delete cascade,
  competencia text not null check (competencia ~ '^\d{4}-\d{2}$'),
  pago_em date not null default current_date,
  unique (cartao_id, competencia)
);

-- Compra (ou parcela) marcada como paga dentro de uma fatura, sem pagar a fatura inteira.
create table if not exists public.itens_pagos (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users on delete cascade,
  lancamento_id uuid not null references public.lancamentos on delete cascade,
  competencia text not null check (competencia ~ '^\d{4}-\d{2}$'),
  pago_em date not null default current_date,
  unique (lancamento_id, competencia)
);

-- Valores avulsos pagos numa fatura ("sobrou dinheiro e paguei R$ 50").
create table if not exists public.pagamentos_fatura (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users on delete cascade,
  cartao_id uuid not null references public.cartoes on delete cascade,
  competencia text not null check (competencia ~ '^\d{4}-\d{2}$'),
  valor numeric(12,2) not null check (valor > 0),
  data date not null default current_date,
  created_at timestamptz not null default now()
);

-- Aparelhos que recebem os avisos de contas (Web Push). O agendamento fica em avisos.sql.
create table if not exists public.push_inscricoes (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users on delete cascade,
  endpoint text not null unique,
  p256dh text not null,
  auth text not null,
  aparelho text,
  created_at timestamptz not null default now()
);

create table if not exists public.contas_fixas (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users on delete cascade,
  descricao text not null,
  valor numeric(12,2) not null check (valor > 0),
  dia smallint not null check (dia between 1 and 31),
  categoria text not null,
  desde text not null check (desde ~ '^\d{4}-\d{2}$'),
  ativa boolean not null default true,
  created_at timestamptz not null default now()
);

create table if not exists public.contas_pagas (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users on delete cascade,
  conta_id uuid not null references public.contas_fixas on delete cascade,
  competencia text not null check (competencia ~ '^\d{4}-\d{2}$'),
  lancamento_id uuid references public.lancamentos on delete cascade,
  unique (conta_id, competencia)
);

create table if not exists public.metas (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users on delete cascade,
  nome text not null,
  alvo numeric(12,2) not null check (alvo > 0),
  prazo text check (prazo ~ '^\d{4}-\d{2}$'),
  cor text not null default '#7c3aed',
  created_at timestamptz not null default now()
);

-- Valor positivo = guardou; negativo = retirou.
create table if not exists public.metas_movimentos (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users on delete cascade,
  meta_id uuid not null references public.metas on delete cascade,
  valor numeric(12,2) not null check (valor <> 0),
  data date not null,
  created_at timestamptz not null default now()
);

do $$
declare t text;
begin
  foreach t in array array['cartoes','lancamentos','faturas_pagas','itens_pagos','pagamentos_fatura','push_inscricoes','contas_fixas','contas_pagas','metas','metas_movimentos'] loop
    execute format('alter table public.%I enable row level security', t);
    execute format('drop policy if exists "so_o_dono" on public.%I', t);
    execute format(
      'create policy "so_o_dono" on public.%I for all to authenticated
         using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()))', t);
  end loop;
end $$;

-- Verificação em duas etapas obrigatória no banco.
-- Se o usuário tem um app autenticador confirmado, toda leitura/gravação exige
-- uma sessão que passou pelo código (aal2). Sem autenticador, basta a senha (aal1).

-- A tabela auth.mfa_factors não pode ser lida pelos usuários, então a checagem
-- fica numa função "security definer" em um schema que não é exposto pela API.
create schema if not exists privado;
grant usage on schema privado to authenticated;

create or replace function privado.tem_2fa_ativo()
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1 from auth.mfa_factors
    where user_id = (select auth.uid()) and status = 'verified'
  );
$$;

revoke all on function privado.tem_2fa_ativo() from public, anon;
grant execute on function privado.tem_2fa_ativo() to authenticated;

do $$
declare t text;
begin
  foreach t in array array['cartoes','lancamentos','faturas_pagas','itens_pagos','pagamentos_fatura','push_inscricoes','contas_fixas','contas_pagas','metas','metas_movimentos'] loop
    execute format('drop policy if exists "exige_2fa_se_ativo" on public.%I', t);
    execute format(
      'create policy "exige_2fa_se_ativo" on public.%I as restrictive for all to authenticated
         using ((select auth.jwt() ->> ''aal'') = ''aal2'' or not (select privado.tem_2fa_ativo()))
         with check ((select auth.jwt() ->> ''aal'') = ''aal2'' or not (select privado.tem_2fa_ativo()))', t);
  end loop;
end $$;
