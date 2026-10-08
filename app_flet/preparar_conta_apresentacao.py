"""Enche uma conta NOVA do Supabase com dados de exemplo, para apresentar o app sem mostrar dados reais.

Uso (na pasta app_flet):   .venv\\Scripts\\python preparar_conta_apresentacao.py

- Pede o e-mail e a senha da conta de apresentação (a senha não aparece enquanto você digita).
- Se a conta tiver verificação em duas etapas, pede o código.
- POR SEGURANÇA: se a conta já tiver qualquer dado, o script para sem gravar nada.
  Assim não tem como misturar exemplos nas suas finanças reais por engano.
- Não mexe na sessão salva do app (usa um login temporário, só na memória).
"""
from __future__ import annotations

import asyncio
import getpass

from supabase import AsyncClientOptions, acreate_client
from supabase_auth import AsyncMemoryStorage

from financas_app import config
from financas_app.dados import TABELAS, BancoSupabase, ErroApp, dados_de_exemplo

# Colunas que apontam para outra tabela: o id antigo (do exemplo) vira o id novo (gerado pelo banco).
LIGACOES = ("cartao_id", "lancamento_id", "conta_id", "meta_id")


async def semear(banco, dados: dict) -> dict[str, int]:
    """Grava os dados de exemplo trocando os ids pelos gerados no banco. Devolve quantos por tabela."""
    novos: dict[str, str] = {}
    contagem = {}
    for tabela in TABELAS:  # ordem já respeita as ligações (cartões antes das compras etc.)
        contagem[tabela] = 0
        for linha in dados.get(tabela, []):
            obj = {k: v for k, v in linha.items() if k not in ("id", "created_at", "user_id", "pago")}
            for coluna in LIGACOES:
                if obj.get(coluna):
                    obj[coluna] = novos[obj[coluna]]
            gravado = await banco.inserir(tabela, obj)
            novos[linha["id"]] = gravado["id"]
            contagem[tabela] += 1
    return contagem


async def main() -> None:
    print("Conta de APRESENTAÇÃO (não use a sua conta de verdade).")
    email = input("E-mail: ").strip()
    senha = getpass.getpass("Senha (não aparece enquanto digita): ")

    banco = BancoSupabase()
    banco.sb = await acreate_client(config.SUPABASE_URL, config.SUPABASE_ANON_KEY,
                                    AsyncClientOptions(storage=AsyncMemoryStorage(), persist_session=False,
                                                       auto_refresh_token=False))
    try:
        await banco.entrar(email, senha)
        if await banco.precisa_codigo():
            await banco.verificar_codigo(input("Código de 6 dígitos do autenticador: ").strip())
        atuais = await banco.carregar_tudo()
        ocupadas = {t: len(v) for t, v in atuais.items() if v}
        if ocupadas:
            print("\nEsta conta JÁ TEM dados:", ", ".join(f"{t} ({n})" for t, n in ocupadas.items()))
            print("Por segurança, nada foi gravado. Use uma conta nova, só para a apresentação.")
            return
        contagem = await semear(banco, dados_de_exemplo())
        print("\nPronto! Dados de exemplo gravados:")
        for tabela, n in contagem.items():
            if n:
                print(f"  {tabela}: {n}")
        print("\nAgora é só entrar no app com essa conta.")
    except ErroApp as e:
        print(f"\nNão deu certo: {e}")
    finally:
        await banco.sb.auth.sign_out({"scope": "local"})


if __name__ == "__main__":
    asyncio.run(main())
