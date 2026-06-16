from openai import OpenAI
import sounddevice as sd
import scipy.io.wavfile as wav
import tempfile
import io # 👈 메모리 상의 바이너리를 파일 객체로 변환하기 위해 추가
import numpy as np

class STT:
    def __init__(self, openai_api_key):
        self.client = OpenAI(api_key=openai_api_key)
        self.duration = 5  # seconds
        self.samplerate = 16000  # Whisper는 16kHz를 선호

    def speech2text_from_bytes(self, audio_bytes, mic_config):
        """
        [새로 추가된 함수]
        audio_manager.py에서 실시간 침묵 감지로 모아온 오디오 바이너리 데이터를 
        디스크에 파일로 저장하지 않고 메모리 상에서 바로 Whisper API로 전송합니다.
        """
        try:
            # 1. 오디오 매니저의 샘플 레이트(예: 48000Hz) 정보 가져오기
            rate = mic_config.rate if hasattr(mic_config, 'rate') else 48000
            
            # 2. PyAudio에서 들어온 바이트 데이터를 numpy array(int16)로 변환
            audio_data = np.frombuffer(audio_bytes, dtype=np.int16)
            
            # 3. 파일 저장 없이 메모리 안에서 WAV 포맷 데이터 구조 빌드 (BytesIO 활용)
            wav_io = io.BytesIO()
            wav.write(wav_io, rate, audio_data)
            wav_io.seek(0) # 데이터의 처음 위치로 커서 이동
            
            # OpenAI API가 파일명 확장자를 통해 포맷을 인지할 수 있도록 가상 이름 부여
            wav_io.name = "input_audio.wav"

            # 4. Whisper API 호출
            # language="ko"를 지정하면 침묵/잡음 시 뜬금없는 영어 환각 문장이 튀어나오는 것을 방지하는 데 큰 도움이 됩니다.
            transcript = self.client.audio.transcriptions.create(
                model="whisper-1", 
                file=wav_io,
                language="ko" 
            )

            print("STT 결과: ", transcript.text)
            return transcript.text

        except Exception as e:
            print(f"❌ Whisper API 통신 에러: {e}")
            return ""

    def speech2text(self):
        """[기존 함수 - 백업용] 5초 고정 녹음 방식"""
        # 녹음 설정
        print("음성 녹음을 시작합니다. \n 5초 동안 말해주세요...")
        audio = sd.rec(int(self.duration * self.samplerate), samplerate=self.samplerate, channels=1, dtype='int16')
        sd.wait()
        print("녹음 완료. Whisper에 전송 중...")

        # 임시 WAV 파일 저장
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
            wav.write(temp_wav.name, self.samplerate, audio)

            # Whisper API 호출
            with open(temp_wav.name, "rb") as f:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1", file=f, language="ko")

        print("STT 결과: ", transcript.text)
        return transcript.text