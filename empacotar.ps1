# Gera ..\financas-site.zip só com os arquivos do site, pronto para arrastar no Netlify.
$src = $PSScriptRoot
$zip = Join-Path (Split-Path $src) 'financas-site.zip'
if (Test-Path $zip) { Remove-Item $zip -Confirm:$false }
Add-Type -AssemblyName System.IO.Compression, System.IO.Compression.FileSystem
$arq = [IO.Compression.ZipFile]::Open($zip, 'Create')
foreach ($rel in 'index.html', 'manifest.json', 'sw.js', 'icon.svg', 'icon-192.png', 'icon-512.png', 'badge-96.png', 'css/style.css', 'js/config.js', 'js/store.js', 'js/finance.js', 'js/app.js') {
  [void][IO.Compression.ZipFileExtensions]::CreateEntryFromFile($arq, (Join-Path $src $rel), $rel)
}
$arq.Dispose()
"Pacote criado: $zip"
