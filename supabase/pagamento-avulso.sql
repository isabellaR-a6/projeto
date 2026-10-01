-- Valores avulsos pagos numa fatura ("sobrou dinheiro e paguei R$ 50").
-- Já incluído no schema.sql; rode este arquivo sozinho só em um banco criado antes desta mudança.

create table if not exists public.pagamentos_fatura (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users on delete cascade,
  cartao_id uuid not null references public.cartoes on delete cascade,
  competencia text not null check (competencia ~ '^\d{4}-\d{2}$'),
  valor numeric(12,2) not null check (valor > 0),
  data date not null default current_date,
  created_at timestamptz not null default now()
);

alter table public.pagamentos_fatura enable row level security;

drop policy if exists "so_o_dono" on public.pagamentos_fatura;
create policy "so_o_dono" on public.pagamentos_fatura for all to authenticated
  using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));

drop policy if exists "exige_2fa_se_ativo" on public.pagamentos_fatura;
create policy "exige_2fa_se_ativo" on public.pagamentos_fatura as restrictive for all to authenticated
  using ((select auth.jwt() ->> 'aal') = 'aal2' or not (select privado.tem_2fa_ativo()))
  with check ((select auth.jwt() ->> 'aal') = 'aal2' or not (select privado.tem_2fa_ativo()));
