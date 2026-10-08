# instalar_servidor.ps1
# Ejecutar como Administrador en el Windows Server

$ruta = "C:\charito"
$python = "python"

Write-Host "=== Instalando Charito en Windows Server ===" -ForegroundColor Cyan

# 1. Crear entorno virtual
Write-Host "`n[1] Creando entorno virtual..." -ForegroundColor Yellow
& $python -m venv "$ruta\venv"

# 2. Activar e instalar dependencias
Write-Host "`n[2] Instalando dependencias..." -ForegroundColor Yellow
& "$ruta\venv\Scripts\pip.exe" install -r "$ruta\requirements.txt"

# 3. Recolectar archivos estáticos
Write-Host "`n[3] Recolectando estáticos..." -ForegroundColor Yellow
& "$ruta\venv\Scripts\python.exe" "$ruta\manage.py" collectstatic --noinput

# 4. Aplicar migraciones
Write-Host "`n[4] Aplicando migraciones..." -ForegroundColor Yellow
& "$ruta\venv\Scripts\python.exe" "$ruta\manage.py" migrate

Write-Host "`n=== Listo. Ejecuta 'iniciar_charito.ps1' para arrancar ===" -ForegroundColor Green
