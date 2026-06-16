#0526 #############112-194(cleanup노드 추가)

import os
import rclpy
import pyaudio
import json
import time
import audioop
import requests
import threading
from rclpy.node import Node
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from dotenv import load_dotenv
import openai
import chromadb

from std_msgs.msg import String  

from ament_index_python.packages import get_package_share_directory

try:
    from cocktail_order_interfaces.action import CocktailOrder
    from cocktail_order_interfaces.srv import TriggerCleanup  
except ImportError:
    pass

try:
    from .MicController import MicController, MicConfig
    from .wakeup_word import WakeupWord
    from .stt import STT
    from .tts import TTS
    from .firebase_store import get_firebase_store
except ImportError:
    from MicController import MicController, MicConfig
    from wakeup_word import WakeupWord
    from stt import STT
    from tts import TTS
    from firebase_store import get_firebase_store

PACKAGE_NAME = "cocktail_order_pkg"
try:
    RESOURCE_PATH = os.path.join(get_package_share_directory(PACKAGE_NAME), "resource")
except Exception:
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    RESOURCE_PATH = os.path.join(CURRENT_DIR, "resource")

ENV_PATH = os.path.join(RESOURCE_PATH, ".env")
BEEP_PATH = os.path.join(RESOURCE_PATH, "beep.mp3")
DB_PATH = os.path.join(RESOURCE_PATH, "cocktail_vector_db")

load_dotenv(dotenv_path=ENV_PATH)
openai_api_key = os.getenv("OPENAI_API_KEY")
client = openai.OpenAI(api_key=openai_api_key)

