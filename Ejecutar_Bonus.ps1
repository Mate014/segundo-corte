# Primero cargar programa 2 y confirmar su popup. Esperar 5 segundos.
$ErrorActionPreference = 'Stop'
$taskLinuxDirectory = (& wsl -d Ubuntu-24.04 -- wslpath -a $PSScriptRoot).Trim()
& wsl -d Ubuntu-24.04 -u brayan_mateo_bravo_l -- bash -lc "source /opt/ros/kilted/setup.bash; python3 '$taskLinuxDirectory/bonus_moveit.py'"
