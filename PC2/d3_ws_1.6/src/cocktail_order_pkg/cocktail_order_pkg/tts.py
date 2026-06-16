from openai import OpenAI
import os # 추가: 시스템 명령어를 실행하기 위함
import shutil
import subprocess

class TTS:
    def __init__(self, openai_api_key):
        self.client = OpenAI(api_key=openai_api_key)
        self.player_cmd = shutil.which("mpg123")
        self._player_warned = False

    def text2speech(self, text):
        print(f"TTS 합성 시작: {text}")
        
        # OpenAI로부터 음성 파일 가져오기
        response = self.client.audio.speech.create(
            model="tts-1",
            voice="nova",
            input=text
        )

        # 임시 MP3 파일로 저장
        temp_file = "temp_tts.mp3"
        with open(temp_file, "wb") as f:
            f.write(response.content)

        print("음성 출력 중...")
        # mpg123이 있을 때만 재생하고, 없으면 경고 1회만 출력합니다.
        if self.player_cmd:
            try:
                subprocess.run([self.player_cmd, "-q", temp_file], check=False)
            except Exception as e:
                print(f"TTS 재생 실패: {e}")
        elif not self._player_warned:
            print("TTS 재생기를 찾지 못했습니다. 'sudo apt install mpg123' 후 음성 재생이 가능합니다.")
            self._player_warned = True
        
        print("음성 출력 완료.")
        
        # 재생이 끝난 후 임시 파일 삭제
        if os.path.exists(temp_file):
            os.remove(temp_file)