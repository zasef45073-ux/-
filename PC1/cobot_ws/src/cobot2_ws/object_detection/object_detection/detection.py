# # import numpy as np
# # import rclpy
# # from rclpy.node import Node
# # from typing import Any, Callable, Optional, Tuple

# # from ament_index_python.packages import get_package_share_directory
# # from od_msg.srv import SrvDepthPosition
# # from object_detection.realsense import ImgNode
# # from object_detection.yolo import YoloModel


# # PACKAGE_NAME = 'object_detection'
# # PACKAGE_PATH = get_package_share_directory(PACKAGE_NAME)


# # class ObjectDetectionNode(Node):
# #     def __init__(self, model_name = 'yolo'):
# #         super().__init__('object_detection_node')
# #         self.img_node = ImgNode()
# #         self.model = self._load_model(model_name)
# #         self.intrinsics = self._wait_for_valid_data(
# #             self.img_node.get_camera_intrinsic, "camera intrinsics"
# #         )
# #         self.create_service(
# #             SrvDepthPosition,
# #             'get_3d_position',
# #             self.handle_get_depth
# #         )
# #         self.get_logger().info("ObjectDetectionNode initialized.")

# #     def _load_model(self, name):
# #         """모델 이름에 따라 인스턴스를 반환합니다."""
# #         if name.lower() == 'yolo':
# #             return YoloModel()
# #         raise ValueError(f"Unsupported model: {name}")

# #     def handle_get_depth(self, request, response):
# #         """클라이언트 요청을 처리해 3D 좌표를 반환합니다."""
# #         self.get_logger().info(f"Received request: {request}")
# #         coords = self._compute_position(request.target)
# #         response.depth_position = [float(x) for x in coords]
# #         return response

# #     def _compute_position(self, target):
# #         """이미지를 처리해 객체의 카메라 좌표를 계산합니다."""
# #         rclpy.spin_once(self.img_node)

# #         box, score = self.model.get_best_detection(self.img_node, target)
# #         if box is None or score is None:
# #             self.get_logger().warn("No detection found.")
# #             return 0.0, 0.0, 0.0
        
# #         self.get_logger().info(f"Detection: box={box}, score={score}")
# #         cx, cy = map(int, [(box[0] + box[2]) / 2, (box[1] + box[3]) / 2])
# #         cz = self._get_depth(cx, cy)
# #         if cz is None:
# #             self.get_logger().warn("Depth out of range.")
# #             return 0.0, 0.0, 0.0

# #         return self._pixel_to_camera_coords(cx, cy, cz)

# #     def _get_depth(self, x, y):
# #         """픽셀 좌표의 depth 값을 안전하게 읽어옵니다."""
# #         frame = self._wait_for_valid_data(self.img_node.get_depth_frame, "depth frame")
# #         try:
# #             return frame[y, x]
# #         except IndexError:
# #             self.get_logger().warn(f"Coordinates ({x},{y}) out of range.")
# #             return None

# #     def _wait_for_valid_data(self, getter, description):
# #         """getter 함수가 유효한 데이터를 반환할 때까지 spin 하며 재시도합니다."""
# #         data = getter()
# #         while data is None or (isinstance(data, np.ndarray) and not data.any()):
# #             rclpy.spin_once(self.img_node)
# #             self.get_logger().info(f"Retry getting {description}.")
# #             data = getter()
# #         return data

# #     def _pixel_to_camera_coords(self, x, y, z):
# #         """픽셀 좌표와 intrinsics를 이용해 카메라 좌표계로 변환합니다."""
# #         fx = self.intrinsics['fx']
# #         fy = self.intrinsics['fy']
# #         ppx = self.intrinsics['ppx']
# #         ppy = self.intrinsics['ppy']
# #         return (
# #             (x - ppx) * z / fx,
# #             (y - ppy) * z / fy,
# #             z
# #         )


# # def main(args=None):
# #     rclpy.init(args=args)
# #     node = ObjectDetectionNode()
# #     try:
# #         rclpy.spin(node)
# #     finally:
# #         node.destroy_node()
# #         rclpy.shutdown()


# # if __name__ == '__main__':
# #     main()
















# import cv2
# import numpy as np
# import rclpy
# from rclpy.node import Node
# from typing import Any, Callable, Optional, Tuple

# from ament_index_python.packages import get_package_share_directory
# from od_msg.srv import SrvDepthPosition
# from object_detection.realsense import ImgNode
# from object_detection.yolo import YoloModel


