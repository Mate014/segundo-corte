import json
import socket
import struct
import tempfile
import threading
import unittest
from pathlib import Path
from simulador_celda import Cell, ModbusServer, ModbusHandler
from generar_programas import letter_paths


class SimulationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.cell = Cell(Path(self.temp.name)/'events.jsonl')

    def tearDown(self):
        self.temp.cleanup()

    def test_gripper_state_and_payload(self):
        self.cell.initialize()
        self.cell.begin_cycle([0,0,0], [1,0,0])
        self.cell.close(1,[0,0,0])
        self.assertEqual(self.cell.state['held'],1)
        self.assertEqual(self.cell.state['opening'],35)
        with self.assertRaises(ValueError):
            self.cell.close(2,[1,0,0])
        self.cell.open([0,1,0])
        self.assertEqual(self.cell.state['held'],0)
        self.assertEqual(self.cell.state['pieces']['1']['position'],[0,1,0])
        self.assertTrue(self.cell.state['pieces']['1']['delivered'])
        with self.assertRaises(ValueError):
            self.cell.close(1,[0,1,0])

    def test_reject_pick_outside_virtual_piece(self):
        self.cell.initialize()
        self.cell.begin_cycle([0,0,0], [1,0,0])
        with self.assertRaises(ValueError):
            self.cell.close(1,[0,0,0.05])

    def test_modbus_discrete_input_low_and_high(self):
        server = ModbusServer(('127.0.0.1',0), ModbusHandler)
        server.cell = self.cell
        worker = threading.Thread(target=server.serve_forever,daemon=True)
        worker.start()
        try:
            with socket.create_connection(server.server_address) as sock:
                for high in (False,True,False):
                    self.cell.input(high)
                    sock.sendall(struct.pack('>HHHBBHH',1,0,6,255,2,0,1))
                    response = b''
                    while len(response)<10:
                        response += sock.recv(10-len(response))
                    self.assertEqual(response[-3:],bytes([2,1,int(high)]))
        finally:
            server.shutdown()
            server.server_close()

    def test_initial_geometries_in_normalized_plane(self):
        for letter in 'BMBL':
            for stroke in letter_paths(letter):
                self.assertGreaterEqual(len(stroke),2)
                for x,y in stroke:
                    self.assertTrue(0<=x<=1 and 0<=y<=1)
        upper,lower = letter_paths('B')[1:]
        self.assertEqual(upper[-1],(0,.5))
        self.assertEqual(lower[-1],(0,0))


if __name__=='__main__':
    unittest.main(verbosity=2)
