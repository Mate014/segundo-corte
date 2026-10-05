"""Genera URScript y árboles URP (gzip XML) para PolyScope CB3 3.15.
No se exportan binarios ni código del URCap Robotiq.
"""
import gzip
import json
import math
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT/'programas'
CFG = json.loads((ROOT/'config.json').read_text(encoding='utf-8'))
HOME = str(CFG['home'])


def script_node(parent, code, name):
    node = ET.SubElement(parent, 'Script', type='File')
    ET.SubElement(node, 'cachedContents').text = code+'\n'
    ET.SubElement(node, 'file', {'resolves-to':'file'}).text = '/ursim/programs/'+name+'.script'
    (OUT/(name+'.script')).write_text(code+'\n', encoding='utf-8')
    return node


def root_program(name):
    root = ET.Element('URProgram', createdIn='3.15.8.106339', lastSavedIn='3.15.8.106339',
                      name=name, directory='/ursim/programs', installation='practica_simulacion',
                      installationRelativePath='practica_simulacion', robotSerialNumber='2018359999', crcValue='2588156642')
    k = ET.SubElement(root, 'kinematics', status='NOT_INITIALIZED', validChecksum='false')
    for name_, value in dict(deltaTheta='0, 0, 0, 0, 0, 0', a='0, -0.425, -0.39225, 0, 0, 0',
                             d='0.089159, 0, 0, 0.10915, 0.09465, 0.0823',
                             alpha='1.570796327, 0, 0, 1.570796327, -1.570796327, 0',
                             jointChecksum='-1, -1, -1, -1, -1, -1').items():
        ET.SubElement(k, name_, value=value)
    children = ET.SubElement(root, 'children')
    main = ET.SubElement(children, 'MainProgram', runOnlyOnce='true', motionType='MoveJ',
                         speed='0.4', acceleration='0.6', useActiveTCP='true')
    return root, ET.SubElement(main, 'children')


def save(name, body, external=False):
    root, nodes = root_program(name)
    ET.SubElement(nodes, 'Comment', comment='SOLO URSim — Brayan Mateo Bravo Losada')
    script_node(nodes, body, name+'_rutina')
    if external:
        contribution = ET.SubElement(nodes, 'Contributed', strategyClass='com.fzi.externalcontrol.ExternalControlNode',
                      strategyProgramNodeType='External Control', strategyURCapDeveloper='FZI Research Center for Information Technology',
                      strategyURCapName='External Control')
        ET.SubElement(contribution,'dataModel')
        script_node(nodes, 'set_standard_digital_out(0, False)\nsim.event("control_devuelto", get_actual_tcp_pose())', 'Programa_2_devolver')
    ET.indent(root)
    (OUT/(name+'.urp')).write_bytes(gzip.compress(ET.tostring(root, encoding='utf-8')))
    wrapped = 'def '+name+'():\n'+''.join('  '+line+'\n' for line in body.splitlines())+'end\n'
    (OUT/(name+'.script')).write_text(wrapped, encoding='utf-8')
    (OUT/(name+'.txt')).write_text(body, encoding='utf-8')


RPC = f'sim = rpc_factory("xmlrpc", "http://{CFG["servidor_ip"]}:40404/RPC2")'
SETUP = f'''{RPC}
set_tcp(p[0,0,0,0,0,0])
set_payload({CFG['masa_pinza_kg']}, [0,0,0.04])
movej({HOME}, a=0.6, v=0.4)
base = get_actual_tcp_pose()
def punto(dx, dy, dz):
  return p[base[0]+dx,base[1]+dy,base[2]+dz,base[3],base[4],base[5]]
end'''


def letter_paths(letter):
    if letter == 'M':
        return [[(0,0),(0,1),(.5,.45),(1,1),(1,0)]]
    if letter == 'L':
        return [[(0,1),(0,0),(1,0)]]
    if letter == 'B':
        upper = [(0,1),(.48,1)] + [(.48+.52*math.sin(t),.75+.25*math.cos(t)) for t in [i*math.pi/8 for i in range(1,9)]] + [(0,.5)]
        lower = [(0,.5),(.48,.5)] + [(.48+.52*math.sin(t),.25+.25*math.cos(t)) for t in [i*math.pi/8 for i in range(1,9)]] + [(0,0)]
        return [[(0,0),(0,1)],upper,lower]
    raise ValueError('Falta definir geometría para '+letter)


def initials():
    lines = [SETUP, 'sim.event("iniciales_iniciadas", get_actual_tcp_pose())']
    letters = CFG['iniciales']
    for index, letter in enumerate(letters):
        lines.append(f'popup("Letra {letter} — inicial {index+1}: Brayan Mateo Bravo Losada", title="Programa 1", blocking=True)')
        lines.append(f'sim.event("letra_{index+1}_{letter}", get_actual_tcp_pose())')
        for stroke in letter_paths(letter):
            x, y = stroke[0]
            dx = -.09 + index*.05 + x*.035
            dy = -.035 + y*.07
            lines.extend([f'movel(punto({dx:.6f},{dy:.6f},0.03), a=0.3, v=0.08)',
                          f'movel(punto({dx:.6f},{dy:.6f},0), a=0.3, v=0.06)'])
            for x, y in stroke[1:]:
                lines.append(f'movel(punto({-.09+index*.05+x*.035:.6f},{-.035+y*.07:.6f},0), a=0.3, v=0.06)')
                lines.append('sim.event("trazo", get_actual_tcp_pose())')
            x, y = stroke[-1]
            lines.append(f'movel(punto({-.09+index*.05+x*.035:.6f},{-.035+y*.07:.6f},0.03), a=0.3, v=0.08)')
    lines.extend(['sim.event("iniciales_terminadas", get_actual_tcp_pose())', f'movej({HOME}, a=0.6, v=0.4)'])
    return '\n'.join(lines)


