# Uso: .\Cargar_Programa.ps1 -Programa 1 (o 2 o 3).
# Iniciar_Practica.ps1 debe seguir abierto. Confirmar los popups en URSim.
param([Parameter(Mandatory=$true)][ValidateSet('1','2','3')][string]$Programa)
$ErrorActionPreference = 'Stop'
$taskLinuxDirectory = (& wsl -d Ubuntu-24.04 -- wslpath -a $PSScriptRoot).Trim()
$taskPrograms = @{'1'='Programa_1_Iniciales_BMBL';'2'='Programa_2_ExternalControl';'3'='Programa_3_PickPlace'}
& wsl -d Ubuntu-24.04 -u root -- python3 "$taskLinuxDirectory/control_ursim.py" stop
& wsl -d Ubuntu-24.04 -u root -- python3 "$taskLinuxDirectory/control_ursim.py" cargar $taskPrograms[$Programa]
& wsl -d Ubuntu-24.04 -u root -- python3 "$taskLinuxDirectory/control_ursim.py" encender
& wsl -d Ubuntu-24.04 -u root -- python3 "$taskLinuxDirectory/control_ursim.py" play
