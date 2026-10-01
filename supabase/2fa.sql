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
  foreach t in array array['cartoes','lancamentos','faturas_pagas','contas_fixas','contas_pagas','metas','metas_movimentos'] loop
    execute format('drop policy if exists "exige_2fa_se_ativo" on public.%I', t);
    execute format(
      'create policy "exige_2fa_se_ativo" on public.%I as restrictive for all to authenticated
         using ((select auth.jwt() ->> ''aal'') = ''aal2'' or not (select privado.tem_2fa_ativo()))
         with check ((select auth.jwt() ->> ''aal'') = ''aal2'' or not (select privado.tem_2fa_ativo()))', t);
  end loop;
end $$;
