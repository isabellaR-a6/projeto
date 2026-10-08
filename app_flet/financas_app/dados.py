"""Acesso aos dados: Supabase (conta real) ou demonstração (arquivo local com dados de exemplo).

As duas classes têm os mesmos métodos, então as telas não sabem qual está em uso.
"""
from __future__ import annotations

import asyncio
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from supabase import AsyncClientOptions, acreate_client
from supabase_auth import AsyncMemoryStorage, AsyncSupportedStorage

from . import config
from . import regras as R

TABELAS = ["cartoes", "lancamentos", "faturas_pagas", "itens_pagos", "pagamentos_fatura",
           "contas_fixas", "contas_pagas", "metas", "metas_movimentos"]

# Mesmas regras de "on delete cascade" do banco, para o modo demonstração.
CASCATA = {
    "cartoes": [("lancamentos", "cartao_id"), ("faturas_pagas", "cartao_id"), ("pagamentos_fatura", "cartao_id")],
    "contas_fixas": [("contas_pagas", "conta_id")],
    "lancamentos": [("contas_pagas", "lancamento_id"), ("itens_pagos", "lancamento_id")],
    "metas": [("metas_movimentos", "meta_id")],
}

ERROS = {
    "Invalid login credentials": "E-mail ou senha incorretos.",
    "Email not confirmed": "Confirme seu e-mail antes de entrar.",
    "Invalid TOTP code entered": "Código incorreto. Confira no app autenticador e tente de novo.",
}


class ErroApp(Exception):
    """Erro com mensagem pronta para mostrar na tela."""


def pasta_dados() -> Path:
    """Pasta privada do app (no Android o Flet informa por variável de ambiente)."""
    pasta = Path(os.getenv("FLET_APP_STORAGE_DATA") or Path.home() / ".minhas-financas")
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def _traduzir(e: Exception) -> ErroApp:
    msg = getattr(e, "message", None) or str(e)
    return ErroApp(ERROS.get(msg, msg))