# PACKAGE_NAME = 'object_detection'
# PACKAGE_PATH = get_package_share_directory(PACKAGE_NAME)

# # robot_control_final_v2.py와 공유하는 ROI 저장 경로
# ROI_SAVE_PATH = "/tmp/cup_roi.png"


# class ObjectDetectionNode(Node):
#     def __init__(self, model_name = 'yolo'):
#         """객체 탐지/깊이 추정 서비스를 제공하는 ROS2 노드 초기화.

#         초기화 순서:
#         1) RealSense 이미지 수신 노드 생성
#         2) 탐지 모델 로딩
#         3) 카메라 내부 파라미터(intrinsics) 확보
#         4) 서비스(get_3d_position) 등록
#         """
#         super().__init__('object_detection_node')
#         # 색상/깊이 프레임을 제공하는 보조 노드
#         self.img_node = ImgNode()
#         # 현재는 YOLO만 지원하지만, 추후 모델 교체를 위해 팩토리 형태 유지
#         self.model = self._load_model(model_name)
#         # 좌표 변환에 필요한 intrinsics가 유효할 때까지 대기
#         self.intrinsics = self._wait_for_valid_data(
#             self.img_node.get_camera_intrinsic, "camera intrinsics"
#         )
#         # 외부 노드가 3D 위치를 요청할 때 호출될 서비스 콜백 등록
#         self.create_service(
#             SrvDepthPosition,
#             'get_3d_position',
#             self.handle_get_depth
#         )
#         self.get_logger().info("ObjectDetectionNode initialized.")

#     def _load_model(self, name):
#         """모델 이름으로 탐지 모델 인스턴스를 생성한다."""
#         if name.lower() == 'yolo':
#             return YoloModel()
#         raise ValueError(f"Unsupported model: {name}")

#     def handle_get_depth(self, request, response):
#         """서비스 요청(target 라벨)에 대해 카메라 좌표계 3D 위치를 반환한다."""
#         self.get_logger().info(f"Received request: {request}")
#         # 요청한 타깃 객체의 중심점 기준 (x, y, z) 계산
#         coords = self._compute_position(request.target)
#         # ROS 메시지 타입 호환을 위해 float 리스트로 명시적 변환
#         response.depth_position = [float(x) for x in coords]
#         return response

#     def _compute_position(self, target):
#         """탐지 + depth 조회를 결합해 타깃의 3D 좌표를 계산한다.

#         반환값:
#             (x, y, z) in camera coordinate
#             실패 시 (0.0, 0.0, 0.0)
#         """
#         # 최신 프레임을 반영하기 위해 한 번 spin
#         rclpy.spin_once(self.img_node)

#         # 타깃 라벨에 대해 가장 신뢰도 높은 바운딩 박스 선택
#         box, score = self.model.get_best_detection(self.img_node, target)
#         if box is None or score is None:
#             self.get_logger().warn("No detection found.")
#             return 0.0, 0.0, 0.0

#         self.get_logger().info(f"Detection: box={box}, score={score}")

#         # 후속 파이프라인(컵 방향 판별)에서 사용할 ROI 이미지 저장
#         self._save_roi(box)

#         # 바운딩박스 중심 픽셀 좌표(cx, cy) 계산
#         cx, cy = map(int, [(box[0] + box[2]) / 2, (box[1] + box[3]) / 2])
#         # 중심 픽셀에서 depth(z) 획득
#         cz = self._get_depth(cx, cy)
#         if cz is None:
#             self.get_logger().warn("Depth out of range.")
#             return 0.0, 0.0, 0.0

#         # 픽셀 좌표 + depth를 카메라 3D 좌표로 변환
#         return self._pixel_to_camera_coords(cx, cy, cz)

#     def _save_roi(self, box):
#         """바운딩박스 영역을 컬러 프레임에서 잘라 파일로 저장한다.

#         ROI 이미지는 다른 프로세스가 바로 읽을 수 있도록 고정 경로에 덮어쓴다.
#         """
#         # 컬러 프레임이 아직 준비되지 않았으면 저장하지 않음
#         color_frame = self.img_node.get_color_frame()
#         if color_frame is None:
#             self.get_logger().warn("ROI 저장 실패: 컬러 프레임 없음")
#             return

#         # 박스 좌표를 정수화하고 프레임 경계 안으로 보정(clamp)
#         x1, y1, x2, y2 = map(int, box)
#         h, w = color_frame.shape[:2]
#         x1, y1 = max(0, x1), max(0, y1)
#         x2, y2 = min(w, x2), min(h, y2)

