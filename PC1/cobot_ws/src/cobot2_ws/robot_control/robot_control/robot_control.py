# ============================================================
# robot_control.py
# Doosan DSR 로봇(m0609)을 이용한 음성 명령 기반 Pick-and-Place 제어 노드
# ============================================================

import os
import time
import sys
import threading
from scipy.spatial.transform import Rotation
import numpy as np
import rclpy
from std_msgs.msg import String
from rclpy.node import Node
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
import DR_init
import robot_control.under_cup as under_cup

from od_msg.srv import SrvDepthPosition
from std_srvs.srv import Trigger
from ament_index_python.packages import get_package_share_directory
from robot_control.onrobot import RG

package_path = get_package_share_directory("robot_control")

ROBOT_ID = "dsr01"
ROBOT_MODEL = "m0609"

VELOCITY, ACC = 60, 60
PICK_VELOCITY, PICK_ACC = 70, 60
POUR_VELOCITY, POUR_ACC = 60, 60
FINISH_VELOCITY, FINISH_ACC = 60, 60

STEP_DELAY = 0.3
GRIPPER_FORCE = 400
GRIPPER_WAIT_TIMEOUT = 10.0
FINISH_GRIPPER_WIDTH_VAL = 450

BUCKET_POS = [43.021, 40.999, 119.626, 98.4, -84.1, -286.472]
JHOME_POS = [25.094, -6.727, 111.35, 111.046, -116.14, -337.042]
J_READY = [13.998, -18.531, 110.579, 110.158, -97.937, -173.785]
J_CLEAN = [-0.601, -8.663, 133.093, 3.415, -0.562, 86.678]
J_SINK = [17.533, 7.259, 96.128, 64.292, 76.434, -9.813]
# posj([17.533, 7.259, 96.128, 64.292, 76.434, -9.813])
# Container pose constants
GREEN_APPROACH_X = [751.269, -390.366, 363.04, 93.258, -88.214, -89.882]
GREEN_PICK_X = [754.086, -424.825, 363.869, 94.204, -88.426, -89.633]
GREEN_LIFT_X = [742.491, -423.131, 474.593, 97.875, -86.072, -88.192]
GREEN_PULL_X = [726.906, -304.104, 488.466, 95.518, -85.414, -90.861]

RED_APPROACH_X = [640.142, -388.318, 370.336, 89.524, -88.151, -87.846]
RED_PICK_X = [636.483, -428.828, 364.711, 89.177, -88.804, -90.285]
RED_LIFT_X = [634.418, -433.039, 452.721, 92.404, -87.972, -88.686]
RED_PULL_X = [626.922, -306.674, 450.569, 90.633, -88.488, -88.387]

BLUE_APPROACH_X = [515.656, -385.572, 363.062, 88.646, -93.026, -87.944]
BLUE_PICK_X = [516.469, -438.05, 361.98, 87.452, -92.218, -89.576]
BLUE_LIFT_X = [514.673, -432.484, 469.462, 89.44, -90.046, -88.036]
BLUE_PULL_X = [519.358, -283.568, 480.917, 89.964, -88.189, -87.788]

# Common pose constants
HOME_J = [0, 0, 90, 0, 90, 0]
POSE_LIE_J = [-1.198, 13.163, 100.74, 0.048, 4.711, 0.001]
POSE_ROTATE_J = [-2.261, 13.186, 100.765, 84.124, 4.701, -0.001]
POSE_READY_J = [5.214, -1.897, 101.356, 91.993, -95.872, 10.662]
POUR_FRONT_X = [472.499, -139.658, 479.44, 88.543, -87.831, -86.6]
POUR_BACK_X = [476.662, 99.315, 385.841, 89.531, -88.885, -88.713]
POUR_HALF_X = [477.95, 122.859, 248.708, 85.595, 149.129, -95.925]
POUR_THIRD_X = [478.072, 128.012, 240.373, 86.945, 160.822, -91.697]
POUR_QUARTER_X = [468.995, 141.743, 217.159, 46.353, 166.538, -131.547]
FINISH_CHANGE_J = [5.214, -1.897, 101.356, 91.993, -95.872, 10.662]
FINISH_PUSH_READY_J = [5.559, -4.823, 93.516, 179.568, -90.063, -86.139]
FINISH_PUSH_START_X = [414.927, 10.146, 16.604, 2.495, 154.408, 89.548]
FINISH_PUSH_END_X = [771.341, 14.919, 17.261, 0.219, 148.877, 90.736]


CONTAINER_POSES = {
    "green": {
        "name": "초록",
        "approach_x": GREEN_APPROACH_X,
        "pick_x": GREEN_PICK_X,
        "lift_x": GREEN_LIFT_X,
        "pull_x": GREEN_PULL_X,
    },
    "red": {
        "name": "빨강",
        "approach_x": RED_APPROACH_X,
        "pick_x": RED_PICK_X,
        "lift_x": RED_LIFT_X,
        "pull_x": RED_PULL_X,
    },
    "blue": {
        "name": "파랑",
        "approach_x": BLUE_APPROACH_X,
        "pick_x": BLUE_PICK_X,
        "lift_x": BLUE_LIFT_X,
        "pull_x": BLUE_PULL_X,
    },
}

COMMON_POSES = {
    "home_j": HOME_J,
    "pose_lie_j": POSE_LIE_J,
    "pose_rotate_j": POSE_ROTATE_J,
    "pose_ready_j": POSE_READY_J,
    "pour_front_x": POUR_FRONT_X,
    "pour_back_x": POUR_BACK_X,
    "pour_half_x": POUR_HALF_X,
    "pour_third_x": POUR_THIRD_X,
    "pour_quarter_x": POUR_QUARTER_X,
    "finish_change_j": FINISH_CHANGE_J,
    "finish_push_ready_j": FINISH_PUSH_READY_J,
    "finish_push_start_x": FINISH_PUSH_START_X,
    "finish_push_end_x": FINISH_PUSH_END_X,
}

RECIPE_MATRIX = {
    "RECIPE_BR_01": ["red", "blue"],
    "RECIPE_MH_01": ["green", "blue"],
    "RECIPE_KM_01": ["green", "red"],
    "RECIPE_NULL_01": ["blue"],
}

RECIPE_TRIGGER_TOPIC = "/robot_recipe_trigger"

GRIPPER_NAME = "rg2"
TOOLCHARGER_IP = "192.168.1.1"
TOOLCHARGER_PORT = "502"

DEPTH_OFFSET = -10.0
MIN_DEPTH = 2.0

PICK_INWARD_OFFSET_X = 60.0
PICK_INWARD_OFFSET_Z = -35.00

ROI_SAVE_PATH = "/tmp/cup_roi.png"

DR_init.__dsr__id = ROBOT_ID
DR_init.__dsr__model = ROBOT_MODEL

rclpy.init()
dsr_node = rclpy.create_node("robot_control_node", namespace=ROBOT_ID)
DR_init.__dsr__node = dsr_node

try:
    from DSR_ROBOT2 import (
        movej,
        movel,
        amovej,
        amovel,
        get_current_posx,
        mwait,
        set_singularity_handling,
        DR_VAR_VEL,
    )
except ImportError as e:
    print(f"Error importing DSR_ROBOT2: {e}")
    sys.exit()

gripper = RG(GRIPPER_NAME, TOOLCHARGER_IP, TOOLCHARGER_PORT)


