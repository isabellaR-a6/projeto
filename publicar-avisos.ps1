# Publica a função "avisos" no Supabase e grava as chaves dela.
# Antes, uma única vez neste computador: npx supabase login
$ErrorActionPreference = 'Stop'
$raiz = $PSScriptRoot
$projeto = 'kwnbzbttiuulhrsblwtw'
# Cache próprio do npm: o cache global deste computador dá erro "ECOMPROMISED".
$env:npm_config_cache = Join-Path $PSScriptRoot '.cache-npm'

# A função usa as mesmas regras do app: copia js/finance.js como módulo.
$regras = Get-Content -Raw -Encoding UTF8 (Join-Path $raiz 'js/finance.js')
$exportar = "`nexport { compAtual, contasDoMes, fatura, hoje, somarDias, somarMeses, todasParcelas };`n"
[IO.File]::WriteAllText((Join-Path $raiz 'supabase/functions/avisos/finance.mjs'), "// GERADO por publicar-avisos.ps1 a partir de js/finance.js. Não edite.`n" + $regras + $exportar)

Push-Location $raiz
try {
  npx -y supabase@latest functions deploy avisos --project-ref $projeto --no-verify-jwt --use-api
  if ($LASTEXITCODE) { throw 'Falha ao publicar a função.' }
  npx -y supabase@latest secrets set --project-ref $projeto --env-file 'supabase/.segredos-avisos.txt'
  if ($LASTEXITCODE) { throw 'Falha ao gravar as chaves.' }
} finally {
  Pop-Location
}
'Função de avisos publicada.'
