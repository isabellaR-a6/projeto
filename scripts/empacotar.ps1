# Gera Documentos\financas-site.zip com a pasta site/, pronto para arrastar no Netlify.
$raiz = Split-Path $PSScriptRoot
$site = Join-Path $raiz 'site'
$zip = Join-Path (Split-Path $raiz) 'financas-site.zip'
if (Test-Path $zip) { Remove-Item $zip -Confirm:$false }
Add-Type -AssemblyName System.IO.Compression, System.IO.Compression.FileSystem
$arq = [IO.Compression.ZipFile]::Open($zip, 'Create')
foreach ($f in Get-ChildItem $site -Recurse -File) {
  # Caminhos com "/" para o Netlify (servidor Linux) achar css/ e js/.
  $rel = $f.FullName.Substring($site.Length + 1).Replace('\', '/')
  [void][IO.Compression.ZipFileExtensions]::CreateEntryFromFile($arq, $f.FullName, $rel)
}
$arq.Dispose()
"Pacote criado: $zip"
