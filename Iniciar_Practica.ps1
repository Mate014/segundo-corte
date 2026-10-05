# Ejecutar desde PowerShell y mantener esta sesión abierta.
# Solo usa el contenedor URSim existente; no conecta ningún robot físico.
$ErrorActionPreference = 'Stop'
$taskDirectory = $PSScriptRoot
$taskLinuxDirectory = (& wsl -d Ubuntu-24.04 -- wslpath -a $taskDirectory).Trim()
& wsl -d Ubuntu-24.04 -u root -- python3 "$taskLinuxDirectory/ejecutar_stack.py"
