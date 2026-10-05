"""Planifica y ejecuta con MoveIt, guardando estados reales del URSim.
Debe estar activo el programa 2, después del popup y los 5 segundos.
"""
import json
import time
from pathlib import Path
import xml.etree.ElementTree as ET
import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy
from sensor_msgs.msg import JointState
from std_msgs.msg import Bool, String
from std_srvs.srv import Trigger
from moveit_msgs.msg import Constraints, JointConstraint, MoveItErrorCodes
from moveit_msgs.srv import GetMotionPlan
from moveit_msgs.action import ExecuteTrajectory
from controller_manager_msgs.srv import SwitchController

ROOT = Path(__file__).resolve().parent
JOINTS = ['shoulder_pan_joint', 'shoulder_lift_joint', 'elbow_joint',
          'wrist_1_joint', 'wrist_2_joint', 'wrist_3_joint']
HOME = json.loads((ROOT/'config.json').read_text())['home']


class Bonus(Node):
    def __init__(self):
        super().__init__('bonus_moveit_ursim')
        self.current = None
        self.running = False
        self.simulator_verified = False
        self.samples = []
        self.create_subscription(JointState, '/joint_states', self.joints, 10)
        self.create_subscription(Bool, '/io_and_status_controller/robot_program_running', self.program_running,
                                 QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL))
        self.create_subscription(String, '/robot_description', self.description,
                                 QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL))
        self.planner = self.create_client(GetMotionPlan, '/plan_kinematic_path')
        self.execute = ActionClient(self, ExecuteTrajectory, '/execute_trajectory')
        self.handback = self.create_client(Trigger, '/io_and_status_controller/hand_back_control')
        self.switch = self.create_client(SwitchController, '/controller_manager/switch_controller')

    def joints(self, msg):
        self.current = msg
        if len(self.samples) == 0 or time.time()-self.samples[-1]['time'] > 0.08:
            self.samples.append(dict(time=time.time(), names=list(msg.name), positions=list(msg.position)))

    def program_running(self, msg):
        self.running = msg.data

    def description(self, msg):
        root = ET.fromstring(msg.data)
        ips = [p.text for p in root.findall('.//ros2_control/hardware/param') if p.attrib.get('name')=='robot_ip']
        self.simulator_verified = ips == ['172.17.0.2']

    def wait(self, future, timeout=60):
        rclpy.spin_until_future_complete(self, future, timeout_sec=timeout)
        if not future.done():
            raise TimeoutError('La operacion ROS2 no terminó')
        result = future.result()
        if result is None:
            raise RuntimeError('Sin respuesta ROS2')
        return result

    def move(self, target):
        if not self.planner.wait_for_service(timeout_sec=20) or not self.execute.wait_for_server(timeout_sec=20):
            raise RuntimeError('MoveIt no disponible')
        request = GetMotionPlan.Request()
        plan = request.motion_plan_request
        plan.group_name = 'ur_manipulator'
        plan.pipeline_id = 'ompl'
        plan.planner_id = 'RRTConnectkConfigDefault'
        plan.num_planning_attempts = 5
        plan.allowed_planning_time = 5.0
        plan.max_velocity_scaling_factor = 0.15
        plan.max_acceleration_scaling_factor = 0.15
        plan.start_state.joint_state = self.current
        goal = Constraints()
        for name, position in zip(JOINTS,target):
            goal.joint_constraints.append(JointConstraint(joint_name=name, position=float(position),
                                                          tolerance_above=0.005, tolerance_below=0.005, weight=1.0))
        plan.goal_constraints = [goal]
        response = self.wait(self.planner.call_async(request)).motion_plan_response
        if response.error_code.val != MoveItErrorCodes.SUCCESS:
            raise RuntimeError('Falló planificación: '+str(response.error_code.val))
        goal_msg = ExecuteTrajectory.Goal(trajectory=response.trajectory)
        handle = self.wait(self.execute.send_goal_async(goal_msg))
        if not handle.accepted:
            raise RuntimeError('Ejecución no aceptada')
        result = self.wait(handle.get_result_async(), timeout=90).result
        if result.error_code.val != MoveItErrorCodes.SUCCESS:
            raise RuntimeError('Falló ejecución: '+str(result.error_code.val))
        for _ in range(5):
            rclpy.spin_once(self, timeout_sec=0.1)
        actual = dict(zip(self.current.name, self.current.position))
        error = max(abs(actual[name]-position) for name,position in zip(JOINTS,target))
        if error > 0.02:
            raise RuntimeError('Estado final no coincide: '+str(error))
        return dict(plan_success=True, execute_success=True, max_error_rad=error,
                    trajectory_points=len(response.trajectory.joint_trajectory.points), target=target)

    def controller(self, activate):
        if not self.switch.wait_for_service(timeout_sec=10):
            raise RuntimeError('Gestor de controladores no disponible')
        request = SwitchController.Request()
        request.strictness = SwitchController.Request.BEST_EFFORT
        request.activate_asap = True
        request.timeout.sec = 10
        if activate:
            request.activate_controllers = ['scaled_joint_trajectory_controller']
        else:
            request.deactivate_controllers = ['scaled_joint_trajectory_controller','joint_trajectory_controller']
        result = self.wait(self.switch.call_async(request),timeout=20)
        if not result.ok:
            raise RuntimeError('Cambio de controlador falló: '+result.message)


def main():
    rclpy.init()
    node = Bonus()
    deadline = time.time()+60
    while (node.current is None or not node.running or not node.simulator_verified) and time.time()<deadline:
        rclpy.spin_once(node, timeout_sec=0.2)
    if node.current is None or not node.running:
        raise RuntimeError('Iniciar Programa_2_ExternalControl y confirmar su popup primero')
    if not node.simulator_verified:
        raise RuntimeError('La descripcion del driver no corresponde a URSim 172.17.0.2; no se enviara movimiento')
    node.controller(False)
    node.controller(True)  # Tomar la postura actual, nunca una consigna anterior a URScript.
    results = []
    target = list(HOME)
    target[0] = 0.20
    for pose in (HOME, target, HOME):
        results.append(node.move(pose))
    folder = ROOT/'evidencias'
    folder.mkdir(exist_ok=True)
    (folder/'bonus_moveit.json').write_text(json.dumps(dict(results=results, joint_states=node.samples), indent=2))
    if not node.handback.wait_for_service(timeout_sec=10):
        raise RuntimeError('Servicio de devolución de control no disponible')
    reply = node.wait(node.handback.call_async(Trigger.Request()))
    if not reply.success:
        raise RuntimeError(reply.message)
    node.controller(False)
    print(json.dumps(results, indent=2), flush=True)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
