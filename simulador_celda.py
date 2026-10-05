"""Efector y pulsador virtuales. Solo red Docker/loopback, sin hardware.

XML-RPC para el efector; Modbus TCP FC02 para una ENTRADA DIGITAL real
del cliente Modbus de URSim (no se sustituye por una salida del robot).
No emula el URCap propietario de Robotiq ni la fisica de contacto.
"""
import argparse
import json
import math
import socketserver
import struct
import threading
import time
from pathlib import Path
from xmlrpc.server import SimpleXMLRPCRequestHandler, SimpleXMLRPCServer

ROOT = Path(__file__).resolve().parent


def xyz(pose):
    if isinstance(pose, dict):
        return [float(pose[k]) for k in ('x', 'y', 'z')]
    return list(map(float, pose[:3]))


class Cell:
    def __init__(self, log):
        self.lock = threading.RLock()
        self.log = Path(log)
        self.log.parent.mkdir(parents=True, exist_ok=True)
        self.state = dict(simulation=True, di=False, active=False, opening=85,
                          held=0, cycle=0, phase='Preparado', pieces={}, events=[])

    def record(self, event, **data):
        with self.lock:
            row = dict(time=time.time(), event=event, **data)
            self.state['events'].append(row)
            self.state['events'] = self.state['events'][-100:]
            with self.log.open('a', encoding='utf-8') as f:
                f.write(json.dumps(row, ensure_ascii=False) + '\n')
            print(json.dumps(row, ensure_ascii=False), flush=True)
        return True

    def event(self, name, pose):
        with self.lock:
            self.state['phase'] = name
            self.state['tcp'] = xyz(pose)
            return self.record(name, tcp=xyz(pose))

    def initialize(self):
        with self.lock:
            self.state.update(active=True, opening=85, held=0)
            return self.record('pinza_activada')

    def begin_cycle(self, pick1, pick2):
        with self.lock:
            if self.state['held']:
                raise ValueError('No se reinicia con carga sujeta')
            self.state['cycle'] += 1
            self.state['pieces'] = {str(i): dict(position=xyz(p), delivered=False)
                                    for i, p in enumerate((pick1, pick2), 1)}
            return self.record('ciclo_iniciado', cycle=self.state['cycle'])

    def close(self, piece, pose):
        with self.lock:
            target = self.state['pieces'][str(piece)]
            if not self.state['active'] or self.state['held']:
                raise ValueError('Pinza no activada o ya ocupada')
            error = math.dist(xyz(pose), target['position'])
            if error > 0.012 or target['delivered']:
                raise ValueError(f'Pieza fuera del alcance virtual: {error:.4f} m')
            self.state.update(held=piece, opening=35)
            return self.record('pieza_recogida', piece=piece, tcp=xyz(pose), error_m=error)

    def open(self, pose):
        with self.lock:
            piece = self.state['held']
            if piece:
                self.state['pieces'][str(piece)].update(position=xyz(pose), delivered=True)
            self.state.update(held=0, opening=85)
            return self.record('pieza_liberada', piece=piece, tcp=xyz(pose))

    def input(self, high):
        with self.lock:
            self.state['di'] = bool(high)
            return self.record('entrada_digital', high=bool(high))


class RPCServer(socketserver.ThreadingMixIn, SimpleXMLRPCServer):
    daemon_threads = True
    allow_reuse_address = True


class ModbusServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


class ModbusHandler(socketserver.BaseRequestHandler):
    def receive(self, length):
        buf = b''
        while len(buf) < length:
            chunk = self.request.recv(length - len(buf))
            if not chunk:
                return None
            buf += chunk
        return buf

    def handle(self):
        while True:
            header = self.receive(7)
            if header is None:
                return
            transaction, protocol, length, unit = struct.unpack('>HHHB', header)
            if protocol != 0 or not 2 <= length <= 254:
                return
            pdu = self.receive(length - 1)
            if pdu is None:
                return
            if pdu[0] == 2 and len(pdu) == 5:
                address, quantity = struct.unpack('>HH', pdu[1:])
                if address == 0 and quantity == 1:
                    result = bytes([2, 1, int(self.server.cell.state['di'])])
                else:
                    result = bytes([0x82, 2])
            else:
                result = bytes([pdu[0] | 0x80, 1])
            self.request.sendall(struct.pack('>HHHB', transaction, 0, len(result)+1, unit)+result)