class RobotController(Node):
    """음성 명령 기반 Pick-and-Place 로봇 제어 노드."""

    def __init__(self):
        super().__init__("pick_and_place")
        self._stop_event = threading.Event()
        self._motion_lock = threading.Lock()
        self._service_group = ReentrantCallbackGroup()
        self._recipe_event = threading.Event()
        self._pending_recipe_code = None
        self.init_robot()

        set_singularity_handling(DR_VAR_VEL)

        self.get_position_client = self.create_client(
            SrvDepthPosition, "/get_3d_position", callback_group=self._service_group
        )
        while not self.get_position_client.wait_for_service(timeout_sec=3.0):
            self.get_logger().info("Waiting for get_depth_position service...")
        self.get_position_request = SrvDepthPosition.Request()

        # ── 키보드 입력 키워드 서비스 클라이언트 ────────────────────────
        # /get_keyword: Trigger 서비스로 키보드 입력을 받아 GPT가 파싱한 물체 이름을 반환
        # self.get_keyword_client = self.create_client(Trigger, "/get_keyword")
        # while not self.get_keyword_client.wait_for_service(timeout_sec=3.0):
            # self.get_logger().info("Waiting for get_keyword service...")
        # self.get_keyword_request = Trigger.Request()
        
        self._recipe_trigger_sub = self.create_subscription(
            String,
            RECIPE_TRIGGER_TOPIC,
            self.recipe_trigger_callback,
            10,
        )
        self.get_logger().info(f"Subscribed to {RECIPE_TRIGGER_TOPIC}")

    def stop(self):
        self._stop_event.set()

    def _wait_future(self, future, timeout_sec=None):
        start = time.time()
        while rclpy.ok() and not future.done() and not self._stop_event.is_set():
            if timeout_sec is not None and (time.time() - start) > timeout_sec:
                return None
            time.sleep(0.01)
        if not future.done():
            return None
        return future.result()

    def control_loop(self):
        while rclpy.ok() and not self._stop_event.is_set():
            self.robot_control()

    def get_robot_pose_matrix(self, x, y, z, rx, ry, rz):
        """TCP 위치/자세를 4x4 동차 변환행렬로 변환한다."""
        R = Rotation.from_euler("ZYZ", [rx, ry, rz], degrees=True).as_matrix()

        T = np.eye(4)
        T[:3, :3] = R
        T[:3, 3] = [x, y, z]
        return T

    def transform_to_base(self, camera_coords, gripper2cam_path, robot_pos):
        """카메라 좌표계를 로봇 베이스 좌표계로 변환한다."""
        gripper2cam = np.load(gripper2cam_path)
        coord = np.append(np.array(camera_coords), 1)

        x, y, z, rx, ry, rz = robot_pos
        base2gripper = self.get_robot_pose_matrix(x, y, z, rx, ry, rz)
        base2cam = base2gripper @ gripper2cam
        td_coord = np.dot(base2cam, coord)

        return td_coord[:3]


    def get_target_pos(self, target):
        """물체 이름을 받아 TCP 목표 위치를 계산한다."""
        self.get_position_request.target = target

        self.get_logger().info("call depth position service with object_detection node")
        get_position_future = self.get_position_client.call_async(
            self.get_position_request
        )
        get_position_result = self._wait_future(get_position_future)

        if get_position_result:
            result = get_position_result.depth_position.tolist()
            self.get_logger().info(f"Received depth position: {result}")

            if sum(result) == 0:
                print("No target position")
                return None

            gripper2cam_path = os.path.join(
                package_path, "resource", "T_gripper2camera.npy"
            )
            robot_posx = get_current_posx()[0]
            td_coord = self.transform_to_base(result, gripper2cam_path, robot_posx)

            if td_coord[2] and sum(td_coord) != 0:
                td_coord[2] += DEPTH_OFFSET
                td_coord[2] = max(td_coord[2], MIN_DEPTH)

            target_pos = list(td_coord[:3]) + robot_posx[3:]
            return target_pos

        return None

    def recipe_trigger_callback(self, msg):
        recipe_code = msg.data.strip()
        self.get_logger().info(f"📡 제조 시그널 수신: [{recipe_code}]")

        if recipe_code not in RECIPE_MATRIX:
            self.get_logger().error(f"❌ [에러] 레시피 매핑 실패: {recipe_code}")
            return

        self._pending_recipe_code = recipe_code
        self._recipe_event.set()
        self.get_logger().info(f"📦 레시피 대기열 등록 완료: {RECIPE_MATRIX[recipe_code]}")
        

    def robot_control(self):
        with self._motion_lock:
            self.get_logger().info("레시피 콜백 대기 중...")
            while rclpy.ok() and not self._stop_event.is_set():
                if self._recipe_event.wait(timeout=0.1):
                    break

            if self._stop_event.is_set() or not self._recipe_event.is_set():
                return
            self.init_robot(J_READY)
            recipe_code = self._pending_recipe_code
            self._recipe_event.clear()
            self._pending_recipe_code = None
            recipe = RECIPE_MATRIX.get(recipe_code)
            target_cup = f"{recipe[-1]}_cup" if recipe else "red_cup"  # 레시피가 없으면 기본적으로 빨간 컵을 타겟으로 설정

            target_pos = self.get_target_pos(target_cup)
            if target_pos is None:
                # self.init_robot()
                self.get_logger().warn("No target position")
                return

            self.get_logger().info(f"target position: {target_pos}")
            self.pick_and_place_target(target_pos, target_cup)

            if recipe:
                self.get_logger().info(f"레시피 실행 요청: {recipe_code} -> {recipe}")
                self.cocktail_making(recipe)
            # self.init_robot(J_CLEAN)

            # time.sleep(5.0)  # 다음 레시피 대기 전 잠시 휴식
            # 클컵 진행 
            # self.get_logger().info("클컵 진행")
            # self.clear_pick_and_place_target("red_cup")
            self.init_robot()
    
    def move_j(self, joint_positions, **kwargs):
        """주어진 관절 위치로 movej 이동한다."""
        movej(joint_positions, **kwargs)
        self.get_logger().info(f"movej to {joint_positions} with params {kwargs}")
        mwait(1.0)

    def move_l(self, cartesian_positions, **kwargs):
        """주어진 TCP 위치로 movel 이동한다."""
        movel(cartesian_positions, **kwargs)
        self.get_logger().info(f"movel to {cartesian_positions} with params {kwargs}")
        mwait(1.0)

    def set_target_pose(self, x, y, z, rx, ry, rz):
        """목적지 좌표로 movel 이동한다."""
        target_pose = [x, y, z, rx, ry, rz]
        self.move_l(target_pose, vel=VELOCITY, acc=ACC)
        return target_pose

    def robot_wait(self, sec):
        time.sleep(sec)

    def wait_gripper_until_idle(self, timeout=GRIPPER_WAIT_TIMEOUT):
        start_time = time.time()
        while gripper.get_status()[0]:
            if time.time() - start_time > timeout:
                raise TimeoutError("그리퍼 동작 대기 시간이 초과되었습니다.")
            time.sleep(0.5)

    def gripper_close(self, force_val=GRIPPER_FORCE):
        gripper.close_gripper(force_val=force_val)
        self.wait_gripper_until_idle()
        self.robot_wait(STEP_DELAY)

    def gripper_open(self, force_val=GRIPPER_FORCE):
        gripper.open_gripper(force_val=force_val)
        self.wait_gripper_until_idle()
        self.robot_wait(STEP_DELAY)

    def set_gripper_width_45(self, force_val=GRIPPER_FORCE):
        gripper.move_gripper(FINISH_GRIPPER_WIDTH_VAL, force_val=force_val)
        self.wait_gripper_until_idle()
        self.robot_wait(STEP_DELAY)

    def move_start_ready(self):
        self.move_j(COMMON_POSES["pose_lie_j"], vel=VELOCITY, acc=ACC)
        self.move_j(COMMON_POSES["pose_rotate_j"], vel=VELOCITY, acc=ACC)
        self.move_j(COMMON_POSES["pose_ready_j"], vel=VELOCITY, acc=ACC)

    def pick_container(self, color):
        pose_data = CONTAINER_POSES[color]
        self.move_l(pose_data["approach_x"], vel=PICK_VELOCITY, acc=PICK_ACC)
        self.move_l(pose_data["pick_x"], vel=PICK_VELOCITY, acc=PICK_ACC)
        self.gripper_close()
        self.move_l(pose_data["lift_x"], vel=PICK_VELOCITY, acc=PICK_ACC)
        self.move_l(pose_data["pull_x"], vel=PICK_VELOCITY, acc=PICK_ACC)

    def pour_container(self, recipe_count):
        if recipe_count == 2:
            pour_pose = COMMON_POSES["pour_half_x"]
        elif recipe_count == 3:
            pour_pose = COMMON_POSES["pour_third_x"]
        else:
            pour_pose = COMMON_POSES["pour_quarter_x"]

        self.move_l(COMMON_POSES["pour_front_x"], vel=POUR_VELOCITY, acc=POUR_ACC)
        self.move_l(COMMON_POSES["pour_back_x"], vel=POUR_VELOCITY, acc=POUR_ACC)
        self.move_l(pour_pose, vel=POUR_VELOCITY, acc=POUR_ACC)
        self.robot_wait(0.1)
        self.move_l(COMMON_POSES["pour_back_x"], vel=POUR_VELOCITY, acc=POUR_ACC)
        self.move_l(COMMON_POSES["pour_front_x"], vel=POUR_VELOCITY, acc=POUR_ACC)

    def return_container(self, color):
        pose_data = CONTAINER_POSES[color]
        self.move_l(pose_data["pull_x"], vel=PICK_VELOCITY, acc=PICK_ACC)
        self.move_l(pose_data["lift_x"], vel=PICK_VELOCITY, acc=PICK_ACC)
        self.move_l(pose_data["pick_x"], vel=PICK_VELOCITY, acc=PICK_ACC)
        self.gripper_open()
        self.move_l(pose_data["pull_x"], vel=PICK_VELOCITY, acc=PICK_ACC)

    def finish_motion(self):
        self.move_j(COMMON_POSES["finish_change_j"], vel=FINISH_VELOCITY, acc=FINISH_ACC)
        self.move_j(COMMON_POSES["finish_push_ready_j"], vel=FINISH_VELOCITY, acc=FINISH_ACC)
        self.set_gripper_width_45()
        self.move_l(COMMON_POSES["finish_push_start_x"], vel=FINISH_VELOCITY, acc=FINISH_ACC)
        self.move_l(COMMON_POSES["finish_push_end_x"], vel=FINISH_VELOCITY, acc=FINISH_ACC)
        self.move_l(COMMON_POSES["finish_push_start_x"], vel=FINISH_VELOCITY, acc=FINISH_ACC)
        self.move_j(COMMON_POSES["home_j"], vel=VELOCITY, acc=ACC)

    def init_robot(self, pose=JHOME_POS):
        """로봇을 준비 자세로 초기화한다."""

        self.move_j(pose, vel=VELOCITY, acc=ACC)
        self.gripper_open()
        mwait(1.0)

    def cup_frontal_position(self, target_pos):
        """물체의 정면 접근 위치로 직선 이동한다."""
        self.get_logger().info(f"Moving to frontal view position: {target_pos}")
        self.move_l(target_pos, vel=VELOCITY, acc=ACC)
        mwait(1.0)
        return target_pos

    def clear_pick_and_place_target(self, target):
        """간소화된 접근-전진-파지-상승 시퀀스를 수행한다."""
        self.get_logger().info(f"Clearing pick-and-place target: {target}")
        self.get_logger().info("1단계: 카메라로부터 목표 위치 획득")
        target_pos = self.get_target_pos(target)
        if target_pos is None:
            self.get_logger().warn("No target position")
            return
        pick_down_pos = target_pos
        self.get_logger().info(f"1단계 접근 이동: {pick_down_pos}")
        self.move_l(pick_down_pos, vel=VELOCITY, acc=ACC)
        mwait(1.0)

        pick_inward_pos = [
            target_pos[0] + PICK_INWARD_OFFSET_X,
            target_pos[1],
            target_pos[2] + (PICK_INWARD_OFFSET_Z - 10),
            target_pos[3],
            target_pos[4] + 10,
            target_pos[5]
        ]
        self.get_logger().info(
            f"2단계 중앙 방향 전진 이동: {pick_inward_pos} "
            f"(offset_x={PICK_INWARD_OFFSET_X:.1f}mm, offset_z={PICK_INWARD_OFFSET_Z:.1f}mm)"
        )
        self.move_l(pick_inward_pos, vel=VELOCITY, acc=ACC)
        
        self.get_logger().info("3단계: 그리퍼 닫기")
        self.gripper_close()
        mwait(1.0)

        self.get_logger().info("4단계 상승 이동")
        pick_up_pos = pick_inward_pos[0:2] + [pick_inward_pos[2] + 50] + pick_inward_pos[3:]
        self.move_l(pick_up_pos, vel=VELOCITY, acc=ACC)

        # 안전 싱크대 위치로 이동
        self.get_logger().info("5단계: 안전 싱크대 위치로 이동")
        self.move_j(J_SINK, vel=VELOCITY, acc=ACC)

        self.get_logger().info("6단계: 그리퍼 열기 및 초기화 완료")
        self.gripper_open()
        mwait(1.0)
        
    def cocktail_making(self, recipe):
        """레시피 색상 순서에 따라 칵테일 제조 시퀀스를 수행한다."""
        recipe_count = len(recipe)
        if recipe_count == 0:
            self.get_logger().warn("빈 레시피는 실행하지 않습니다.")
            return

        self.get_logger().info(f"칵테일 제조 시작: {recipe}")
        try:
            self.gripper_open()
            self.move_start_ready()

            for idx, color in enumerate(recipe, start=1):
                if color not in CONTAINER_POSES:
                    raise ValueError(f"지원하지 않는 재료 색상: {color}")
                self.get_logger().info(
                    f"[{idx}/{recipe_count}] 재료 처리: {CONTAINER_POSES[color]['name']}"
                )
                self.pick_container(color)
                self.pour_container(recipe_count)
                self.return_container(color)

            self.finish_motion()
            self.get_logger().info("칵테일 제조 완료")
        except Exception as e:
            self.get_logger().error(f"칵테일 제조 중 예외 발생: {e}")


    def pick_and_place_target(self, target_pos, target="red_cup"):
        """물체를 집어 버킷에 내려놓는 전체 시퀀스."""
        self.get_logger().info("===== Pick-and-Place 시퀀스 시작 =====")

        pick_pose = (
            target_pos[:2]
            + [target_pos[2] - 50]
            + [target_pos[3]]
            + [target_pos[4] + 45]
            + [target_pos[5]]
        )
        current_frontal_pos = self.cup_frontal_position(pick_pose)
 
        # ┌─────────────────────────────────────────────────────────────────┐
        # │                      ROI REFRESH BLOCK                         │
        # │  정면 위치에서 ROI를 다시 저장하여 방향 판별 정확도를 높인다.         │
        # │  JReady 대각선 자세보다 정면에서 찍은 ROI가 컵 형태를 더 잘 보여준다. │
        # │  성공 시 target_pos도 정밀화된 값으로 갱신한다.                     │
        # └─────────────────────────────────────────────────────────────────┘
        self.get_logger().info("정면 위치에서 ROI 갱신 중...")
        fresh_pos = self.get_target_pos(target)     # 재감지 → ROI_SAVE_PATH 갱신됨
        if fresh_pos is not None:
            target_pos = fresh_pos                  # 정밀화된 위치로 교체
            self.get_logger().info(f"target_pos 갱신 완료: {target_pos}")
        else:
            self.get_logger().warn("정면 재감지 실패 — 기존 target_pos 유지")
        # └─────────────────────── ROI REFRESH END ─────────────────────────┘
 
        # ┌─────────────────────────────────────────────────────────────────┐
        # │                   CUP ORIENTATION BLOCK                        │
        # │  align_cup()  : ROI 이미지를 컵이 수직이 되도록 회전 보정           │
        # │  check_cup_status() : 상단/하단 너비 비교 → 방향 판별              │
        # │    True  = 정방향 (입구가 위) : 파지 전 별도 회전 불필요             │
        # │    False = 역방향 (바닥이 위) : 5단계에서 6번 관절 180° 보정 필요    │
        # │  예외 발생 시 기본값 True(정방향)로 처리하여 동작을 안전하게 유지.     │
        # └─────────────────────────────────────────────────────────────────┘
        try:
            time.sleep(0.5)  # ROI 파일 기록 완료를 보장하기 위한 짧은 대기
 
            aligned    = under_cup.align_cup(ROI_SAVE_PATH)          # 수직 정렬
            is_upright = under_cup.check_cup_status(aligned)         # 방향 판별
 
            self.get_logger().info(f"컵 방향: {'정방향' if is_upright else '역방향'}")
        except Exception as e:
            # ROI 파일 없음, 윤곽선 미검출 등 → 정방향으로 가정하고 계속 진행
            self.get_logger().warn(f"컵 방향 판별 실패 ({e}) — 정방향으로 가정")
            is_upright = True
        # └────────────────────── CUP ORIENTATION END ──────────────────────┘

        # ── 4단계: 파지 전 선회(방향 보정) ───────────────────────────────
        # 방향 판별 결과를 반영해 하강/전진 전에 손목 자세를 먼저 맞춘다.
        if not is_upright:
            rotation_offset = -170 if target_pos[5] > 0.0 else 170
            self.get_logger().info(
                f"4단계: 역방향 컵 — 파지 전 그리퍼 선회 수행 (Rz {rotation_offset:+.1f}deg)"
            )

            target_pos[5] += rotation_offset
            current_frontal_pos[5] += rotation_offset

            # 현재 정면 위치에서 자세만 선회해 이후 접근 경로의 자세를 일관되게 유지
            self.move_l(current_frontal_pos, vel=VELOCITY, acc=ACC)
        else:
            self.get_logger().info("4단계: 정방향 컵 — 파지 전 선회 생략")
 
        # ── 5단계: 물체 정면으로 하강 ──────────────────────────────────
        # current_frontal_pos 기준으로 Z축 -20mm 하강
        pick_down_pos = (
            current_frontal_pos[0:2]
            + [current_frontal_pos[2] - 20]
            + current_frontal_pos[3:]
        )
        self.get_logger().info(f"5단계 하강 이동: {pick_down_pos}")
        self.move_l(pick_down_pos, vel=VELOCITY, acc=ACC)

        pick_forward_pos = [target_pos[0], target_pos[1] - 70, target_pos[2]] + target_pos[3:]
        self.get_logger().info(f"6단계 전진 이동: {pick_forward_pos}")
        self.move_l(pick_forward_pos, vel=VELOCITY, acc=ACC)

        self.get_logger().info("7단계: 그리퍼 닫기")
        self.gripper_close()
        mwait(1.0)

        current_posx = list(get_current_posx()[0])
        pick_up_pos = current_posx[0:2] + [current_posx[2] + 100] + current_posx[3:]
        self.get_logger().info(f"8단계 상승 이동: {pick_up_pos}")
        self.move_l(pick_up_pos, vel=VELOCITY, acc=ACC)

        self.get_logger().info("9단계: 안전 홈 자세(Joint) 이동")
        self.move_j(JHOME_POS, vel=VELOCITY, acc=ACC)

        self.get_logger().info("10단계: 버킷 위치로 이동")
        self.move_j(BUCKET_POS, vel=VELOCITY, acc=ACC)

        self.get_logger().info("11단계: 그리퍼 열기 및 배치 완료")
        self.gripper_open()
        mwait(1.0)

        self.move_l(
            [350.498, 175.531, 280.101, 127.418, -98.359, -87.164],
            vel=VELOCITY,
            acc=ACC,
        )



