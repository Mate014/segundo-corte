"""Operaciones exclusivamente sobre el contenedor URSim conocido.
No acepta IPs o nombres de contenedores arbitrarios.
"""
import argparse
import json
import socket
import subprocess
import time
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent


@lru_cache(maxsize=1)
def simulator_ip():
    data = json.loads(subprocess.check_output(['docker', 'inspect', 'ursim_cb3_pinza_gui']))[0]
    if not data['Config']['Image'].startswith('universalrobots/ursim_cb3'):
        raise RuntimeError('El destino no es el simulador CB3 autorizado')
    ip = data['NetworkSettings']['Networks']['bridge']['IPAddress']
    if ip != '172.17.0.2' or not data['State']['Running']:
        raise RuntimeError('La IP/estado del simulador cambió; revisar antes de ejecutar')
    return ip


def dashboard(command):
    with socket.create_connection((simulator_ip(), 29999), timeout=15) as sock:
        sock.recv(4096)
        sock.sendall((command+'\n').encode())
        output = sock.recv(8192).decode(errors='replace').strip()
        print(output, flush=True)
        return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['estado', 'encender', 'cargar', 'play', 'stop', 'cerrar_popup', 'enviar_script'])
    parser.add_argument('program', nargs='?')
    args = parser.parse_args()
    if args.command == 'estado':
        for cmd in ('robotmode', 'safetymode', 'programState', 'get loaded program'):
            dashboard(cmd)
    elif args.command == 'encender':
        if 'RUNNING' in dashboard('robotmode'):
            return
        dashboard('power on')
        for _ in range(30):
            if 'IDLE' in dashboard('robotmode'):
                break
            time.sleep(0.5)
        dashboard('brake release')
    elif args.command == 'cargar':
        if args.program not in ('Programa_1_Iniciales_BMBL', 'Programa_2_ExternalControl', 'Programa_3_PickPlace'):
            parser.error('Programa no autorizado')
        dashboard('load /ursim/programs/'+args.program+'.urp')
    elif args.command == 'cerrar_popup':
        dashboard('close popup')
    elif args.command == 'enviar_script':
        file = (ROOT/'programas'/str(args.program)).resolve()
        if file.parent != (ROOT/'programas').resolve() or file.suffix != '.script':
            parser.error('Solo scripts generados dentro de programas')
        with socket.create_connection((simulator_ip(),30002), timeout=10) as sock:
            sock.sendall(file.read_bytes()+b'\n')
    else:
        dashboard(args.command)


if __name__ == '__main__':
    main()
