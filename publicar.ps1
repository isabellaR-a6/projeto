# Publica o app no Netlify (https://minhas-financas-isa.netlify.app).
# Botão direito → "Executar com o PowerShell". Precisa do Node instalado e da conta do Netlify logada.
$ErrorActionPreference = 'Stop'
$src = $PSScriptRoot
$tmp = Join-Path $env:TEMP 'financas-publicar'
if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force -Confirm:$false }
foreach ($rel in 'index.html', 'manifest.json', 'sw.js', 'icon.svg', 'icon-192.png', 'icon-512.png', 'badge-96.png', 'css/style.css', 'js/config.js', 'js/store.js', 'js/finance.js', 'js/app.js') {
  $destino = Join-Path $tmp $rel
  New-Item -ItemType Directory -Force (Split-Path $destino) | Out-Null
  Copy-Item (Join-Path $src $rel) $destino
}
# Cache próprio do npm: o cache global deste computador dá erro "ECOMPROMISED".
$env:npm_config_cache = Join-Path $PSScriptRoot '.cache-npm'
npx -y netlify-cli@latest deploy --dir $tmp --prod --no-build --site 7c7e488a-b9b7-4c8c-ad83-160e84bee80a
Read-Host 'Pronto. Aperte Enter para fechar'