def main(args=None):
    node = RobotController()
    worker = threading.Thread(target=node.control_loop, daemon=True)
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)
    worker.start()

    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.stop()
        worker.join(timeout=1.0)
        executor.shutdown()
        executor.remove_node(node)
        node.destroy_node()
        rclpy.shutdown()




if __name__ == "__main__":
    main()





















# # ============================================================
# # robot_control_v4.py
# # Doosan DSR 로봇(m0609)을 이용한 키보드 입력 기반 Pick-and-Place 제어 노드
# #
# # 전체 동작 흐름:
# #   1. 키보드 입력 서비스(/get_keyword)로 집을 물체 이름 수신
# #   2. 뎁스 카메라 서비스(/get_3d_position)로 물체의 3D 좌표 획득
# #   3. 카메라 좌표 → 로봇 베이스 좌표 변환
# #   4. 로봇이 물체를 집어 버킷 위치에 내려놓는 Pick-and-Place 수행
# #
# # robot_control.py 대비 추가/변경 사항:
# #   1. under_cup 모듈 임포트 추가 (align_cup, check_cup_status)
# #   2. ROI_SAVE_PATH 상수 추가
# #   3. pick_and_place_target 시그니처에 target 파라미터 추가
# #      → 정면 이동 후 재감지 시 어떤 물체를 찾을지 전달하기 위함
# #   4. robot_control()의 pick_and_place_target 호출부에 target 추가
# #   5. 1단계 이후 정면 ROI 재감지 블록 추가
# #      → JReady 자세보다 정면에서 찍은 ROI가 방향 판별에 정확하기 때문
# #   6. 컵 방향 판별 블록 추가 (under_cup 모듈 사용)
# #   7. 6단계(JHOME) 이후 Rz +180° 회전 블록 추가
# #      → 파지는 항상 동일한 자세로 수행하고, JHOME 안정 후 공중에서 컵을 뒤집어
# #         버킷에 정방향으로 내려놓기 위함
# #      → 정방향 컵을 그대로 놓으면 버킷에 거꾸로 들어가는 구조이므로
# #         is_upright=True일 때 회전 적용
# # ============================================================

