# Minhas Finanças

Controle financeiro pessoal: saldo previsto do mês, gastos por forma de pagamento (Pix, débito, dinheiro, crédito), faturas e limite dos cartões com parcelas, contas fixas, metas para juntar dinheiro e alertas do que está para vencer.

Funciona no PC e no celular. É só HTML, CSS e JavaScript, sem instalar nada.

## Testar agora (modo de teste)

Com `js/config.js` em branco, o app roda sem login e guarda os dados **só no navegador** em que você abriu. Serve para experimentar.

Para abrir no PC, rode na pasta do projeto:

```
python -m http.server 5520
```

e acesse http://localhost:5520.

## Ativar login e sincronização (só você tem acesso)

1. Crie uma conta grátis em https://supabase.com e clique em **New project**. Anote a senha do banco em um lugar seguro.
2. No projeto, abra **SQL Editor → New query**, cole todo o conteúdo de `supabase/schema.sql` e clique em **Run**.
3. Crie o seu usuário: **Authentication → Users → Add user → Create new user**. Informe seu e-mail e uma senha forte e marque **Auto Confirm User**.
4. **Bloqueie novos cadastros**: em **Authentication → Sign In / Providers**, desligue **Allow new users to sign up** e salve. Assim ninguém mais consegue criar conta, nem tendo o link do app.
5. Em **Project Settings → API** (ou **Data API**), copie a **Project URL** e a chave **anon / publishable** e cole em `js/config.js`:

   ```js
   window.CONFIG = {
     SUPABASE_URL: 'https://xxxxxxxx.supabase.co',
     SUPABASE_ANON_KEY: 'eyJhbGciOi...',
   };
   ```

   A chave *anon* pode ficar no código, porque foi feita para isso: sem login, ela não lê nada, já que todas as tabelas têm regras (RLS) que só liberam os dados para o dono. **Nunca** coloque a chave `service_role` no app.

6. Abra o app, entre com seu e-mail e senha, e pronto.

Se você usou o modo de teste antes, vá em **Metas → Baixar backup** *antes* de preencher o `config.js`. Depois, já logada, use **Importar backup**.

## Verificação em duas etapas

1. No Supabase, rode `supabase/2fa.sql` no SQL Editor. Isso faz o banco exigir o código para quem tem a verificação ligada. Quem cria o banco do zero com o `schema.sql` já recebe essa regra.
2. No app, clique no **escudo** no topo → **Ativar**, escaneie o QR code com o Google Authenticator ou o Microsoft Authenticator e confirme com o código.

A partir daí, todo login pede a senha **e** o código do app autenticador. Se trocar de celular, transfira as contas do autenticador antes de apagar o antigo.

## Endereço do app

**https://minhas-financas-isa.netlify.app**.

Para publicar uma atualização: botão direito em `publicar.ps1` → **Executar com o PowerShell**. Precisa do Node instalado e da conta do Netlify logada no computador; se não estiver, rode `npx netlify-cli login` antes.

## Usar no celular

O app precisa estar publicado em um endereço na internet. O jeito mais fácil:

1. Entre em https://app.netlify.com/drop (crie uma conta grátis).
2. Arraste a pasta `financas` inteira para a página.
3. O Netlify gera um link (dá para trocar o nome em *Site configuration*). Abra esse link no celular, entre e use **Adicionar à tela inicial** (no Android, pelo menu do Chrome; no iPhone, pelo botão Compartilhar do Safari). Ele passa a abrir como um aplicativo.

Para atualizar o site depois, rode `empacotar.ps1` (botão direito → *Executar com o PowerShell*). Ele cria `financas-site.zip` na pasta Documentos. Arraste esse zip em **Deploys** no Netlify.

Os seus dados ficam no Supabase, não nos arquivos do site.

## Como as contas são feitas

- **Fatura**: identificada pelo mês em que vence. A compra feita **no dia do fechamento ou depois** vai para a fatura seguinte. Por isso o "melhor dia de compra" é o próprio dia do fechamento.
- **Parcelas**: o valor total é dividido igualmente, e os centavos que sobram vão na 1ª parcela. Cada parcela cai em uma fatura.
- **Limite usado**: soma de todas as parcelas de faturas que ainda não foram marcadas como pagas, inclusive as futuras. Igual ao que o banco faz.
- **Gastos do mês**: o que você pagou com Pix, débito ou dinheiro no mês, mais as faturas que vencem no mês.
- **Saldo previsto**: entradas − gastos e faturas − contas fixas que ainda faltam pagar − o que você guardou nas metas no mês.
- **Crédito**: ao lançar, escolha o cartão e se é à vista ou parcelado. O app mostra o valor de cada parcela, em qual fatura cai a primeira, **quando termina de pagar** e quanto de limite sobra depois da compra.
- **Cartões**: cada cartão mostra o limite total, quanto já foi gasto (limite em uso) e quanto está disponível, além dos parcelamentos em andamento com quanto falta e quando terminam.
- **Metas**: diga quanto quer juntar e, se quiser, até quando. O app calcula quanto guardar por mês. Use **Guardar** e **Retirar** para registrar os depósitos.
- **Pagar a fatura aos poucos**: marque compras específicas como pagas (o ✓ de cada compra) ou use **Pagar um valor** para registrar um valor solto (ex.: R$ 50). A fatura mostra quanto foi pago e quanto falta, e o limite libera na hora.
- **Simular**: veja, antes de comprar ou pagar, como ficariam o limite, as faturas e a sobra de cada mês. Nada é salvo.
- **Contas fixas**: ao marcar como paga, vira um lançamento do mês. Ao desmarcar, o lançamento é removido.
- O ícone de olho no topo esconde os valores (para usar em público).
