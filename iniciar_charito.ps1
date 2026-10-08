# iniciar_charito.ps1
# Arrancar el servidor Charito

$ruta = "C:\charito"
Set-Location $ruta
& "$ruta\venv\Scripts\python.exe" "$ruta\serve.py"