# import os
# import time
# import sys
# from scipy.spatial.transform import Rotation  # 오일러각 → 회전행렬 변환에 사용
# import numpy as np
# import rclpy
# from rclpy.node import Node
# import DR_init  # Doosan 로봇 초기화 모듈

# from od_msg.srv import SrvDepthPosition  # 커스텀 서비스: 물체의 3D 뎁스 위치 요청
# from std_srvs.srv import Trigger          # 표준 서비스: 트리거 신호(키보드 입력 요청에 사용)
# from ament_index_python.packages import get_package_share_directory
# from robot_control.onrobot import RG      # OnRobot RG 그리퍼 제어 클래스
# # [추가 1] 컵 방향 판별 모듈 임포트
# from robot_control.under_cup import align_cup, check_cup_status

# # robot_control 패키지의 share 디렉터리 경로 (캘리브레이션 파일 로드에 사용)
# package_path = get_package_share_directory("robot_control")

# # ============================================================
# # 전역 상수 정의
# # ============================================================

# ROBOT_ID = "dsr01"       # ROS2 네임스페이스에서 사용할 로봇 식별자
# ROBOT_MODEL = "m0609"    # Doosan 로봇 모델명

# VELOCITY, ACC = 60, 60   # 로봇 이동 속도(%) 및 가속도(%) — 값이 클수록 빠름