class IntegratedOrderManager(Node):
    def __init__(self):
        super().__init__("integrated_order_node")

        self.stt = STT(openai_api_key=openai_api_key)
        self.tts = TTS(openai_api_key=openai_api_key)

        # ===== Firebase 연결 초기화 시작 =====
        self.firebase_store = get_firebase_store()
        if self.firebase_store.enabled:
            self.get_logger().info("Firebase order logging is enabled.")
        else:
            self.get_logger().info("Firebase order logging is disabled.")
        # ===== Firebase 연결 초기화 끝 =====
        
        self.mic_config = MicConfig(
            chunk=1024, rate=48000, channels=1, record_seconds=5,
            fmt=pyaudio.paInt16, device_index=4, buffer_size=24000,
        )
        self.mic_controller = MicController(config=self.mic_config)
        self.wakeup_word = WakeupWord(self.mic_config.buffer_size)

        # 🌟 GPT가 확실히 복사할 수 있도록 예비 리스트에도 레시피 코드를 명시
        self.menu_db_fallback = [
            "블랙 러시안 (8,000원, 레시피코드: RECIPE_BR_01)", 
            "모히또 (7,500원, 레시피코드: RECIPE_MH_01)", 
            "깔루아 밀크 (7,000원, 레시피코드: RECIPE_KM_01)"
        ]
        
        try:
            self.get_logger().info(f"💾 Vector DB 로드 경로: {DB_PATH}")
            self.chroma_client = chromadb.PersistentClient(path=DB_PATH)
            self.collection = self.chroma_client.get_or_create_collection(name="cocktails")
        except Exception as e:
            self.collection = None

        self.VOLUME_THRESHOLD = 300  
        self.SILENCE_LIMIT = 1.8     
        self.TIMEOUT_LIMIT = 5.0     
        self.MAX_RECORD_TIME = 20.0  

        self.state = "IDLE"
        self.ask_cancel_requested = False
        self.is_recording = False  # 🌟 [추가] 현재 마이크 녹음 중인지 확인하는 플래그

        # ===== Firebase 주문 키 추적 시작 =====
        self.last_order_key = None
        # ===== Firebase 주문 키 추적 끝 =====

        try:
            self.mic_controller.open_stream()
            self.wakeup_word.set_stream(self.mic_controller.stream)
        except OSError:
            self.get_logger().error("마이크 스트림 오픈 실패")

        self.mutually_exclusive_group = ReentrantCallbackGroup()

        self._action_server = ActionServer(
            self, CocktailOrder, 'cocktail_order',
            execute_callback=self.execute_callback,
            goal_callback=self.goal_callback,
            cancel_callback=self.cancel_callback,
            callback_group=self.mutually_exclusive_group
        )

        #0526추가##트리거 구독 및 피드백 발행자 추가 (기존 pub/sub 모아두는 곳에 작성)####0##
        self._trigger_sub = self.create_subscription(
            String, '/cup_cleanup/ask_trigger', self.trigger_callback, 10,
            callback_group=self.mutually_exclusive_group
        )
        self._feedback_pub = self.create_publisher(
            String, '/cup_cleanup/robot_feedback', 10
        )
        self._robot_trigger_pub = self.create_publisher(
            String, '/cup_cleanup/trigger', 10
        )
        #0526##########################################################################

        self._recipe_pub = self.create_publisher(String, '/robot_recipe_trigger', 10)

        self.get_logger().info("🍹 [READY] 칵테일 주문 통합 브레인 가동 완료.")

        self.wakeup_thread = threading.Thread(target=self.wakeup_loop, daemon=True)
        self.wakeup_thread.start()


    #0526 추가 트리거 수신 콜백 함수 추가#################################################
    def _legacy_trigger_callback_unused(self, msg):
        try:
            payload = json.loads(msg.data)
            event_type = payload.get("event_type")
            
            # ASK_TRIGGER(치울지 물어보기) 이벤트만 이 노드에서 처리합니다.
            if event_type == "ASK_TRIGGER":
                self.get_logger().info("📥 [수신] 컵 수거 질문 트리거(ASK_TRIGGER) 감지!")
                # 마이크 스트림 블로킹 방지를 위해 별도 스레드로 실행
                threading.Thread(target=self.process_ask_trigger, args=(payload,), daemon=True).start()
        except Exception as e:
            self.get_logger().error(f"트리거 파싱 에러: {e}")

    # 🌟 3. 음성 질문 및 판단 로직 
    def _legacy_process_ask_trigger_unused(self, payload):
        if self.state != "IDLE":
            self.get_logger().warn("⚠️ 로봇이 대화 중입니다. 수거 질문을 무시합니다.")
            return

        self.state = "CLEANUP_CHECK"
        cup_id = payload.get("cup_id")
        source_cup_id = payload.get("source_cup_id")

        self.tts.text2speech("손님, 다 드신 잔을 치워드릴까요?")
        audio_binary = self.record_dynamic_audio()
        
        if not audio_binary:
            self.tts.text2speech("대답이 없으셔서 잔은 그대로 두겠습니다.")
            self.publish_ask_feedback(source_cup_id, cup_id, "cancelled", "user_silence")
            self.reset_to_idle()
            return

        self.get_logger().info("🤖 Whisper STT 연산 요청 중...")
        user_text = self.stt.speech2text_from_bytes(audio_binary, self.mic_config).strip()
        self.get_logger().info(f"🗣️ 수거 제안 유저 발화: '{user_text}'")

        affirmative_keywords = ["응", "네", "어", "치워", "그래", "치워줘", "가져가", "오케이", "좋아", "치워라"]

        if any(k in user_text.lower() for k in affirmative_keywords):
            self.tts.text2speech("잔을 안전하게 치워드릴게요. 로봇이 움직이니 잠시 몸을 뒤로 물려주세요.")
            # 🌟 수락 시 'completed' 발송 -> 비전 서버가 이를 받고 로봇을 움직이게 함
            self.publish_ask_feedback(source_cup_id, cup_id, "completed", "user_accepted")
        else:
            self.tts.text2speech("알겠습니다. 편안한 시간 보내세요.")
            # 🌟 거절 시 'cancelled' 발송
            self.publish_ask_feedback(source_cup_id, cup_id, "cancelled", "user_declined")

        self.reset_to_idle()

    # 🌟 4. 피드백 발송 함수
    def _legacy_publish_ask_feedback_unused(self, source_cup_id, cup_id, status, reason):
        payload = {
            "event_type": "ASK_ACTION_FINISHED",
            "status": status,  # "completed" 또는 "cancelled"
            "reason": reason,
            "source_cup_id": source_cup_id,
            "cup_id": cup_id,
            "timestamp": time.time()
        }
        msg = String()
        msg.data = json.dumps(payload)
        self._feedback_pub.publish(msg)
        self.get_logger().info(f"📤 [송신] 로봇 피드백 전송 완료: {status} ({reason})")
    #0526 추가 트리거 수신 콜백 함수 추가#################################################

    # 🌟 복구됨: 원격 비전 서버 실시간 감정 연동
    def trigger_callback(self, msg):
        try:
            payload = json.loads(msg.data)
            event_type = payload.get("event_type")

            if event_type == "ASK_TRIGGER":
                self.ask_cancel_requested = False
                self.get_logger().info("Received ASK_TRIGGER for cleanup confirmation.")
                threading.Thread(
                    target=self.process_ask_trigger,
                    args=(payload,),
                    daemon=True,
                ).start()
            elif event_type == "CANCEL_ASK_TRIGGER":
                self.ask_cancel_requested = True
                self.get_logger().info("Received CANCEL_ASK_TRIGGER. Voice cleanup prompt will stop.")
                self.reset_to_idle()
        except Exception as e:
            self.get_logger().error(f"Trigger parsing error: {e}")

    def process_ask_trigger(self, payload):
        if self.state != "IDLE":
            self.get_logger().warn("Another action is already running. The cleanup ask will be ignored.")
            return

        self.state = "CLEANUP_CHECK"
        cup_id = payload.get("cup_id")
        source_cup_id = payload.get("source_cup_id", cup_id)

        self.tts.text2speech("손님, 이 컵을 치워드릴까요?")
        audio_binary = self.record_dynamic_audio()
        if self.ask_cancel_requested:
            self.get_logger().info("ASK cancellation arrived while listening. The cleanup prompt will stop.")
            self.reset_to_idle()
            return

        if not audio_binary:
            self.tts.text2speech("응답이 없어서 이 컵은 그대로 두겠습니다.")
            self.publish_ask_feedback(source_cup_id, cup_id, "cancelled", "user_silence")
            self.reset_to_idle()
            return

        self.get_logger().info("Requesting Whisper STT for cleanup confirmation.")
        user_text = self.stt.speech2text_from_bytes(audio_binary, self.mic_config).strip()
        self.get_logger().info(f"Voice cleanup answer: '{user_text}'")
        if self.ask_cancel_requested:
            self.get_logger().info("ASK cancellation arrived after STT. The cleanup result will be ignored.")
            self.reset_to_idle()
            return

        negative_keywords = ["아니", "하지마", "두세요", "그대로", "괜찮", "노", "no", "치우지마", "놔둬"]
        affirmative_keywords = ["yes", "네", "예", "응", "그래", "좋아", "치워", "가져가"]

        user_text_lower = user_text.lower()

        if any(keyword in user_text_lower for keyword in negative_keywords):
            self.tts.text2speech("알겠습니다. 이 컵은 그대로 두겠습니다.")
            self.publish_ask_feedback(source_cup_id, cup_id, "cancelled", "user_declined")

        if any(keyword in user_text.lower() for keyword in affirmative_keywords):
            self.tts.text2speech("컵을 치우겠습니다. 로봇이 곧 움직이니 손을 치워주세요.")
            self.publish_pick_trigger(source_cup_id, cup_id)
        else:
            self.tts.text2speech("알겠습니다. 이 컵은 그대로 두겠습니다.")
            self.publish_ask_feedback(source_cup_id, cup_id, "cancelled", "user_declined")

        self.reset_to_idle()

    def publish_pick_trigger(self, source_cup_id, cup_id):
        payload = {
            "event_type": "CUP_PICK_TRIGGER",
            "source_cup_id": source_cup_id,
            "cup_id": cup_id,
            "timestamp": time.time(),
        }
        msg = String()
        msg.data = json.dumps(payload)
        self._robot_trigger_pub.publish(msg)
        self.get_logger().info(
            f"Published robot pick trigger: source_cup_id={source_cup_id}, cup_id={cup_id}"
        )

        # ===== Firebase 컵 정리 이벤트 저장 + robot_status 업데이트 시작 =====
        self._save_cleanup_event_to_firebase(payload)
        self._update_order_status_in_firebase("cleanup_in_progress")
        # ===== Firebase 컵 정리 이벤트 저장 + robot_status 업데이트 끝 =====

    def publish_ask_feedback(self, source_cup_id, cup_id, status, reason):
        payload = {
            "event_type": "ASK_ACTION_FINISHED",
            "status": status,
            "reason": reason,
            "source_cup_id": source_cup_id,
            "cup_id": cup_id,
            "timestamp": time.time(),
        }
        msg = String()
        msg.data = json.dumps(payload)
        self._feedback_pub.publish(msg)
        self.get_logger().info(f"Published ASK feedback: {status} ({reason})")

        # ===== Firebase 컵 정리 이벤트 저장 + robot_status 업데이트 시작 =====
        self._save_cleanup_event_to_firebase(payload)
        mapped_status = "cleanup_completed" if status == "completed" else "cleanup_cancelled"
        self._update_order_status_in_firebase(mapped_status)
        # ===== Firebase 컵 정리 이벤트 저장 + robot_status 업데이트 끝 =====

    def get_initial_vision_emotion(self):
        self.get_logger().info("📸 원격 비전 서버에 실시간 감정 인식 JSON 데이터 요청 중...")
        try:
            url = "http://192.168.10.27:8000/analyze/"
            response = requests.post(url, timeout=3.0)
                
            if response.status_code == 200:
                result = response.json().get("component_results", {})
                raw_emotion = result.get("emotion", {})
                cleaned_emotion = {k: round(float(v), 2) for k, v in raw_emotion.items()}
                self.get_logger().info(f"✅ 실시간 비전 감정 JSON 획득 성공: {cleaned_emotion}")
                return cleaned_emotion
            else:
                self.get_logger().warn(f"⚠️ 비전 서버 응답 에러 (Status Code: {response.status_code})")
        except Exception as e:
            self.get_logger().error(f"❌ 비전 서버 통신 실패 (안전 기본값 사용): {e}")
        
        return {"angry": 0.0, "happy": 0.0, "sad": 0.0, "surprise": 0.0, "neutral": 100.0}

    # 🌟 수정됨: 마이크 프리징을 막는 안전한 소프트 버퍼 플러시
    def flush_mic_buffer(self, verbose=True):
        try:
            stream = self.mic_controller.stream
            
            # 1. 현재 OS 오디오 하드웨어 버퍼에 밀려있는(고여있는) 모든 프레임의 개수를 파악합니다.
            available_frames = stream.get_read_available()
            
            # 2. 고여있는 데이터가 1프레임이라도 있다면, 그 양만큼 '한 번에' 읽어서 허공에 날려버립니다.
            if available_frames > 0:
                stream.read(available_frames, exception_on_overflow=False)
                if verbose:
                    self.get_logger().info(f"🧹 마이크 버퍼 완벽 청소 완료 (버려진 잔향: {available_frames} 프레임)")
                
        except Exception as e:
            self.get_logger().error(f"마이크 버퍼 플러시 중 에러 발생: {e}")

    def reset_to_idle(self):
        time.sleep(7.0) 
        self.flush_mic_buffer()
        self.state = "IDLE"
        self.get_logger().info("👂 다시 대기 상태(IDLE)로 전환되었습니다. '헬로 로키'를 부르거나 트리거를 기다리는 중...")

    def wakeup_loop(self):
        self.get_logger().info("👂 웨이크워드 상시 감시 마이크가 켜졌습니다. ('헬로 로키'를 불러주세요)")
        while rclpy.ok():
            if self.state == "IDLE":
                try:
                    if self.wakeup_word.is_wakeup():
                        self.get_logger().info("🔥 웨이크워드 감지됨! 주문 대화를 즉시 시작합니다.")
                        self.state = "ACTION_RUNNING"
                        self.run_dialogue_session(goal_handle=None)
                except Exception:
                    pass
                time.sleep(0.1) # IDLE 상태일 때의 최소 루프 주기
            else:
                # 🌟 [필수 수정] 로봇이 대화 중이거나 컵 수거 중일 때는
                # 마이크 자원을 완전히 양보하고 이 스레드를 0.5초 동안 확실하게 재웁니다.
                if not getattr(self, 'is_recording', False):
                    self.flush_mic_buffer(verbose=False)
                time.sleep(0.1)

    def goal_callback(self, goal_request): return GoalResponse.ACCEPT
    def cancel_callback(self, goal_handle): return CancelResponse.ACCEPT

    def cleanup_ask_callback(self, request, response):
        if self.state != "IDLE":
            response.success = False
            return response

        self.state = "CLEANUP_CHECK"
        self.tts.text2speech("손님, 다 드신 잔을 치워드릴까요?")
        audio_binary = self.record_dynamic_audio()
        
        if not audio_binary:
            self.tts.text2speech("대답이 없으셔서 잔은 그대로 두겠습니다.")
            self.reset_to_idle()
            response.success = False
            return response

        self.get_logger().info("🤖 Whisper STT 연산 요청 중...")
        user_text = self.stt.speech2text_from_bytes(audio_binary, self.mic_config).strip()
        self.get_logger().info(f"🗣️ 수거 제안 유저 발화: '{user_text}'")

        affirmative_keywords = ["응", "네", "어", "치워", "그래", "치워줘", "가져가", "오케이", "좋아", "치워라"]

        if any(k in user_text.lower() for k in affirmative_keywords):
            self.tts.text2speech("잔을 안전하게 치워드릴게요. 로봇이 움직이니 잠시 몸을 뒤로 물려주세요.")
            response.success = True
        else:
            self.tts.text2speech("알겠습니다. 잔은 그대로 두겠습니다. 편안한 시간 보내세요.")
            response.success = False

        self.reset_to_idle()
        return response

    def execute_callback(self, goal_handle):
        return self.run_dialogue_session(goal_handle=goal_handle)

    # ===== Firebase 주문 저장 보조 함수 시작 =====
    def _save_order_to_firebase(self, menu, recipe_code, dialogue_turn, emotion_snapshot):
        if not self.firebase_store or not self.firebase_store.enabled:
            return None

        payload = {
            "event_type": "ORDER_CONFIRMED",
            "menu": menu,
            "recipe_code": recipe_code,
            "dialogue_turn": dialogue_turn,
            "robot_status": "pending",
            "emotion": emotion_snapshot,
            "source": "integrated_order_node",
        }

        try:
            firebase_key = self.firebase_store.save_order(payload)
            if firebase_key:
                # ===== Firebase 주문 키 저장 시작 =====
                self.last_order_key = firebase_key
                # ===== Firebase 주문 키 저장 끝 =====
                self.get_logger().info(f"Firebase order saved: {firebase_key}")
            else:
                self.get_logger().warn("Firebase save skipped. Check config or credentials.")
            return firebase_key
        except Exception as e:
            self.get_logger().error(f"Firebase order save failed: {e}")
            return None

    # ===== Firebase robot_status 업데이트 보조 함수 시작 =====
    def _update_order_status_in_firebase(self, status):
        if not self.firebase_store or not self.firebase_store.enabled:
            return

        if not self.last_order_key:
            self.get_logger().warn("No saved order key. robot_status update skipped.")
            return

        try:
            ok = self.firebase_store.update_order_status(self.last_order_key, status)
            if ok:
                self.get_logger().info(
                    f"Firebase robot_status updated: {self.last_order_key} -> {status}"
                )
            else:
                self.get_logger().warn("Firebase robot_status update skipped.")
        except Exception as e:
            self.get_logger().error(f"Firebase robot_status update failed: {e}")
    # ===== Firebase robot_status 업데이트 보조 함수 끝 =====

    # ===== Firebase 컵 정리 이벤트 저장 보조 함수 시작 =====
    def _save_cleanup_event_to_firebase(self, payload):
        if not self.firebase_store or not self.firebase_store.enabled:
            return None

        try:
            firebase_key = self.firebase_store.save_cleanup_event(payload)
            if firebase_key:
                self.get_logger().info(f"Firebase cleanup event saved: {firebase_key}")
            else:
                self.get_logger().warn("Firebase cleanup event save skipped.")
            return firebase_key
        except Exception as e:
            self.get_logger().error(f"Firebase cleanup event save failed: {e}")
            return None
    # ===== Firebase 컵 정리 이벤트 저장 보조 함수 끝 =====
    # ===== Firebase 주문 저장 보조 함수 끝 =====

    def run_dialogue_session(self, goal_handle=None):
        self.get_logger().info("🎯 주문 접수 비즈니스 로직 시퀀스 가동 시작!")
        self.state = "ACTION_RUNNING"

        feedback_msg = CocktailOrder.Feedback() if goal_handle else None
        result = CocktailOrder.Result() if goal_handle else None
        
        dialogue_turn = 0
        MAX_TURNS = 10
        user_preference = ""
        
        # 🌟 비전 감정 연동 복구
        current_emotion_parameters = self.get_initial_vision_emotion()
        
        self.tts.text2speech("안녕하세요! 스마트 웨이터 로봇입니다. 원하시는 칵테일이 있으신가요, 아니면 추천해 드릴까요?")

        while dialogue_turn < MAX_TURNS:
            if goal_handle and goal_handle.is_cancel_requested:
                goal_handle.canceled()
                if result: result.is_success = False
                self.reset_to_idle()
                return result if goal_handle else None

            audio_binary = self.record_dynamic_audio()
            
            if not audio_binary:
                self.tts.text2speech("잘 듣지 못했어요. 다시 한 번 말씀해 주시겠어요?")
                continue

            self.get_logger().info("🤖 Whisper STT 연산 요청 중...")
            user_text = self.stt.speech2text_from_bytes(audio_binary, self.mic_config).strip()
            
            if not user_text or any(h in user_text.lower() for h in ["share this", "구독", "시청해"]):
                self.tts.text2speech("주변 소음 때문에 놓쳤어요. 다시 말씀해 주시겠어요?")
                continue

            self.get_logger().info(f"🗣️ 인식된 텍스트: {user_text}")
            dialogue_turn += 1

            status, menu, recipe_code, bot_message, updated_emotion = self.process_gpt_logic(
                user_text, user_preference, dialogue_turn, current_emotion_parameters
            )
            
            # 🌟 감정 파라미터 변화 로그 복구
            if updated_emotion:
                current_emotion_parameters = updated_emotion
                self.get_logger().info(f"📈 [{dialogue_turn}턴] 조절된 감정 파라미터: {current_emotion_parameters}")
            
            if goal_handle:
                feedback_msg.current_turn = dialogue_turn
                feedback_msg.user_text = user_text
                feedback_msg.bot_message = bot_message
                goal_handle.publish_feedback(feedback_msg)

            user_preference += f" 유저: {user_text}\n 웨이터: {bot_message}\n"
            self.tts.text2speech(bot_message)

            if status == "success":
                self.get_logger().info(f"🏆 [최종 승인 완료] 메뉴: {menu} | 레시피: {recipe_code}")
                recipe_msg = String()
                recipe_msg.data = recipe_code
                self._recipe_pub.publish(recipe_msg)

                # ===== Firebase 주문 저장 호출 시작 =====
                self._save_order_to_firebase(
                    menu=menu,
                    recipe_code=recipe_code,
                    dialogue_turn=dialogue_turn,
                    emotion_snapshot=current_emotion_parameters,
                )
                self._update_order_status_in_firebase("recipe_triggered")
                # ===== Firebase 주문 저장 호출 끝 =====
                
                if goal_handle: goal_handle.succeed()
                if result: 
                    result.is_success = True
                    result.final_menu = menu
                    result.recipe_code = recipe_code
                
                self.reset_to_idle()
                return result if goal_handle else None
        
        self.tts.text2speech("대화 시간이 초과되어 주문을 초기화합니다. 처음부터 다시 시작해 주세요.")
        if goal_handle: goal_handle.abort()
        if result: result.is_success = False
        self.reset_to_idle()
        return result if goal_handle else None

    def record_dynamic_audio(self):
        self.is_recording = True
        try:
            # 1. 로봇 TTS 대사가 끝나고 안내음이 나오기 전 최소한의 안정화 시간
            time.sleep(0.2) 
            
            # 2. 🌟 "띵~" 안내음 재생 (끝날 때까지 대기하도록 백그라운드 '&' 기호 제거)
            if os.path.exists(BEEP_PATH): 
                os.system(f"mpg123 -q {BEEP_PATH}") 
            # 3. 비프음의 물리적 공간 잔향(에코)이 사라질 아주 짧은 틈(0.2초) 부여
            time.sleep(0.2)
            # 3. 🌟 [핵심] 안내음 소리와 로봇 대사의 모든 잔향이 하드웨어 버퍼에 남아있으므로
            # 안내음이 끝난 '바로 지금' 버퍼를 싹 비워줍니다.
            self.flush_mic_buffer() 
            
            print("\n" + "="*40 + "\n 🎙️ 마이크 ON : 지금 말씀해주세요 \n" + "="*40 + "\n")
            
            frames, initial_noises = [], []
            has_spoken = False
            start_time = last_voice_time = time.time()
            stream = self.mic_controller.stream
            dynamic_threshold = self.VOLUME_THRESHOLD 
            voice_contour = 0

            
            while True:
                data = stream.read(self.mic_config.chunk, exception_on_overflow=False)
                frames.append(data)
                rms = audioop.rms(data, 2)
                current_time = time.time()
                print(f"🎤 실시간 RMS: {rms:4d} | 문턱값: {dynamic_threshold:4d}", end='\r', flush=True)

                if current_time - start_time < 0.4:
                    initial_noises.append(rms)
                    continue

                elif current_time - start_time >= 0.4 and initial_noises:
                    dynamic_threshold = max(self.VOLUME_THRESHOLD, int((sum(initial_noises)/len(initial_noises)) * 1.5) + 150)
                    initial_noises.clear()
                    print(f"\n[시스템] 0.4초 소음 측정 완료. 최종 적용 문턱값: {dynamic_threshold}")
                    
                if rms > dynamic_threshold:
                    voice_contour += 1
                    if voice_contour >= 7 and not has_spoken:
                        print() # 줄바꿈 추가
                        self.get_logger().info("🗣️ 유저 발화 시작 감지!")
                        has_spoken = True
                        last_voice_time = current_time
                    elif has_spoken:
                        last_voice_time = current_time 
                else:
                    voice_contour = max(0, voice_contour - 1)

                if has_spoken and (current_time - last_voice_time > self.SILENCE_LIMIT): 
                    print()
                    break
                if not has_spoken and (current_time - start_time > self.TIMEOUT_LIMIT): 
                    print()
                    return None
                if current_time - start_time > self.MAX_RECORD_TIME: 
                    print()
                    break

            return b"".join(frames) if has_spoken else None
        
        except Exception:
            return None
        finally:
            self.is_recording = False

    def process_gpt_logic(self, user_text, user_preference, dialogue_turn, current_emotion):
        context_data = ""
        if self.collection is not None:
            try:
                search_query = user_text
                results = self.collection.query(query_texts=[search_query], n_results=5)
                if results and results['documents'] and results['documents'][0]:
                    context_data = "====== [추천 가능한 DB 지식베이스 정보 (반드시 이 안에서만 제안할 것)] ======\n"
                    for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
                        context_data += f"- 칵테일명: {meta.get('name')}\n  레시피코드: {meta.get('recipe_code')}\n  특징 및 가격: {doc}\n\n"
            except Exception:
                pass

        if not context_data:
            context_data = f"====== [기본 메뉴 정보 (반드시 이 안에서만 제안할 것)] ======\n"
            context_data += f"{chr(10).join(self.menu_db_fallback)}\n"

        # 💡 [하울링 방어] 컨텍스트 히스토리에서 직전 웨이터 대사를 추적하여 추출
        last_waiter_message = ""
        if "웨이터:" in user_preference:
            try:
                last_waiter_message = user_preference.split("웨이터:")[-1].split("\n")[0].strip()
            except Exception:
                pass

        # 원본 프롬프트 완벽 복구 + 날조 금지 절대 규칙 + 하울링 극단 제어 융합
        system_prompt = f"""
        너는 손님의 지친 마음을 치료해주는 '심리 처방 소믈리에 바텐더' 로봇이야.

        [현재 상태 정보]
        1. 대화 진행 상태: 현재 [{dialogue_turn}번째 턴] 진행 중. (최대 6턴 제한)
        2. 직전 턴까지 누적된 유저 감정 파라미터 수치: {json.dumps(current_emotion)}

        [⚠️ 핵심 비즈니스 파이프라인 및 상태 제어 규칙]
        대화는 반드시 아래 순서대로 징검다리를 건너듯 단계적으로 진행되어야 한다.

        - 1단계: 'chat' (대화 및 감정 빌드업)
          대화 시작(1~2턴) 단계이거나 유저가 사연을 풀어놓는 중일 때. 절대 메뉴를 먼저 결정하거나 가격을 고지하지 마라. 유저의 마음에 공감하며 사연을 유도하고 status는 무조건 "chat", menu와 recipe_code는 null로 보낸다.

        - 2단계: 'recommend' (메뉴 제안 및 의사 타진)
          유저의 감정이 충분히 분석되었거나 유저가 추천을 요구할 때, 지식베이스 정보를 바탕으로 "당신의 슬픔(또는 기쁨)을 달래기 위해 'ㅇㅇ 칵테일'을 처방해 드리고 싶은데 어떠신가요?"라고 제안한다. 
          이때 가격은 아직 말하지 않는다. 추천할 의도가 생겼으므로 'menu'와 'recipe_code'는 매칭되는 값으로 채우고, status는 "recommend"로 반환한다.

        - 3단계: 'confirm' (★가격 고지 및 최종 결제 동의 구하기)
          유저가 로봇의 2단계 제안('recommend')을 듣고 "좋아요", "그걸로 줘", "오케이" 등 [긍정적인 수락 의사]를 명확히 표현했을 때진입한다.
          이 단계에서 로봇은 절대로 바로 제조를 시작하면 안 된다! 반드시 지식베이스에 명시된 해당 칵테일의 [정확한 가격]을 언급하며 재확인해야 한다.
          예: "탁월한 선택이십니다. ㅇㅇ 칵테일은 12,000원입니다. 이 메뉴로 최종 주문을 확정하고 제조를 시작할까요?"
          이때 'menu'와 'recipe_code'는 유지하고, status는 반드시 "confirm"으로 반환한다.

        - 4단계: 'success' (최종 승인 및 하드웨어 연동 완료)
          유저가 3단계의 가격 고지 및 재확인 멘트를 듣고 "네", "결제해줘", "확정해주세요", "만들어줘" 등 [최종 동의 발화]를 했을 때만 진입한다.
          "감사합니다. 주문이 최종 확정되었습니다. 신속하고 맛있게 만들어 드릴게요!"라고 친절하게 마무리하며, status를 무조건 "success"로 발송하여 시퀀스를 종료한다. 이 순간에만 로봇 기계가 움직인다.

        [⚠️ 추가 예외 및 하울링 제어 규칙]
        - ★★★ 시스템 에코(하울링) 극단적 제어 규칙: 3단계(confirm)의 대사가 길기 때문에 마이크로 유저 발화에 내 직전 대사가 그대로 섞여 들어오는 경우가 많다. 유저 발화 앞부분에 내 직전 대사 내용이 반복되더라도, 절대 유저가 질문을 복창하거나 취소한 것으로 오해하지 마라. 앞부분의 중복 소음 문장은 칼같이 무시하고, 맨 뒤에 붙은 "네", "그래", "주문해줘", "확정" 등의 최종 승인 단어만 인식했다면 무조건 status를 "success"로 전환해야 한다.
        - 유저가 대화 도중 "아무거나 줘", "귀찮아", "그냥 추천해"라며 대화를 거부하거나 지친 기색을 보이면, 1~2단계를 즉시 건너뛰고 바로 3단계('confirm')로 강제 진입하여 가격을 고지하고 동의를 구해라. 절대로 가격 동의 없이 4단계('success')로 바로 넘어가면 안 된다.
        - 유저가 가격을 듣고 "비싸요", "안 마실래요" 등 거부 의사를 밝히면 다시 'chat'이나 'recommend' 단계로 돌아가 대안을 제시해라.
        - 계산된 5가지 감정 파라미터의 총합은 수학적으로 반드시 '100.0'이 되도록 정교하게 보정하여 "updated_emotion" 필드에 채워라.

        [🚫 절대 지시사항 - 엄격하게 준수할 것]
        1. 너는 반드시 하단에 제공된 [DB 지식베이스 정보] 또는 [기본 메뉴 정보] 내에 존재하는 칵테일만 추천할 수 있다.
        2. 제공된 정보에 없는 메뉴는 "준비되어 있지 않다"고 정중히 거절하고, 있는 메뉴 중 하나를 권해라.
        3. 'recipe_code' 필드에는 반드시 제공된 텍스트에 명시된 'RECIPE_XX_XX' 형태의 정확한 코드를 그대로 복사해서 넣어야 한다. 절대로 칵테일의 영어 이름이나 임의의 텍스트를 지어내어 넣지 마라.

        {context_data}

        너는 반드시 아래의 명시된 JSON 형식 구조로만 완벽히 답변해야 해. (마크다운 백틱 문자는 적지 마)
        {{
            "status": "chat" 또는 "recommend" 또는 "confirm" 또는 "success",
            "menu": "결정되거나 제안된 메뉴 이름 (없으면 null)",
            "recipe_code": "레시피 코드 (없으면 null)",
            "message": "로봇의 따뜻하고 정교한 음성 대사 (1~2문장)",
            "updated_emotion": {{
                "angry": 0.0,
                "happy": 0.0,
                "sad": 0.0,
                "surprise": 0.0,
                "neutral": 0.0
            }}
        }}
        """
        
        # 💡 [하울링 방어] 유저 입력 컨텍스트에 하울링 가이드라인을 동적으로 주입
        user_content = user_preference + f"유저: {user_text}"
        if last_waiter_message:
            user_content += f"\n\n[현재 턴 노이즈 필터링 힌트]: 현재 유저 발화 앞쪽에 직전 대사인 '{last_waiter_message}'가 에코로 섞여있다면 그 부분은 노이즈이므로 완전히 지워버리고 맨 뒤의 본심만 파악하여 상태(status)를 승인하시오."

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                response_format={ "type": "json_object" },
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}],
                max_tokens=450, temperature=0.1 
            )
            data = json.loads(response.choices[0].message.content.strip())
            return data.get("status"), data.get("menu"), data.get("recipe_code"), data.get("message"), data.get("updated_emotion")
        except Exception:
            return "chat", None, None, "오류가 발생했습니다.", current_emotion

def main():
    rclpy.init()
    node = IntegratedOrderManager()
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.mic_controller.close_stream()
        node.destroy_node()
        if rclpy.ok(): rclpy.shutdown()

if __name__ == "__main__": main()