#         # numpy 슬라이싱으로 ROI 추출
#         roi = color_frame[y1:y2, x1:x2]
#         if roi.size == 0:
#             self.get_logger().warn("ROI 저장 실패: 빈 영역")
#             return

#         # 이미지 파일로 저장 (성공/실패 여부가 필요하면 반환값으로 확장 가능)
#         cv2.imwrite(ROI_SAVE_PATH, roi)
#         self.get_logger().info(f"ROI 저장 완료: {ROI_SAVE_PATH}")

#     def _get_depth(self, x, y):
#         """픽셀 좌표(x, y)의 depth 값을 안전하게 읽어온다."""
#         # depth 프레임이 준비될 때까지 대기
#         frame = self._wait_for_valid_data(self.img_node.get_depth_frame, "depth frame")
#         try:
#             # numpy 인덱싱은 [row, col] == [y, x]
#             return frame[y, x]
#         except IndexError:
#             self.get_logger().warn(f"Coordinates ({x},{y}) out of range.")
#             return None

#     def _wait_for_valid_data(self, getter, description):
#         """getter가 유효 데이터를 반환할 때까지 spin/retry를 반복한다."""
#         data = getter()
#         # ndarray인 경우 all-zero 프레임도 무효 데이터로 간주
#         while data is None or (isinstance(data, np.ndarray) and not data.any()):
#             rclpy.spin_once(self.img_node)
#             self.get_logger().info(f"Retry getting {description}.")
#             data = getter()
#         return data

#     def _pixel_to_camera_coords(self, x, y, z):
#         """핀홀 카메라 모델로 픽셀 좌표를 카메라 좌표계로 투영한다.

#         X = (x - ppx) * z / fx
#         Y = (y - ppy) * z / fy
#         Z = z
#         """
#         fx = self.intrinsics['fx']
#         fy = self.intrinsics['fy']
#         ppx = self.intrinsics['ppx']
#         ppy = self.intrinsics['ppy']
#         return (
#             (x - ppx) * z / fx,
#             (y - ppy) * z / fy,
#             z
#         )


# def main(args=None):
#     """ROS2 엔트리포인트: 노드를 생성하고 스핀 루프를 실행한다."""
#     rclpy.init(args=args)
#     node = ObjectDetectionNode()
#     try:
#         rclpy.spin(node)
#     finally:
#         node.destroy_node()
#         rclpy.shutdown()


# if __name__ == '__main__':
#     main()




import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from typing import Any, Callable, Optional, Tuple

from ament_index_python.packages import get_package_share_directory
from od_msg.srv import SrvDepthPosition
from object_detection.realsense import ImgNode
from object_detection.yolo import YoloModel


PACKAGE_NAME = 'object_detection'
PACKAGE_PATH = get_package_share_directory(PACKAGE_NAME)

# robot_control_final_v2.py와 공유하는 ROI 저장 경로
ROI_SAVE_PATH = "/tmp/cup_roi.png"