# # 버킷(내려놓을 위치)의 관절각도 [J1~J6, 단위: deg]
# # BUCKET_POS = [4.00, 38.00, 64.00, -0.1, 78.0, 4]
# # posj([43.021, 40.999, 119.626, 98.4, -84.1, -286.472])
# BUCKET_POS = [43.021, 40.999, 119.626, 98.4, -84.1, -286.472]

# # BUCKET_POS = [32.84,50.01,81.17,-50.82,101.33,-126.14]


# # 물체를 집은 후 중간 경유지로 사용할 안전 홈 관절각도 [J1~J6, 단위: deg]
# # 관절 공간 이동이므로 충돌 위험이 낮음
# JHOME_POS = [25.094, -6.727, 111.35, 111.046, -116.14, -337.042]

# GRIPPER_NAME = "rg2"          # OnRobot RG2 그리퍼 모델명
# TOOLCHARGER_IP = "192.168.1.1"  # 툴체인저(그리퍼 전원/통신 허브) IP
# TOOLCHARGER_PORT = "502"         # Modbus TCP 포트번호

# DEPTH_OFFSET =-5.0  # 뎁스 카메라로 측정한 Z 값에 더할 보정 오프셋(mm 단위)
#                     # 카메라-그리퍼 간 측정 오차를 보완하기 위해 사용
# MIN_DEPTH = 2.0     # Z 좌표의 최솟값(mm) — 바닥 충돌 방지용 하한선

# # [추가 2] object_detection 노드가 ROI를 저장하는 고정 경로 (detection.py의 ROI_SAVE_PATH와 동일)
# ROI_SAVE_PATH = "/tmp/cup_roi.png"


# """
# # 현재: 5mm 내려감
# DEPTH_OFFSET = -5.0

# # 그리퍼가 물체 위에서 멈춰서 못 잡힐 때 → 더 내려가도록
# DEPTH_OFFSET = -10.0   # 10mm 내려감
# DEPTH_OFFSET = -15.0   # 15mm 내려감
# """



# # ============================================================
# # Doosan 로봇 SDK 초기화
# # ============================================================

# # DR_init 모듈에 로봇 ID와 모델을 등록하여 DSR_ROBOT2 함수들이 올바른 로봇에 연결되도록 설정
# DR_init.__dsr__id = ROBOT_ID
# DR_init.__dsr__model = ROBOT_MODEL

# # ROS2 런타임 초기화 및 로봇 제어용 노드 생성
# rclpy.init()
# dsr_node = rclpy.create_node("robot_control_node", namespace=ROBOT_ID)
# DR_init.__dsr__node = dsr_node  # DSR SDK가 내부적으로 이 노드를 통해 토픽/서비스를 사용

# # DSR_ROBOT2: Doosan 로봇 제어 함수 임포트
# #   movej  — 관절 공간(Joint Space) 이동
# #   movel  — 작업 공간(Cartesian Space) 직선 이동
# #   get_current_posx — 현재 TCP(툴 중심점) 위치 및 자세 반환 [x, y, z, rx, ry, rz]
# #   mwait  — 로봇 동작이 완료될 때까지 대기
# #   trans  — 좌표 변환 유틸리티 (현재 코드에서는 미사용)
# try:
#     from DSR_ROBOT2 import movej, movel, get_current_posx, mwait, trans
# except ImportError as e:
#     print(f"Error importing DSR_ROBOT2: {e}")
#     sys.exit()

# ########### Gripper Setup. Do not modify this area ############

# # OnRobot RG2 그리퍼 객체 생성
# # Modbus TCP를 통해 툴체인저에 연결하여 그리퍼를 제어
# gripper = RG(GRIPPER_NAME, TOOLCHARGER_IP, TOOLCHARGER_PORT)


# ########### Robot Controller ############


# class RobotController(Node):
#     """
#     키보드 입력 기반 Pick-and-Place 로봇 제어 노드.

#     - /get_keyword  서비스: 터미널 키보드 입력을 받아 GPT로 파싱된 물체 이름 목록을 받음
#     - /get_3d_position 서비스: 물체 이름을 넘겨주면 카메라 좌표계의 3D 위치를 반환
#     """

#     def __init__(self):
#         super().__init__("pick_and_place")

#         # 노드 시작 시 로봇을 준비 자세로 초기화하고 그리퍼를 열어둠
#         self.init_robot()

#         # ── 뎁스 위치 서비스 클라이언트 ──────────────────────────
#         # /get_3d_position: 물체 이름(target)을 보내면 카메라 좌표계의 [x, y, z]를 반환
#         self.get_position_client = self.create_client(
#             SrvDepthPosition, "/get_3d_position"
#         )
#         # 서비스가 준비될 때까지 최대 3초 간격으로 대기
#         while not self.get_position_client.wait_for_service(timeout_sec=3.0):
#             self.get_logger().info("Waiting for get_depth_position service...")
#         self.get_position_request = SrvDepthPosition.Request()  # 재사용할 요청 객체

#         # ── 키보드 입력 키워드 서비스 클라이언트 ────────────────────────
#         # /get_keyword: Trigger 서비스로 키보드 입력을 받아 GPT가 파싱한 물체 이름을 반환
#         self.get_keyword_client = self.create_client(Trigger, "/get_keyword")
#         while not self.get_keyword_client.wait_for_service(timeout_sec=3.0):
#             self.get_logger().info("Waiting for get_keyword service...")
#         self.get_keyword_request = Trigger.Request()

#     def get_robot_pose_matrix(self, x, y, z, rx, ry, rz):
#         """
#         로봇 TCP의 위치(x, y, z)와 ZYZ 오일러각(rx, ry, rz)을 받아
#         4×4 동차변환행렬(Homogeneous Transformation Matrix)을 반환한다.

#         반환 행렬 구조:
#             [ R  t ]   R: 3×3 회전행렬, t: [x, y, z] 위치벡터
#             [ 0  1 ]
#         """
#         # ZYZ 오일러 규약으로 회전행렬 생성 (Doosan DSR은 ZYZ 규약 사용)
#         # R = Rotation.from_euler("ZYZ", [rx, ry, rz], degrees=True).as_matrix()
#         R = Rotation.from_euler("ZYZ", [rx, ry, rz], degrees=True).as_matrix()

