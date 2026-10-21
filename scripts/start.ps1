param([string]$PythonPath = 'C:\Users\mayan\Documents\ChatGPT\twin-env\Scripts\python.exe')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $projectRoot
if (-not (Test-Path -LiteralPath $PythonPath)) { throw 'Supply -PythonPath pointing to a Python environment with requirements.txt installed.' }
New-Item -ItemType Directory -Force .runtime | Out-Null
$apiProcess = Start-Process -FilePath $PythonPath -ArgumentList '-m','uvicorn','backend.api:app','--host','127.0.0.1','--port','8000' -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput .runtime/api.log -RedirectStandardError .runtime/api-error.log -PassThru
$uiProcess = Start-Process -FilePath 'cmd.exe' -ArgumentList '/c','npm.cmd run dev --prefix frontend' -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput .runtime/ui.log -RedirectStandardError .runtime/ui-error.log -PassThru
Write-Output "API process: $($apiProcess.Id); dashboard process: $($uiProcess.Id)"
Write-Output 'Dashboard: http://127.0.0.1:5173 — logs: .runtime/'
