import os
import shutil
import json
import chromadb
from dotenv import load_dotenv
from ament_index_python.packages import get_package_share_directory

def main():
    PACKAGE_NAME = "cocktail_order_pkg"
    
    # ─── [수정] ROS 2 환경에 인스톨된 share/resource 폴더 경로 유연한 추적 ───
    try:
        RESOURCE_PATH = os.path.join(get_package_share_directory(PACKAGE_NAME), "resource")
    except Exception:
        # 빌드 전 소스 디렉토리 상태에서 로컬로 직접 실행할 때를 위한 안전 방어선
        CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
        RESOURCE_PATH = os.path.join(CURRENT_DIR, "resource")

    env_path = os.path.join(RESOURCE_PATH, ".env")
    db_path = os.path.join(RESOURCE_PATH, "cocktail_vector_db")

    # ─── [수정] .env 파일 절대 경로 로드 안전 장치 ───────────────────────
    if os.path.exists(env_path):
        load_dotenv(dotenv_path=env_path)
    else:
        print(f"⚠️  [경고] .env 파일을 찾을 수 없습니다. 경로를 확인하세요: {env_path}")

    # 기존 구형 데이터베이스 삭제 (멱등성 확보)
    if os.path.exists(db_path):
        shutil.rmtree(db_path)
        print(f"🧹 기존 구형 데이터베이스 백업 삭제 완료. ({db_path})")

    # 벡터 DB PersistentClient 설정
    client = chromadb.PersistentClient(path=db_path)
    collection = client.get_or_create_collection(name="cocktails")

    # 원본 칵테일 가이드 데이터셋
    cocktail_data = [
        {
            "id": "RECIPE_BR_01",
            "document": "칵테일명: 블랙 러시안. 특징: 은은한 커피 향이 감돌고 달콤 쌉싸름하지만 도수가 강하고 묵직함. 추천 대상 파라미터 수치: sad, angry. 상황: 마음이 깊게 슬프거나 직장인 업무 과다로 매우 지쳤을 때 독하게 위로가 되는 처방.",
            "metadata": {"recipe_code": "RECIPE_BR_01", "name": "블랙 러시안", "price": "8,000원", "mood_tag": "sad, angry"}
        },
        {
            "id": "RECIPE_MH_01",
            "document": "칵테일명: 모히또. 특징: 생라임과 애플민트 잎사귀가 빻아져 들어가 극도로 상큼하고 청량함. 청량 탄산 베이스에 도수가 대단히 낮아 가벼움. 추천 대상 파라미터 수치: happy, surprise. 상황: 즐거운 성과가 있거나 유쾌한 기분 전환, 상쾌한 도파민 충전이 필요할 때 최적.",
            "metadata": {"recipe_code": "RECIPE_MH_01", "name": "모히또", "price": "7,500원", "mood_tag": "happy, surprise"}
        },
        {
            "id": "RECIPE_KM_01",
            "document": "칵테일명: 깔루아 밀크. 특징: 부드럽고 따뜻한 뉘앙스의 우유 층과 커피 리큐르의 달콤한 초콜릿 풍미가 융합됨. 디저트 제과 느낌의 낮은 타격감. 추천 대상 파라미터 수치: neutral, happy. 상황: 고단한 하루 끝에 달콤한 당 충전이 급격히 요구되거나 마음의 평온함, 안락한 휴식을 바랄 때.",
            "metadata": {"recipe_code": "RECIPE_KM_01", "name": "깔루아 밀크", "price": "7,000원", "mood_tag": "neutral, happy"}
        }
    ]

    # 임베딩 데이터 주입 로프
    for data in cocktail_data:
        collection.add(
            documents=[data["document"]],
            metadatas=[data["metadata"]],
            ids=[data["id"]]
        )

    print(f"✅ 대화 추적 시스템 최적화용 로컬 Vector DB 구축 성공!")
    print(f"📌 저장 위치: {db_path}")

if __name__ == "__main__":
    main()