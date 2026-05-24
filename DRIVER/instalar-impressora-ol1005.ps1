param(
  [string]$PrinterName = "OL-1005 USB",
  [string]$DriverName = "Generic / Text Only",
  [string]$PortName = "USB001",
  [string]$DriverDir = ".\driver\POS58 DRIVER"
)

$ErrorActionPreference = "Stop"

Write-Host "Instalando impressora termica..." -ForegroundColor Cyan

$driverCandidates = @(
  $DriverDir,
  (Join-Path $PSScriptRoot 'POS58 DRIVER'),
  (Join-Path (Get-Location).Path 'POS58 DRIVER'),
  (Join-Path $env:USERPROFILE 'Downloads\POS58 DRIVER')
) | Where-Object { $_ -and (Test-Path $_) }

$resolvedDriverDir = $driverCandidates | Select-Object -First 1
if ($resolvedDriverDir) {
  $infFiles = Get-ChildItem -Path $resolvedDriverDir -Recurse -Filter *.inf -ErrorAction SilentlyContinue
  foreach ($inf in $infFiles) {
    Write-Host ("Instalando INF: " + $inf.FullName) -ForegroundColor Yellow
    pnputil /add-driver $inf.FullName /install | Out-Null
  }
} else {
  Write-Host "Pasta de driver nao encontrada. Continuando com driver do Windows." -ForegroundColor DarkYellow
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
try {
  Get-Content -Path $tmp | Out-Printer -Name $PrinterName
  Write-Host "Teste de impressao enviado." -ForegroundColor Green
} catch {
  Write-Host "Nao foi possivel enviar teste de impressao automaticamente: $($_.Exception.Message)" -ForegroundColor Yellow
  Write-Host "A impressora foi cadastrada. Faça um teste manual nas configuracoes do Windows." -ForegroundColor Yellow
}

Write-Host "Concluido. Impressora configurada." -ForegroundColor Green
