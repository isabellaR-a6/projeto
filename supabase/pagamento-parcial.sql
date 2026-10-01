-- Pagamento parcial da fatura e parcelas já pagas em compras antigas.
-- Já incluído no schema.sql; rode este arquivo sozinho só em um banco criado antes desta mudança.

alter table public.lancamentos
  add column if not exists parcelas_pagas smallint not null default 0 check (parcelas_pagas >= 0);

-- Compra (ou parcela) marcada como paga dentro de uma fatura, sem pagar a fatura inteira.
create table if not exists public.itens_pagos (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users on delete cascade,
  lancamento_id uuid not null references public.lancamentos on delete cascade,
  competencia text not null check (competencia ~ '^\d{4}-\d{2}$'),
  pago_em date not null default current_date,
  unique (lancamento_id, competencia)
);

alter table public.itens_pagos enable row level security;

drop policy if exists "so_o_dono" on public.itens_pagos;
create policy "so_o_dono" on public.itens_pagos for all to authenticated
  using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));

drop policy if exists "exige_2fa_se_ativo" on public.itens_pagos;
create policy "exige_2fa_se_ativo" on public.itens_pagos as restrictive for all to authenticated
  using ((select auth.jwt() ->> 'aal') = 'aal2' or not (select privado.tem_2fa_ativo()))
  with check ((select auth.jwt() ->> 'aal') = 'aal2' or not (select privado.tem_2fa_ativo()));
