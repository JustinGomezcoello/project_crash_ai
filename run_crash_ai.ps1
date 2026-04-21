# Script para ejecutar project_crash_ai dentro del entorno crash_ai
# Uso: .\run_crash_ai.ps1 [opción]
#   sin argumentos: ejecuta main.py
#   "activate": abre una sesión PowerShell con el entorno activo
#   "install <paquete>": instala un paquete con pip en el entorno
#   "test": verifica que numpy, cv2 y ultralytics funcionan

param(
    [string]$Action = "run",
    [string]$Package = ""
)

$CondaExe = "D:\miniconda\Scripts\conda.exe"
$EnvName = "crash_ai"

if (-not (Test-Path $CondaExe)) {
    Write-Host "Error: conda.exe no encontrado en $CondaExe" -ForegroundColor Red
    exit 1
}

Write-Host "Usando entorno: $EnvName" -ForegroundColor Green

switch ($Action) {
    "run" {
        Write-Host "Ejecutando main.py..." -ForegroundColor Cyan
        & $CondaExe run -n $EnvName python main.py
    }
    
    "activate" {
        Write-Host "Activando entorno $EnvName en la sesión actual..." -ForegroundColor Cyan
        & $CondaExe activate $EnvName
    }
    
    "test" {
        Write-Host "Verificando dependencias..." -ForegroundColor Cyan
        & $CondaExe run -n $EnvName python -c "import sys, numpy, cv2, ultralytics; print('Python:', sys.version.split()[0]); print('NumPy:', numpy.__version__); print('OpenCV:', cv2.__version__); print('UltraLytics:', ultralytics.__version__)"
    }
    
    "install" {
        if ($Package -eq "") {
            Write-Host "Uso: .\run_crash_ai.ps1 install <nombre_paquete>" -ForegroundColor Yellow
            exit 1
        }
        Write-Host "Instalando $Package en el entorno $EnvName..." -ForegroundColor Cyan
        & $CondaExe run -n $EnvName pip install $Package
    }
    
    default {
        Write-Host "Opciones disponibles:" -ForegroundColor Yellow
        Write-Host "  .\run_crash_ai.ps1                      # ejecutar main.py" -ForegroundColor Gray
        Write-Host "  .\run_crash_ai.ps1 run                  # ejecutar main.py" -ForegroundColor Gray
        Write-Host "  .\run_crash_ai.ps1 activate             # activar entorno en sesión actual" -ForegroundColor Gray
        Write-Host "  .\run_crash_ai.ps1 test                 # verificar dependencias" -ForegroundColor Gray
        Write-Host "  .\run_crash_ai.ps1 install <paquete>    # instalar paquete con pip" -ForegroundColor Gray
        exit 0
    }
}