#         T = np.eye(4)       # 4×4 단위행렬로 초기화
#         T[:3, :3] = R       # 좌상단 3×3 블록에 회전행렬 삽입
#         T[:3, 3] = [x, y, z]  # 우측 열에 위치벡터 삽입
#         return T


#     def move_j(self, joint_positions, **kwargs):
#         """주어진 관절 위치로 movej 이동한다."""
#         movej(joint_positions, **kwargs)
#         self.get_logger().info(f"movej to {joint_positions} with params {kwargs}")
#         mwait(1.0)

#     def move_l(self, cartesian_positions, **kwargs):
#         """주어진 TCP 위치로 movel 이동한다."""
#         movel(cartesian_positions, **kwargs)
#         self.get_logger().info(f"movel to {cartesian_positions} with params {kwargs}")
#         mwait(1.0)

#     def transform_to_base(self, camera_coords, gripper2cam_path, robot_pos):
#         """
#         카메라 좌표계의 3D 좌표를 로봇 베이스 좌표계로 변환한다.

#         변환 체인:
#             카메라 좌표  →(gripper2cam)→  그리퍼 좌표  →(base2gripper)→  베이스 좌표

#         Args:
#             camera_coords: 카메라 좌표계에서의 [x, y, z]
#             gripper2cam_path: 그리퍼→카메라 변환행렬이 저장된 .npy 파일 경로
#                               (핸드-아이 캘리브레이션 결과)
#             robot_pos: 현재 TCP 포즈 [x, y, z, rx, ry, rz] (베이스→그리퍼)

#         Returns:
#             베이스 좌표계에서의 [x, y, z] (3D 배열)
#         """
#         # 핸드-아이 캘리브레이션으로 구한 그리퍼→카메라 변환행렬 (4×4)
#         gripper2cam = np.load(gripper2cam_path)

#         # 동차좌표로 변환: [x, y, z] → [x, y, z, 1]
#         coord = np.append(np.array(camera_coords), 1)

#         # 현재 TCP 포즈로 베이스→그리퍼 변환행렬 생성
#         x, y, z, rx, ry, rz = robot_pos
#         base2gripper = self.get_robot_pose_matrix(x, y, z, rx, ry, rz)

#         # 베이스→카메라 변환행렬 = 베이스→그리퍼 @ 그리퍼→카메라
#         base2cam = base2gripper @ gripper2cam

#         # 카메라 좌표를 베이스 좌표로 변환
#         td_coord = np.dot(base2cam, coord)

#         return td_coord[:3]  # 동차좌표의 w=1 성분 제거 후 반환



#     def robot_control(self):
#         target_list = []
#         self.get_logger().info("call get_keyword service")

#         # ─── 이 부분의 로그 메시지를 수정합니다 ───
#         self.get_logger().info("인식 노드(GetKeyword) 터미널 창에 명령을 타이핑하고 엔터를 누르세요.")

#         get_keyword_future = self.get_keyword_client.call_async(self.get_keyword_request)
#         rclpy.spin_until_future_complete(self, get_keyword_future)

#         if get_keyword_future.result().success:
#             get_keyword_result = get_keyword_future.result()

#             target_list = get_keyword_result.message.split()

#             for target in target_list:
#                 target_pos = self.get_target_pos(target)
#                 # 1번째 감지에서 저장된 ROI는 방향 판별에 쓰지 않으므로 즉시 삭제
#                 if os.path.exists(ROI_SAVE_PATH):
#                     os.remove(ROI_SAVE_PATH)
#                 if target_pos is None:
#                     self.get_logger().warn("No target position")
#                 else:
#                     self.get_logger().info(f"target position: {target_pos}")
#                     self.pick_and_place_target(target, target_pos)
#                     self.init_robot()
#         else:
#             self.get_logger().warn(f"{get_keyword_result.message}")
#             return


#     def get_target_pos(self, target):
#         """
#         물체 이름을 받아 로봇이 이동해야 할 TCP 목표 위치를 계산한다.

#         처리 순서:
#             1. /get_3d_position 서비스로 카메라 좌표계 3D 위치 획득
#             2. 핸드-아이 캘리브레이션 행렬로 베이스 좌표계로 변환
#             3. Z축 오프셋 보정 적용
#             4. 현재 TCP의 자세(rx, ry, rz)를 붙여 최종 6DoF 목표 포즈 반환

#         Args:
#             target: 집을 물체 이름 문자열 (예: "cup")

#         Returns:
#             [x, y, z, rx, ry, rz] 형식의 목표 TCP 포즈, 물체 미감지 시 None
#         """
#         self.get_position_request.target = target  # 찾을 물체 이름 설정

#         self.get_logger().info("call depth position service with object_detection node")
#         get_position_future = self.get_position_client.call_async(
#             self.get_position_request
#         )
#         rclpy.spin_until_future_complete(self, get_position_future)

#         if get_position_future.result():
#             # 뎁스 카메라에서 받은 카메라 좌표계 3D 위치 [x, y, z]
#             result = get_position_future.result().depth_position.tolist()
#             self.get_logger().info(f"Received depth position: {result}")

#             # 좌표가 모두 0이면 물체를 감지하지 못한 것으로 판단
#             if sum(result) == 0:
#                 print("No target position")
#                 return None

#             # 핸드-아이 캘리브레이션 결과 파일 경로
#             gripper2cam_path = os.path.join(
#                 package_path, "resource", "T_gripper2camera.npy"
#             )

#             # 현재 TCP 포즈 취득 — 좌표 변환의 기준점으로 사용
#             # get_current_posx()는 [[x, y, z, rx, ry, rz], ref_frame] 반환
#             robot_posx = get_current_posx()[0]

#             # 카메라 좌표 → 로봇 베이스 좌표 변환
#             td_coord = self.transform_to_base(result, gripper2cam_path, robot_posx)

#             # Z축 보정: 측정 오차를 DEPTH_OFFSET으로 보완하고, MIN_DEPTH 이상 유지
#             if td_coord[2] and sum(td_coord) != 0:
#                 td_coord[2] += DEPTH_OFFSET          # 측정 오차 보정
#                 td_coord[2] = max(td_coord[2], MIN_DEPTH)  # 바닥 충돌 방지 하한선

#             # XYZ는 변환된 좌표, 자세(rx, ry, rz)는 현재 TCP 자세 그대로 사용
#             target_pos = list(td_coord[:3]) + robot_posx[3:]

#         return target_pos

#     def init_robot(self):
#         """
#         로봇을 준비 자세로 초기화한다.

#         JReady는 카메라 시야를 확보하면서 그리퍼가 펼쳐진 대기 자세.
#         gripper.open_gripper() 호출로 그리퍼를 열어 다음 작업을 준비한다.
#         """
#         # 준비 자세 관절각도 [J1~J6, 단위: deg]
#         # JReady = [13.998, -18.531, 103.579, 128.158, -97.937, 3.785]

#         JReady = [13.998, -18.531, 110.579, 110.158, -97.937, -173.785]

#         # JReady = [8.873, -41.257, 128.716, -11.062, 42.819, -254.542]

#         movej(JReady, vel=VELOCITY, acc=ACC)
#         gripper.open_gripper()  # 그리퍼 열기
#         mwait()                 # 로봇 동작 완료까지 대기

