# Segundo corte — Robótica

Práctica 1: manipulador UR5, realizada por Brayan Mateo Bravo Losada exclusivamente en simulación.

## Contenido

- `programas/`: programas PolyScope `.urp`, rutinas URScript y configuración.
- `exportados_desde_docker/`: archivos exportados literalmente desde el contenedor URSim.
- `docs/VIDEO.md`: espacio reservado para el enlace del video de demostración.
- Scripts Python y PowerShell: generación, ejecución, exportación y pruebas.

## Programas

1. `Programa_1_Iniciales_BMBL.urp`: iniciales BMBL y aviso antes de cada letra.
2. `Programa_2_ExternalControl.urp`: DO0 alto, confirmación, espera de 5 segundos y nodo External Control para ROS 2.
3. `Programa_3_PickPlace.urp`: dos recogidas y entregas, puntos intermedios, pinza lógica, payload y confirmación por entrada digital Modbus.

El bonus usa MoveIt para planificar y ejecutar tres trayectorias en URSim mediante `bonus_moveit.py`.

## Video de demostración

<details>
<summary><b>▶ Ver video: práctica del manipulador UR5</b> (clic para abrir o cerrar)</summary>
<br>

[Enlace del video](docs/VIDEO.md)

Estado: pendiente de agregar. Este repositorio todavía no contiene un video.

</details>

**El programa 2 completo es el archivo `.urp`. `Programa_2_PREAMBULO_NO_COMPLETO.script` no contiene el nodo External Control y no sustituye el programa completo.**

## Entorno utilizado

Windows, Ubuntu 24.04 en WSL, Docker, URSim CB3 / PolyScope 3.15.8, ROS 2 Kilted, driver de Universal Robots, MoveIt y URCap External Control.

Los lanzadores están adaptados al equipo donde se realizó la práctica: contenedor `ursim_cb3_pinza_gui`, URSim `172.17.0.2`, host Docker `172.17.0.1` y usuario WSL `brayan_mateo_bravo_l`. En otro equipo deben revisarse esas referencias antes de ejecutar. Se requiere disponer previamente del entorno y de los URCaps; el repositorio no instala ni distribuye sus binarios.

Desde PowerShell, dentro de esta carpeta:

```powershell
.\Iniciar_Practica.ps1
```

Mantener esa sesión abierta. Si la celda ya está activa, no iniciar una segunda copia. Desde otra sesión:

```powershell
.\Cargar_Programa.ps1 -Programa 1
# Elegir 2 o 3 para los otros programas; confirmar los mensajes en URSim.
```

Para el bonus, cargar el programa 2, confirmar su mensaje y esperar la conexión de External Control; después ejecutar `Ejecutar_Bonus.ps1`. Para exportar nuevamente, utilizar `Exportar_Programas.ps1`.

Interfaces locales:

- URSim: `http://localhost:6080/vnc.html?host=localhost&port=6080`
- Pinza y pulsador virtual: `http://localhost:40404/`

## Alcance

No hay conexión a un robot físico. La pinza se simula por estados mediante XML-RPC y DO1; no incluye física de contacto ni emula el protocolo propietario de Robotiq. La confirmación es una entrada digital discreta Modbus, no la entrada estándar DI0 del controlador.

Este repositorio contiene únicamente el código, los programas del manipulador, su configuración y documentación de uso. Las capturas, los registros de ejecución y el informe no se publican. Los scripts pueden generar una carpeta local `evidencias/`, que Git ignora.

## Pruebas

```bash
python3 -m unittest -v test_simulacion
```

Las cuatro pruebas verifican el estado lógico del efector, rechazo de recogidas fuera de alcance, lectura digital Modbus y geometría de las iniciales. No sustituyen la ejecución de los programas en URSim.
