# Publica o site no Netlify (https://minhas-financas-isa.netlify.app).
# Botão direito → "Executar com o PowerShell". Precisa do Node instalado e da conta do Netlify logada.
$ErrorActionPreference = 'Stop'
$raiz = Split-Path $PSScriptRoot
$site = Join-Path $raiz 'site'
# Cache próprio do npm: o cache global deste computador dá erro "ECOMPROMISED".
$env:npm_config_cache = Join-Path $raiz '.cache-npm'
npx -y netlify-cli@latest deploy --dir $site --prod --no-build --site 7c7e488a-b9b7-4c8c-ad83-160e84bee80a
Read-Host 'Pronto. Aperte Enter para fechar'
