-- Marcação "já paguei" em gastos de Pix, débito e dinheiro (a bolinha na lista de lançamentos).
-- Já incluído no schema.sql; rode este arquivo sozinho só em um banco criado antes desta mudança.
alter table public.lancamentos add column if not exists pago boolean not null default false;
