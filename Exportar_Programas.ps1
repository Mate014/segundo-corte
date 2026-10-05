# Exportación literal desde Docker a una carpeta distinta de las fuentes.
$ErrorActionPreference = 'Stop'
$taskExportDirectory = Join-Path $PSScriptRoot 'exportados_desde_docker'
New-Item -ItemType Directory -Path $taskExportDirectory -Force | Out-Null
$taskLinuxExport = (& wsl -d Ubuntu-24.04 -- wslpath -a $taskExportDirectory).Trim()
$taskNames = @('Programa_1_Iniciales_BMBL.urp','Programa_2_ExternalControl.urp','Programa_3_PickPlace.urp','practica_simulacion.installation','practica_simulacion.variables','Programa_1_Iniciales_BMBL_rutina.script','Programa_2_ExternalControl_rutina.script','Programa_2_devolver.script','Programa_3_PickPlace_rutina.script')
foreach ($taskName in $taskNames) {
    & wsl -d Ubuntu-24.04 -u root -- docker cp "ursim_cb3_pinza_gui:/ursim/programs/$taskName" "$taskLinuxExport/$taskName"
    if ($LASTEXITCODE -ne 0) { throw "No se exportó $taskName" }
}
Write-Host "Programas exportados desde Docker a $taskExportDirectory"
