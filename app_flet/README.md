# Minhas Finanças — app em Flet (Python)

A mesma aplicação do site, feita em Python com [Flet](https://flet.dev). Usa **os mesmos dados**
(o mesmo projeto Supabase), então o que você lança no app aparece no site e vice-versa.

## Rodar no computador

Na pasta `app_flet`:

```
python -m venv .venv
.venv\Scripts\pip install flet==1.0.3 supabase==2.32.0 winrt-Windows.Security.Credentials.UI==3.2.1 winrt-Windows.Foundation==3.2.1
.venv\Scripts\python main.py
```

Para abrir no navegador em vez de uma janela: `.venv\Scripts\python main.py --web`.

Na tela de entrada há **Ver demonstração com dados de exemplo**: abre o app com dados fictícios,
guardados só no computador. Bom para apresentar o projeto sem mostrar suas finanças.

## Biometria (sem guardar rosto)

Depois do primeiro login, ao abrir o app ele pede a **biometria do próprio aparelho**:

- **Windows:** Windows Hello (rosto, digital ou PIN).
- **Android/iOS:** a digital ou o rosto do celular (extensão `flet-local-auth`).

O app **nunca vê, recebe ou guarda** rosto, digital ou foto. Ele só pergunta ao sistema
"é a dona?" e recebe sim ou não. Quem lê e guarda a biometria é o chip de segurança do aparelho.
Sem biometria disponível, o app pede a senha da conta no lugar.

Liga e desliga em **Segurança** (engrenagem no topo).

## Gerar o app Android (APK)

Precisa do Flutter SDK e do Android SDK (o `flet build` instala o que faltar na primeira vez).

```
.venv\Scripts\flet build apk
```

O arquivo sai em `build/apk`. Copie para o celular e instale (permita "fontes desconhecidas").
As dependências e a permissão de biometria já estão no `pyproject.toml`.

## Testes

As regras (faturas, parcelas, limite, saldo, metas) estão em `financas_app/regras.py`, traduzidas
de `site/js/finance.js`. O teste compara as duas com dados aleatórios, para os dois apps darem sempre
os mesmos valores:

```
.venv\Scripts\python testes\test_regras_iguais_ao_site.py
```

## Organização

| Arquivo | O que faz |
|---|---|
| `main.py` | Ponto de entrada |
| `financas_app/app.py` | Telas, formulários, trava e login |
| `financas_app/ui.py` | Cores, fontes e componentes visuais |
| `financas_app/regras.py` | Cálculos (iguais aos do site) |
| `financas_app/dados.py` | Supabase e modo demonstração |
| `financas_app/biometria.py` | Windows Hello e biometria do celular |