#     def cup_frontal_position(self, target_pos):
#         """
#         물체의 정면 접근 위치로 직선 이동한다.

#         카메라가 대각선(diagonal view)에서 바라보던 자세에서
#         그리퍼가 물체를 정면으로 향하도록 TCP를 이동시킨다.
#         이 위치에서 카메라로 물체를 재확인한 뒤 파지 동작으로 진행한다.

#         Args:
#             target_pos: 이동할 목표 TCP 포즈 [x, y, z, rx, ry, rz]
#         """
#         self.get_logger().info(f"Moving to frontal view position: {target_pos}")
#         movel(target_pos, vel=VELOCITY, acc=ACC)  # Cartesian 직선 이동
#         mwait()  # 1초 대기 (자세 안정화)
#         return target_pos

#     # # [추가 3] target 파라미터 추가 — 정면 이동 후 재감지 시 물체 이름 전달에 필요
#     # def pick_and_place_target(self, target, target_pos):
#     #         """
#     #         물체를 집어 버킷에 내려놓는 Pick-and-Place 전체 시퀀스 (수정본)
#     #         """
#     #         self.get_logger().info("===== Pick-and-Place 시퀀스 시작 =====")

#     #         # ── 1단계: 정면 접근 위치로 이동 ─────────────────────────
#     #         # 컵의 최종 목표 위치(target_pos)에서 Z축으로 50mm 후퇴하고,
#     #         # 그리퍼가 정면을 바라보도록 Ry 각도를 45도 기울임
#     #         pick_pose = (
#     #             target_pos[:2]
#     #             + [target_pos[2] - 50]
#     #             + [target_pos[3]]
#     #             + [target_pos[4] + 45]
#     #             + [target_pos[5]]
#     #         )
#     #         # 현재 위치 기준 정면 접근 위치 계산 및 이동
#     #         current_frontal_pos = self.cup_frontal_position(pick_pose)
#     #         self.get_logger().info(f"1단계 정면 이동: {current_frontal_pos}")

#     #         # ── [추가 5] 정면에서 ROI 재감지 ─────────────────────────
#     #         # JReady 자세에서 찍은 ROI보다 정면에서 찍은 ROI가 컵 방향 판별에 정확함.
#     #         # get_target_pos 호출 시 object_detection 노드가 ROI_SAVE_PATH에 ROI를 갱신함.
#     #         # 재감지 성공 시 target_pos도 정면 기준으로 정밀화됨.
#     #         self.get_logger().info("정면 위치에서 ROI 갱신 중...")
#     #         fresh_pos = self.get_target_pos(target)
#     #         if fresh_pos is not None:
#     #             target_pos = fresh_pos
#     #             self.get_logger().info(f"갱신된 target_pos: {target_pos}")
#     #         else:
#     #             self.get_logger().warn("정면 재감지 실패 — 기존 target_pos 유지")

#     #         # ── [추가 6] 컵 방향 판별 ────────────────────────────────
#     #         # align_cup: ROI를 수직으로 정렬
#     #         # check_cup_status: 상단 너비 > 하단 너비이면 True(정방향)
#     #         #   이 컵은 상단이 더 넓으므로 True = 바로 세워진 상태
#     #         # is_upright는 파지에는 영향 없이 6단계 이후 회전 여부에만 사용
#     #         try:
#     #             time.sleep(0.5)
#     #             aligned = align_cup(ROI_SAVE_PATH)
#     #             is_upright = check_cup_status(aligned)
#     #             self.get_logger().info(f"컵 방향: {'정방향' if is_upright else '역방향'}")
#     #         except Exception as e:
#     #             # ROI 파일 없음, 윤곽선 미검출 등 예외 → 정방향으로 가정하고 계속
#     #             self.get_logger().warn(f"컵 방향 판별 실패 ({e}) — 정방향으로 가정")
#     #             is_upright = True

#     #         # ── 2단계: 물체 정면으로 하강 (Z축 매칭) ─────────────────────
#     #         # 1단계에서 -200mm 뺐던 Z축을 다시 원래 컵 높이 근처로 완전히 내림 (Z값을 원래 target_pos 수준으로 복구)
#     #         # 안전을 위해 컵 중심보다 10mm 정도만 여유를 두고 하강
#     #         pick_down_pos = current_frontal_pos[0:2] + [current_frontal_pos[2]-20] + current_frontal_pos[3:]
#     #         self.get_logger().info(f"2단계 하강 이동: {pick_down_pos}")
#     #         movel(pick_down_pos, vel=VELOCITY, acc=ACC)
#     #         time.sleep(0.3)  # 하강 후 잠시 대기하여 자세 안정화
#     #         mwait()

#     #         # ── 3단계: Y축 방향으로 물체에 전진 (파지 깊이 맞추기) ──────────
#     #         # [수정] 2단계 위치(pick_down_pos)를 기준으로 정확히 슬라이싱[0:2]을 사용하여 X, Y를 유지한 채 Y만 전진
#     #         # 로봇 좌표계 기준 방향에 따라 -30 또는 +30 확인 필요 (현재 소스 기준인 -30 유지)
#     #         pick_forward_pos = [pick_down_pos[0], pick_down_pos[1] - 70, pick_down_pos[2]] + pick_down_pos[3:]
#     #         self.get_logger().info(f"3단계 전진 이동: {pick_forward_pos}")
#     #         movel(pick_forward_pos, vel=VELOCITY, acc=ACC)
#     #         time.sleep(0.3)  # 전진 후 잠시 대기하여 자세 안정화
#     #         mwait()
#     #         time.sleep(0.5)  # 추가 대기: 그리퍼가 컵을 감싸는 동안 안정화 시간 확보

#     #         # ── 4단계: 그리퍼 닫기(파지) ─────────────────────────────
#     #         self.get_logger().info("4단계: 그리퍼 닫기")
#     #         gripper.close_gripper()
#     #         while gripper.get_status()[0]:
#     #             time.sleep(0.5)
#     #         mwait()  # 파지 완료 후 1초 안정화 대기
#     #         time.sleep(0.5)  # 추가 대기: 그리퍼가 컵을 확실히 감싸는 동안 안정화 시간 확보

#     #         # ── 5단계: 안전 높이로 상승 ──────────────────────────────
#     #         # 현재 들고 있는 위치에서 Z축 방향으로 100mm 들어올림 (주변 충돌 방지)
#     #         current_posx = list(get_current_posx()[0])
#     #         pick_up_pos = current_posx[0:2] + [current_posx[2] + 100] + current_posx[3:]
#     #         self.get_logger().info(f"5단계 상승 이동: {pick_up_pos}")
#     #         movel(pick_up_pos, vel=VELOCITY, acc=ACC)
#     #         time.sleep(0.3)  # 상승 후 잠시 대기하여 자세 안정화
#     #         mwait()

#     #         # ── 6단계: 관절 홈 자세로 이동 ───────────────────────────
#     #         self.get_logger().info("6단계: 안전 홈 자세(Joint) 이동")
#     #         movej(JHOME_POS, vel=VELOCITY, acc=ACC)
#     #         mwait()

#     #         # ── 7단계: 버킷 위치 계산 및 이동 (★ 핵심 수정) ──────────────────
#     #         # 고정된 BUCKET_POS를 복사하여 가변적으로 수정할 준비를 합니다.
#     #         target_bucket_pos = list(BUCKET_POS)

