"""Mantiene WSL y los cuatro procesos de la celda vivos en una sola sesión."""
import json
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def occupied(port):
    with socket.socket() as s:
        s.settimeout(0.3)
        return s.connect_ex(('127.0.0.1',port)) == 0


def main():
    if occupied(40404) or occupied(50001):
        raise SystemExit('La celda/driver ya está en marcha. No se iniciará una copia duplicada.')
    output = ROOT/'evidencias'/'logs'
    output.mkdir(parents=True, exist_ok=True)
    processes, handles = [], []

    def start(name, args):
        handle = (output/(name+'.log')).open('a')
        handles.append(handle)
        process = subprocess.Popen(args, stdout=handle, stderr=subprocess.STDOUT, start_new_session=True)
        processes.append(process)
        print(f'{name}: PID {process.pid}', flush=True)
        return process

    docker = start('ursim', ['docker','start','-a','ursim_cb3_pinza_gui'])
    for _ in range(60):
        with socket.socket() as s:
            s.settimeout(0.4)
            if s.connect_ex(('172.17.0.2',29999)) == 0:
                break
        if docker.poll() is not None:
            raise SystemExit('URSim no inició. Consultar evidencias/logs/ursim.log')
        time.sleep(1)
    try:
        start('celda', [sys.executable,str(ROOT/'simulador_celda.py')])
        time.sleep(1)
        subprocess.run([sys.executable,str(ROOT/'generar_programas.py')],check=True)
        subprocess.run(['docker','cp',str(ROOT/'programas')+'/.','ursim_cb3_pinza_gui:/ursim/programs/'],check=True)
        setup = 'source /opt/ros/kilted/setup.bash; '
        start('driver_ros2', ['runuser','-u','brayan_mateo_bravo_l','--','bash','-lc',setup+'ros2 launch ur_robot_driver ur_control.launch.py ur_type:=ur5 robot_ip:=172.17.0.2 reverse_ip:=172.17.0.1 headless_mode:=false launch_rviz:=false activate_joint_controller:=false'])
        time.sleep(6)
        start('moveit', ['runuser','-u','brayan_mateo_bravo_l','--','bash','-lc',setup+'ros2 launch ur_moveit_config ur_moveit.launch.py ur_type:=ur5 launch_rviz:=false'])
        print('URSim: http://localhost:6080/vnc.html?host=localhost&port=6080',flush=True)
        print('Pinza y pulsador: http://localhost:40404',flush=True)
        print('Mantener esta sesión abierta. Ctrl+C termina los procesos de esta sesión.',flush=True)
        while True:
            if any(p.poll() is not None for p in processes):
                raise RuntimeError('Terminó un proceso: consultar evidencias/logs')
            time.sleep(2)
    except KeyboardInterrupt:
        pass
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                import os
                os.killpg(process.pid,signal.SIGINT)
        for process in processes:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.terminate()
        for handle in handles:
            handle.close()


if __name__=='__main__':
    main()