class ObjectDetectionNode(Node):
    def __init__(self, model_name = 'yolo'):
        """객체 탐지/깊이 추정 서비스를 제공하는 ROS2 노드 초기화.

        초기화 순서:
        1) RealSense 이미지 수신 노드 생성
        2) 탐지 모델 로딩
        3) 카메라 내부 파라미터(intrinsics) 확보
        4) 서비스(get_3d_position) 등록
        """
        super().__init__('object_detection_node')
        # 색상/깊이 프레임을 제공하는 보조 노드
        self.img_node = ImgNode()
        # 현재는 YOLO만 지원하지만, 추후 모델 교체를 위해 팩토리 형태 유지
        self.model = self._load_model(model_name)
        # 좌표 변환에 필요한 intrinsics가 유효할 때까지 대기
        self.intrinsics = self._wait_for_valid_data(
            self.img_node.get_camera_intrinsic, "camera intrinsics"
        )
        # 외부 노드가 3D 위치를 요청할 때 호출될 서비스 콜백 등록
        self.create_service(
            SrvDepthPosition,
            'get_3d_position',
            self.handle_get_depth
        )
        self.get_logger().info("ObjectDetectionNode initialized.")

    def _load_model(self, name):
        """모델 이름으로 탐지 모델 인스턴스를 생성한다."""
        if name.lower() == 'yolo':
            return YoloModel()
        raise ValueError(f"Unsupported model: {name}")

    def handle_get_depth(self, request, response):
        """서비스 요청(target 라벨)에 대해 카메라 좌표계 3D 위치를 반환한다."""
        self.get_logger().info(f"Received request: {request}")
        # 요청한 타깃 객체의 중심점 기준 (x, y, z) 계산
        coords = self._compute_position(request.target)
        # ROS 메시지 타입 호환을 위해 float 리스트로 명시적 변환
        response.depth_position = [float(x) for x in coords]
        return response

    def _compute_position(self, target):
        """탐지 + depth 조회를 결합해 타깃의 3D 좌표를 계산한다.

        반환값:
            (x, y, z) in camera coordinate
            실패 시 (0.0, 0.0, 0.0)
        """
        # 최신 프레임을 반영하기 위해 한 번 spin
        rclpy.spin_once(self.img_node)

        # 타깃 라벨에 대해 가장 신뢰도 높은 바운딩 박스 선택
        box, score = self.model.get_best_detection(self.img_node, target)
        if box is None or score is None:
            self.get_logger().warn("No detection found.")
            return 0.0, 0.0, 0.0

        self.get_logger().info(f"Detection: box={box}, score={score}")

        # 후속 파이프라인(컵 방향 판별)에서 사용할 ROI 이미지 저장
        self._save_roi(box)

        # 바운딩박스 중심 픽셀 좌표(cx, cy) 계산
        cx, cy = map(int, [(box[0] + box[2]) / 2, (box[1] + box[3]) / 2])
        # 중심 픽셀에서 depth(z) 획득
        cz = self._get_depth(cx, cy)
        if cz is None:
            self.get_logger().warn("Depth out of range.")
            return 0.0, 0.0, 0.0

        # 픽셀 좌표 + depth를 카메라 3D 좌표로 변환
        return self._pixel_to_camera_coords(cx, cy, cz)

    def _save_roi(self, box):
        """바운딩박스 영역을 컬러 프레임에서 잘라 파일로 저장한다.

        ROI 이미지는 다른 프로세스가 바로 읽을 수 있도록 고정 경로에 덮어쓴다.
        """
        # 컬러 프레임이 아직 준비되지 않았으면 저장하지 않음
        color_frame = self.img_node.get_color_frame()
        if color_frame is None:
            self.get_logger().warn("ROI 저장 실패: 컬러 프레임 없음")
            return

        # 박스 좌표를 정수화하고 프레임 경계 안으로 보정(clamp)
        x1, y1, x2, y2 = map(int, box)
        h, w = color_frame.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)

        # numpy 슬라이싱으로 ROI 추출
        roi = color_frame[y1:y2, x1:x2]
        if roi.size == 0:
            self.get_logger().warn("ROI 저장 실패: 빈 영역")
            return

        # 이미지 파일로 저장 (성공/실패 여부가 필요하면 반환값으로 확장 가능)
        cv2.imwrite(ROI_SAVE_PATH, roi)
        self.get_logger().info(f"ROI 저장 완료: {ROI_SAVE_PATH}")

    def _get_depth(self, x, y):
        """픽셀 좌표(x, y)의 depth 값을 안전하게 읽어온다."""
        # depth 프레임이 준비될 때까지 대기
        frame = self._wait_for_valid_data(self.img_node.get_depth_frame, "depth frame")
        try:
            # numpy 인덱싱은 [row, col] == [y, x]
            return frame[y, x]
        except IndexError:
            self.get_logger().warn(f"Coordinates ({x},{y}) out of range.")
            return None

    def _wait_for_valid_data(self, getter, description):
        """getter가 유효 데이터를 반환할 때까지 spin/retry를 반복한다."""
        data = getter()
        # ndarray인 경우 all-zero 프레임도 무효 데이터로 간주
        while data is None or (isinstance(data, np.ndarray) and not data.any()):
            rclpy.spin_once(self.img_node)
            self.get_logger().info(f"Retry getting {description}.")
            data = getter()
        return data

    def _pixel_to_camera_coords(self, x, y, z):
        """핀홀 카메라 모델로 픽셀 좌표를 카메라 좌표계로 투영한다.

        X = (x - ppx) * z / fx
        Y = (y - ppy) * z / fy
        Z = z
        """
        fx = self.intrinsics['fx']
        fy = self.intrinsics['fy']
        ppx = self.intrinsics['ppx']
        ppy = self.intrinsics['ppy']
        return (
            (x - ppx) * z / fx,
            (y - ppy) * z / fy,
            z
        )


def main(args=None):
    """ROS2 엔트리포인트: 노드를 생성하고 스핀 루프를 실행한다."""
    rclpy.init(args=args)
    node = ObjectDetectionNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