#     #         if is_upright:
#     #             self.get_logger().info("정방향 컵 감지: 버킷 진입 시 6번 관절을 180도 회전시킵니다.")
#     #             # 기존 고정 각도에 180도를 더해 컵을 뒤집은 채로 버킷에 가도록 만듭니다.
#     #             target_bucket_pos[5] += 180.0
                
#     #             # (옵션) 만약 180도를 더했을 때 로봇의 관절 한계(+360도 등)를 넘어설 것 같다면 
#     #             # 반대로 180도를 빼주는 안전 처리를 더해줍니다.
#     #             if target_bucket_pos[5] > 360.0:
#     #                 target_bucket_pos[5] -= 360.0
#     #         else:
#     #             self.get_logger().info("역방향 컵 감지: 보정 없이 기존 버킷 위치로 이동합니다.")
#     #             # is_upright가 False(이미 뒤집힌 컵)이면 원래 BUCKET_POS 그대로 유지

#     #         self.get_logger().info(f"최종 버킷 이동 좌표: {target_bucket_pos}")
#     #         movej(target_bucket_pos, vel=VELOCITY, acc=ACC)
#     #         mwait()

#     #         # ── 8단계: 그리퍼 열기(해제) ─────────────────────────────
#     #         self.get_logger().info("8단계: 그리퍼 열기 및 배치 완료")
#     #         gripper.open_gripper()
#     #         while gripper.get_status()[0]:
#     #             time.sleep(0.5)
#     #         mwait()

#     #         # ── 9단계: 컵 피하기 ────────────────────────────────────
#     #         movel([350.498, 175.531, 280.101, 127.418, -98.359, -87.164], vel=VELOCITY, acc=ACC)
#     #         mwait()

#     def pick_and_place_target(self, target, target_pos):
#         """물체를 집어 버킷에 내려놓는 전체 시퀀스."""
#         self.get_logger().info("===== Pick-and-Place 시퀀스 시작 =====")

#         pick_pose = (
#             target_pos[:2]
#             + [target_pos[2] - 50]
#             + [target_pos[3]]
#             + [target_pos[4] + 45]
#             + [target_pos[5]]
#         )
#         current_frontal_pos = self.cup_frontal_position(pick_pose)

#         # ── [추가 5] 정면에서 ROI 재감지 ─────────────────────────
#         # JReady 자세에서 찍은 ROI보다 정면에서 찍은 ROI가 컵 방향 판별에 정확함.
#         # get_target_pos 호출 시 object_detection 노드가 ROI_SAVE_PATH에 ROI를 갱신함.
#         # 재감지 성공 시 target_pos도 정면 기준으로 정밀화됨.
#         self.get_logger().info("정면 위치에서 ROI 갱신 중...")
#         fresh_pos = self.get_target_pos(target)
#         if fresh_pos is not None:
#             target_pos = fresh_pos
#             self.get_logger().info(f"갱신된 target_pos: {target_pos}")
#         else:
#             self.get_logger().warn("정면 재감지 실패 — 기존 target_pos 유지")

#         # ── [추가 6] 컵 방향 판별 ────────────────────────────────
#         # align_cup: ROI를 수직으로 정렬
#         # check_cup_status: 상단 너비 > 하단 너비이면 True(정방향)
#         #   이 컵은 상단이 더 넓으므로 True = 바로 세워진 상태
#         # is_upright는 파지에는 영향 없이 6단계 이후 회전 여부에만 사용
#         try:
#             time.sleep(0.5)
#             aligned = align_cup(ROI_SAVE_PATH)
#             is_upright = check_cup_status(aligned)
#             self.get_logger().info(f"컵 방향: {'정방향' if is_upright else '역방향'}")
#         except Exception as e:
#             # ROI 파일 없음, 윤곽선 미검출 등 예외 → 정방향으로 가정하고 계속
#             self.get_logger().warn(f"컵 방향 판별 실패 ({e}) — 정방향으로 가정")
#             is_upright = True

#         pick_down_pos = (
#             current_frontal_pos[0:2] + [current_frontal_pos[2] - 20] + current_frontal_pos[3:]
#         )
#         self.get_logger().info(f"2단계 하강 이동: {pick_down_pos}")
#         self.move_l(pick_down_pos, vel=VELOCITY, acc=ACC)

# # ── [★ 핵심 수정] 3단계 전진 직전 역방향 보정 (abs 활용) ──────────────────
#         if not is_upright:
#             self.get_logger().info("역방향 컵 감지: 3단계 전진 직전, abs()를 이용하여 180도 회전시킵니다.")
            
#             # [abs 활용 로직] 180도를 더했을 때 절댓값이 180보다 커지면, 반대 방향(-180)으로 돌리는 게 최단거리입니다.
#             rotation_offset = -180 if target_pos[5] > 0.0 else -170
            
#             # 계산된 최단 거리 오프셋을 두 좌표에 똑같이 적용
#             target_pos[5] += rotation_offset
#             pick_down_pos[5] += rotation_offset
            
#             # 제자리에서 6번 관절 최단 거리 돌리기 수행
#             self.move_l(pick_down_pos, vel=VELOCITY, acc=ACC)
#         else:
#             self.get_logger().info("정방향 컵 감지: 자세 변경 없이 그대로 전진을 준비합니다.")
#         pick_forward_pos = [target_pos[0], target_pos[1] - 70, target_pos[2]] + target_pos[3:]
#         self.get_logger().info(f"3단계 전진 이동: {pick_forward_pos}")
#         self.move_l(pick_forward_pos, vel=VELOCITY, acc=ACC)

#         self.get_logger().info("4단계: 그리퍼 닫기")
#         gripper.close_gripper()
#         while gripper.get_status()[0]:
#             time.sleep(0.5)
#         mwait(1.0)

#         current_posx = list(get_current_posx()[0])
#         pick_up_pos = current_posx[0:2] + [current_posx[2] + 100] + current_posx[3:]
#         self.get_logger().info(f"5단계 상승 이동: {pick_up_pos}")
#         self.move_l(pick_up_pos, vel=VELOCITY, acc=ACC)

#         self.get_logger().info("6단계: 안전 홈 자세(Joint) 이동")
#         self.move_j(JHOME_POS, vel=VELOCITY, acc=ACC)


#         self.get_logger().info(f"최종 버킷 이동 좌표: {BUCKET_POS}")
#         movej(BUCKET_POS, vel=VELOCITY, acc=ACC)
#         mwait()

#         self.get_logger().info("8단계: 그리퍼 열기 및 배치 완료")
#         gripper.open_gripper()
#         while gripper.get_status()[0]:
#             mwait(1.0)

#         self.move_l(
#             [350.498, 175.531, 280.101, 127.418, -98.359, -87.164],
#             vel=VELOCITY,
#             acc=ACC,
#         )




# def main(args=None):
#     """
#     엔트리포인트.

#     RobotController 노드를 생성하고, ROS2가 정상 동작하는 동안
#     robot_control()을 반복 호출하여 키보드 입력 → Pick-and-Place 루프를 실행한다.
#     종료 시 노드를 정리하고 ROS2를 셧다운한다.
#     """
#     node = RobotController()

#     # rclpy.ok()가 False가 되면(Ctrl+C 등) 루프 종료
#     while rclpy.ok():
#         node.robot_control()

#     rclpy.shutdown()
#     node.destroy_node()


# if __name__ == "__main__":
#     main()