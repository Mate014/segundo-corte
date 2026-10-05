"""Repite solo las iniciales en URSim, confirmando sus popups de prueba.
Registra posiciones ejecutadas; no prueba ni controla hardware físico.
"""
import json
import time
from pathlib import Path
from control_ursim import dashboard, simulator_ip

ROOT = Path(__file__).resolve().parent


def main():
    simulator_ip()
    dashboard('stop')
    dashboard('load /ursim/programs/Programa_1_Iniciales_BMBL.urp')
    result = dashboard('play')
    if result != 'Starting program':
        raise RuntimeError(result)
    start = time.time()
    log = ROOT/'evidencias'/'eventos.jsonl'
    deadline = start+150
    while time.time()<deadline:
        rows = [json.loads(row) for row in log.read_text().splitlines() if row.strip()]
        rows = [row for row in rows if row['time'] >= start]
        if any(row['event']=='iniciales_terminadas' for row in rows):
            letters = [row['event'] for row in rows if row['event'].startswith('letra_')]
            if letters != ['letra_1_B','letra_2_M','letra_3_B','letra_4_L']:
                raise AssertionError(letters)
            report = dict(success=True,letters=letters, executed_events=rows,
                          note='Confirmaciones automaticas exclusivamente en esta prueba de URSim')
            (ROOT/'evidencias'/'verificacion_iniciales.json').write_text(json.dumps(report,indent=2))
            print('Iniciales BMBL completadas y registradas.',flush=True)
            return
        # Solo el programa conocido tiene popups ordinarios de letras.
        # No se confirma el popup de velocidad ni avisos de otras rutinas.
        dashboard('close popup')
        time.sleep(1)
    dashboard('stop')
    raise TimeoutError('Las iniciales no terminaron; revisar el simulador')


if __name__=='__main__':
    main()