PANEL = r'''<!doctype html><html lang="es"><meta charset="utf-8"><title>UR5 · Celda virtual</title>
<style>body{background:#101923;color:#eaf0f6;font:17px system-ui;max-width:850px;margin:35px auto;padding:20px}h1{font-size:28px}button{background:#68ded0;color:#071e29;border:0;border-radius:8px;padding:15px;margin:6px;font-size:17px}pre{white-space:pre-wrap;background:#1b2c3b;padding:20px;border-radius:12px}svg{background:#203344;border-radius:12px;width:100%}.muted{color:#a9bdcd}</style>
<h1>UR5 — Celda de práctica simulada</h1><p class="muted">Efector lógico de dos dedos · Sin robot físico · Sin simulación dinámica de contacto</p>
<svg viewBox="0 0 700 170"><rect x="200" y="20" width="180" height="35" fill="#91a7ba"/><rect id="left" x="200" y="55" width="20" height="90" fill="#68ded0"/><rect id="right" x="360" y="55" width="20" height="90" fill="#68ded0"/><rect id="load" x="270" y="100" width="45" height="45" fill="#ffb763"/><text id="status" x="420" y="80" fill="white" font-size="22"></text></svg>
<p>Entrada digital Modbus: <strong id="di"></strong></p><button onclick="setDI(1)">Confirmar nuevo ciclo (ALTO)</button><button onclick="setDI(0)">Soltar pulsador (BAJO)</button>
<p class="muted">Soltar → confirmar: se exige un flanco nuevo al terminar cada ciclo. Las piezas se reponen virtualmente al iniciar el siguiente.</p><pre id="summary"></pre><pre id="events"></pre>
<script>async function setDI(x){await fetch('/di/'+x,{method:'POST'});update()}async function update(){let s=await(await fetch('/state')).json();document.querySelector('#di').textContent=s.di?'ALTO':'BAJO';document.querySelector('#left').setAttribute('x',s.held?245:200);document.querySelector('#right').setAttribute('x',s.held?315:360);document.querySelector('#load').style.display=s.held?'block':'none';document.querySelector('#status').textContent=s.held?'Pieza '+s.held:'Abierta';document.querySelector('#summary').textContent=JSON.stringify({...s,events:undefined},null,2);document.querySelector('#events').textContent=s.events.slice(-8).map(x=>new Date(x.time*1000).toLocaleTimeString()+' · '+x.event).join('\n')}setInterval(update,700);update()</script></html>'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--log', default=str(ROOT/'evidencias'/'eventos.jsonl'))
    args = parser.parse_args()
    cell = Cell(args.log)

    class Handler(SimpleXMLRPCRequestHandler):
        rpc_paths = ('/RPC2',)
        protocol_version = 'HTTP/1.1'

        def reply(self, body, content_type):
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == '/state':
                with cell.lock:
                    self.reply(json.dumps(cell.state).encode(), 'application/json')
            elif self.path == '/':
                self.reply(PANEL.encode(), 'text/html; charset=utf-8')
            elif self.path == '/bonus':
                evidence = ROOT/'evidencias'/'bonus_moveit.json'
                if not evidence.exists():
                    self.send_error(404, 'Bonus no ejecutado todavia')
                    return
                data = json.loads(evidence.read_text())
                results = json.dumps(data['results'],indent=2)
                html = '<!doctype html><meta charset="utf-8"><title>Evidencia MoveIt</title><style>body{font:17px system-ui;margin:35px;background:#101923;color:#eaf0f6}pre{white-space:pre-wrap;font-size:14px}</style><h1>ROS 2 + MoveIt + URSim</h1><p>Resultados medidos de planificacion y ejecucion. No hardware fisico.</p><p>Estados articulares registrados: '+str(len(data['joint_states']))+'</p><pre>'+results+'</pre>'
                self.reply(html.encode(), 'text/html; charset=utf-8')
            else:
                self.send_error(404)

        def do_POST(self):
            if self.path in ('/di/0', '/di/1'):
                cell.input(self.path.endswith('1'))
                self.reply(b'OK', 'text/plain')
            else:
                super().do_POST()

        def log_message(self, *_):
            pass

    # Exclusively the Docker gateway and localhost; do not expose on LAN.
    servers = []
    for host in ('172.17.0.1', '127.0.0.1'):
        rpc = RPCServer((host, 40404), requestHandler=Handler, allow_none=False, logRequests=False)
        for name in ('initialize', 'begin_cycle', 'close', 'open', 'event'):
            rpc.register_function(getattr(cell, name), name)
        servers.append(rpc)
    modbus = ModbusServer(('172.17.0.1', 502), ModbusHandler)
    modbus.cell = cell
    servers.append(modbus)
    for server in servers:
        threading.Thread(target=server.serve_forever, daemon=True).start()
    cell.record('servidor_listo', rpc_port=40404, modbus_port=502)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        for server in servers:
            server.shutdown()


if __name__ == '__main__':
    main()
