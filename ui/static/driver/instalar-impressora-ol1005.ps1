$ErrorActionPreference = "Stop"

param(
  [string]$PrinterName = "OL-1005 USB",
  [string]$DriverName = "Generic / Text Only",
  [string]$PortName = "USB001",
  [string]$DriverDir = ".\POS58 DRIVER"
)

Write-Host "Instalando impressora termica OL-1005..." -ForegroundColor Cyan

try {
  $current = [Security.Principal.WindowsIdentity]::GetCurrent()
  $principal = New-Object Security.Principal.WindowsPrincipal($current)
  if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Execute este script como Administrador."
  }
} catch {
  throw "Falha ao validar permissao de administrador. $_"
}

if (Test-Path $DriverDir) {
  Write-Host "Instalando INF da pasta: $DriverDir" -ForegroundColor Yellow
  $infFiles = Get-ChildItem -Path $DriverDir -Recurse -Filter *.inf -ErrorAction SilentlyContinue
  foreach ($inf in $infFiles) {
    pnputil /add-driver $inf.FullName /install | Out-Null
  }
} else {
  Write-Host "Pasta de driver nao encontrada ($DriverDir). Continuando com driver do Windows." -ForegroundColor DarkYellow
}

if (-not (Get-PrinterDriver -Name $DriverName -ErrorAction SilentlyContinue)) {
  $fallback = Get-PrinterDriver -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($fallback -and $fallback.Name) {
    $DriverName = $fallback.Name
  }
}

if (-not (Get-PrinterDriver -Name $DriverName -ErrorAction SilentlyContinue)) {
  throw "Nao foi possivel localizar driver de impressora no Windows."
}

if (-not (Get-PrinterPort -Name $PortName -ErrorAction SilentlyContinue)) {
  try { Add-PrinterPort -Name $PortName } catch {}
}

if (Get-Printer -Name $PrinterName -ErrorAction SilentlyContinue) {
  Set-Printer -Name $PrinterName -DriverName $DriverName -PortName $PortName
} else {
  Add-Printer -Name $PrinterName -DriverName $DriverName -PortName $PortName
}

$testText = @(
  "*******************************",
  " TESTE IMPRESSORA OL-1005",
  " Data/Hora: $((Get-Date).ToString('dd/MM/yyyy HH:mm:ss'))",
  "*******************************",
  ""
) -join [Environment]::NewLine

$tmp = Join-Path $env:TEMP "teste-ol1005.txt"
Set-Content -Path $tmp -Value $testText -Encoding ASCII
Get-Content -Path $tmp | Out-Printer -Name $PrinterName

Write-Host "Concluido. Impressora configurada e teste enviado." -ForegroundColor Green