def pick_place():
    return SETUP + f'''
modbus_add_signal("{CFG['servidor_ip']}", 255, 0, 0, "CONFIRMAR_CICLO", False)
modbus_set_signal_update_frequency("CONFIRMAR_CICLO", 10)
sim.initialize()
pick1 = punto(-0.05,-0.06,-0.06)
pick2 = punto(0.05,-0.06,-0.06)
dest1 = punto(-0.05,0.08,-0.06)
dest2 = punto(0.05,0.08,-0.06)
while True:
  sim.begin_cycle(pick1, pick2)
  pieza = 1
  while pieza <= 2:
    if pieza == 1:
      recogida = pick1
      llegada = dest1
    else:
      recogida = pick2
      llegada = dest2
    end
    arriba_recogida = p[recogida[0],recogida[1],recogida[2]+0.10,recogida[3],recogida[4],recogida[5]]
    arriba_llegada = p[llegada[0],llegada[1],llegada[2]+0.10,llegada[3],llegada[4],llegada[5]]
    movel(arriba_recogida, a=0.3, v=0.1)
    movel(recogida, a=0.3, v=0.07)
    sim.close(pieza, get_actual_tcp_pose())
    set_standard_digital_out(1, True)
    set_payload({CFG['masa_pinza_kg']+CFG['masa_pieza_kg']}, [0,0,0.04])
    movel(arriba_recogida, a=0.3, v=0.1)
    sim.event("intermedio_sobre_recogida", get_actual_tcp_pose())
    sleep(0.3)
    movel(arriba_llegada, a=0.3, v=0.1)
    sim.event("intermedio_sobre_llegada", get_actual_tcp_pose())
    sleep(0.3)
    movel(llegada, a=0.3, v=0.07)
    sim.open(get_actual_tcp_pose())
    set_standard_digital_out(1, False)
    set_payload({CFG['masa_pinza_kg']}, [0,0,0.04])
    movel(arriba_llegada, a=0.3, v=0.1)
    pieza = pieza + 1
  end
  sim.event("esperando_entrada_baja", get_actual_tcp_pose())
  while modbus_get_signal_status("CONFIRMAR_CICLO"):
    sleep(0.05)
  end
  sim.event("esperando_confirmacion_alta", get_actual_tcp_pose())
  while not modbus_get_signal_status("CONFIRMAR_CICLO"):
    sleep(0.05)
  end
  sim.event("confirmacion_recibida", get_actual_tcp_pose())
end'''


def installation():
    source = Path('/home/brayan_mateo_bravo_l/.ursim/programs/default.installation')
    if not source.exists():
        raise RuntimeError('Ejecutar generador en WSL con la instalación existente')
    root = ET.fromstring(gzip.decompress(source.read_bytes()))
    root.set('fileName', 'practica_simulacion')
    for cap in root.findall('.//Contributed'):
        if cap.attrib.get('ownerId') == 'com.fzi.externalcontrol':
            for child in list(cap):
                cap.remove(child)
            for key, value in dict(host_ip=CFG['servidor_ip'], port_nr='50002', name='ROS2_SIMULADO').items():
                ET.SubElement(cap, 'data', key=key, value=value)
    ET.indent(root)
    (OUT/'practica_simulacion.installation').write_bytes(gzip.compress(ET.tostring(root)))
    variables = source.with_name('default.variables')
    if variables.exists():
        shutil.copy2(variables, OUT/'practica_simulacion.variables')


def main():
    OUT.mkdir(exist_ok=True)
    save('Programa_1_Iniciales_BMBL', initials())
    prelude = f'''{RPC}
set_standard_digital_out({CFG['salida_control']}, True)
sim.event("salida_control_alta", get_actual_tcp_pose())
popup("El control se compartira con ROS 2 simulado 5 segundos despues de confirmar.", title="Programa 2", blocking=True)
sim.event("popup_control_confirmado", get_actual_tcp_pose())
sleep(5.0)
sim.event("espera_5s_terminada", get_actual_tcp_pose())'''
    save('Programa_2_ExternalControl', prelude, external=True)
    # The .script for program 2 is a prelude only; External Control is in .urp.
    (OUT/'Programa_2_ExternalControl.script').rename(OUT/'Programa_2_PREAMBULO_NO_COMPLETO.script')
    save('Programa_3_PickPlace', pick_place())
    installation()
    print('Generados programas en', OUT)


if __name__ == '__main__':
    main()
