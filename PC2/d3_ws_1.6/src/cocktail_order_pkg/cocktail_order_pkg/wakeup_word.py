import os
import numpy as np
from openwakeword.model import Model
from scipy.signal import resample
from ament_index_python.packages import get_package_share_directory

PACKAGE_NAME = "cocktail_order_pkg"
try:
    RESOURCE_PATH = os.path.join(get_package_share_directory(PACKAGE_NAME), "resource")
except Exception:
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    RESOURCE_PATH = os.path.join(CURRENT_DIR, "resource")

MODEL_NAME = "hello_rokey_8332_32.tflite"
MODEL_PATH = os.path.join(RESOURCE_PATH, MODEL_NAME)

class WakeupWord:
    def __init__(self, buffer_size):
        self.model = None
        self.model_name = MODEL_NAME.split(".", maxsplit=1)[0]
        self.stream = None
        self.buffer_size = buffer_size

    def is_wakeup(self):
        audio_chunk = np.frombuffer(
            self.stream.read(self.buffer_size, exception_on_overflow=False),
            dtype=np.int16,
        )
        audio_chunk = resample(audio_chunk, int(len(audio_chunk) * 16000 / 48000))
        outputs = self.model.predict(audio_chunk, threshold=0.1)
        confidence = outputs[self.model_name]
        
        if confidence > 0.3:
            print("Wakeword detected!")
            return True
        return False

    def set_stream(self, stream):
        # 모델 로딩 전 디버깅 로그
        print(f"DEBUG: Loading wakeword model from: {MODEL_PATH}")
        if not os.path.exists(MODEL_PATH):
            print(f"ERROR: Model file not found at {MODEL_PATH}")
        
        self.model = Model(wakeword_models=[MODEL_PATH])
        self.stream = stream