class SessaoEmArquivo(AsyncSupportedStorage):
    """Guarda a sessão do Supabase na pasta do app (igual ao localStorage do site)."""

    def __init__(self) -> None:
        self.arquivo = pasta_dados() / "sessao.json"

    def _ler(self) -> dict:
        try:
            return json.loads(self.arquivo.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    async def get_item(self, key: str) -> str | None:
        return self._ler().get(key)

    async def set_item(self, key: str, value: str) -> None:
        dados = self._ler()
        dados[key] = value
        self.arquivo.write_text(json.dumps(dados), encoding="utf-8")

    async def remove_item(self, key: str) -> None:
        dados = self._ler()
        dados.pop(key, None)
        self.arquivo.write_text(json.dumps(dados), encoding="utf-8")


class BancoSupabase:
    demonstracao = False

    def __init__(self) -> None:
        self.sb = None

    async def iniciar(self) -> None:
        self.sb = await acreate_client(
            config.SUPABASE_URL, config.SUPABASE_ANON_KEY,
            AsyncClientOptions(storage=SessaoEmArquivo(), persist_session=True, auto_refresh_token=True),
        )

    async def email(self) -> str | None:
        sessao = await self.sb.auth.get_session()
        return sessao.user.email if sessao and sessao.user else None

    async def entrar(self, email: str, senha: str) -> None:
        try:
            await self.sb.auth.sign_in_with_password({"email": email, "password": senha})
        except Exception as e:  # noqa: BLE001 - mensagem vai para a tela
            raise _traduzir(e) from e

    async def conferir_senha(self, senha: str) -> bool:
        """Confere a senha sem mexer na sessão atual (usa um cliente separado, só na memória)."""
        email = await self.email()
        if not email:
            return False
        temp = await acreate_client(config.SUPABASE_URL, config.SUPABASE_ANON_KEY,
                                    AsyncClientOptions(storage=AsyncMemoryStorage(), persist_session=False,
                                                       auto_refresh_token=False))
        try:
            await temp.auth.sign_in_with_password({"email": email, "password": senha})
            # "local": encerra só este login temporário. O padrão ("global") derrubaria
            # todas as sessões da conta (site, celular e este app).
            await temp.auth.sign_out({"scope": "local"})
            return True
        except Exception:  # noqa: BLE001
            return False

    async def precisa_codigo(self) -> bool:
        nivel = await self.sb.auth.mfa.get_authenticator_assurance_level()
        return nivel.next_level == "aal2" and nivel.current_level != "aal2"

    async def verificar_codigo(self, codigo: str) -> None:
        try:
            fatores = await self.sb.auth.mfa.list_factors()
            if not fatores.totp:
                raise ErroApp("A verificação em duas etapas não está ativa.")
            await self.sb.auth.mfa.challenge_and_verify({"factor_id": fatores.totp[0].id, "code": codigo})
        except ErroApp:
            raise
        except Exception as e:  # noqa: BLE001
            raise _traduzir(e) from e

    async def sair(self) -> None:
        await self.sb.auth.sign_out()

    async def carregar_tudo(self) -> dict:
        async def uma(t: str) -> list:
            try:
                return (await self.sb.table(t).select("*").execute()).data
            except Exception as e:  # noqa: BLE001
                # Tabela nova ainda não criada no banco (script SQL pendente): trata como vazia.
                if getattr(e, "code", "") in ("PGRST205", "42P01"):
                    return []
                raise _traduzir(e) from e
        listas = await asyncio.gather(*(uma(t) for t in TABELAS))
        return dict(zip(TABELAS, listas))

    async def inserir(self, tabela: str, obj: dict) -> dict:
        try:
            return (await self.sb.table(tabela).insert(obj).execute()).data[0]
        except Exception as e:  # noqa: BLE001
            raise _traduzir(e) from e

    async def atualizar(self, tabela: str, id_: str, obj: dict) -> None:
        try:
            await self.sb.table(tabela).update(obj).eq("id", id_).execute()
        except Exception as e:  # noqa: BLE001
            raise _traduzir(e) from e

    async def remover(self, tabela: str, id_: str) -> None:
        try:
            await self.sb.table(tabela).delete().eq("id", id_).execute()
        except Exception as e:  # noqa: BLE001
            raise _traduzir(e) from e


class BancoDemonstracao:
    """Dados de exemplo num arquivo local. Nada vai para a internet."""

    demonstracao = True

    def __init__(self) -> None:
        self.arquivo = pasta_dados() / "demonstracao.json"

    async def iniciar(self) -> None:
        if not self.arquivo.exists():
            self._gravar(dados_de_exemplo())

    def _ler(self) -> dict:
        try:
            db = json.loads(self.arquivo.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            db = {}
        return {t: db.get(t, []) for t in TABELAS}

    def _gravar(self, db: dict) -> None:
        self.arquivo.write_text(json.dumps(db, ensure_ascii=False), encoding="utf-8")

    async def email(self) -> str | None:
        return "demonstracao"

    async def entrar(self, email: str, senha: str) -> None:
        return None

    async def conferir_senha(self, senha: str) -> bool:
        return True

    async def precisa_codigo(self) -> bool:
        return False

    async def verificar_codigo(self, codigo: str) -> None:
        return None

    async def sair(self) -> None:
        return None

    async def carregar_tudo(self) -> dict:
        return self._ler()

    async def inserir(self, tabela: str, obj: dict) -> dict:
        db = self._ler()
        linha = {"id": str(uuid.uuid4()), "created_at": datetime.now(timezone.utc).isoformat(), **obj}
        db[tabela].append(linha)
        self._gravar(db)
        return linha

    async def atualizar(self, tabela: str, id_: str, obj: dict) -> None:
        db = self._ler()
        db[tabela] = [{**r, **obj} if r["id"] == id_ else r for r in db[tabela]]
        self._gravar(db)

    async def remover(self, tabela: str, id_: str) -> None:
        db = self._ler()
        self._remover(db, tabela, id_)
        self._gravar(db)

    def _remover(self, db: dict, tabela: str, id_: str) -> None:
        db[tabela] = [r for r in db[tabela] if r["id"] != id_]
        for filha, coluna in CASCATA.get(tabela, []):
            for r in [r for r in db[filha] if r.get(coluna) == id_]:
                self._remover(db, filha, r["id"])

    def reiniciar(self) -> None:
        self._gravar(dados_de_exemplo())


def dados_de_exemplo() -> dict:
    """Um mês realista para mostrar o app funcionando."""
    h = R.hoje()
    comp = R.comp_atual()
    ant = R.somar_meses(comp, -1)
    dia = lambda c, n: R.data_no_mes(c, n)  # noqa: E731
    nu, it = "demo-nubank", "demo-itau"
    lanc = [
        ("Salário", 3500, dia(comp, 5), "receita", "salario", None, None, 1, 0),
        ("Freela de site", 800, dia(comp, 2), "receita", "extra", None, None, 1, 0),
        ("Salário", 3500, dia(ant, 5), "receita", "salario", None, None, 1, 0),
        ("Mercado do mês", 612.4, dia(comp, 3), "despesa", "mercado", "debito", None, 1, 0),
        ("Aluguel", 1200, dia(comp, 5), "despesa", "casa", "pix", None, 1, 0),
        ("Farmácia", 86.9, R.somar_dias(h, -2) if R.somar_dias(h, -2)[:7] == comp else dia(comp, 1), "despesa", "saude", "pix", None, 1, 0),
        ("Celular novo", 2400, dia(R.somar_meses(comp, -2), 20), "despesa", "compras", "credito", nu, 10, 1),
        ("iFood", 89.9, dia(ant, 15), "despesa", "alimentacao", "credito", nu, 1, 0),
        ("Tênis de corrida", 600, dia(comp, 1), "despesa", "compras", "credito", nu, 3, 0),
        ("Uber", 45, dia(ant, 20), "despesa", "transporte", "credito", it, 1, 0),
        ("Game Pass", 59.99, dia(comp, 2), "despesa", "assinaturas", "credito", it, 1, 0),
    ]
    return {
        "cartoes": [
            {"id": nu, "nome": "Nubank", "limite": 5500, "fechamento": 3, "vencimento": 10, "cor": "#7c3aed"},
            {"id": it, "nome": "Itaú", "limite": 2000, "fechamento": 25, "vencimento": 5, "cor": "#db2777"},
        ],
        "lancamentos": [
            {"id": f"demo-l{i}", "descricao": d, "valor": v, "data": data, "tipo": t, "categoria": cat,
             "forma": forma, "cartao_id": cartao, "parcelas": n, "parcelas_pagas": pp, "pago": False,
             "created_at": f"2026-01-01T00:00:{i:02d}Z"}
            for i, (d, v, data, t, cat, forma, cartao, n, pp) in enumerate(lanc)
        ],
        "faturas_pagas": [], "itens_pagos": [], "pagamentos_fatura": [],
        "contas_fixas": [], "contas_pagas": [],
        "metas": [{"id": "demo-m1", "nome": "Viagem para o Nordeste", "alvo": 8000,
                   "prazo": R.somar_meses(comp, 8), "cor": "#a21caf"},
                  {"id": "demo-m2", "nome": "Reserva de emergência", "alvo": 10000, "prazo": None, "cor": "#4f46e5"}],
        "metas_movimentos": [{"id": "demo-mv1", "meta_id": "demo-m1", "valor": 1250, "data": dia(ant, 10)},
                             {"id": "demo-mv2", "meta_id": "demo-m1", "valor": 300, "data": dia(comp, 6)},
                             {"id": "demo-mv3", "meta_id": "demo-m2", "valor": 2100, "data": dia(ant, 6)}],
    }
