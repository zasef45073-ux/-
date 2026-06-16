from firebase.client import get_db
from firebase.config import PATH_FACE_RESULTS, PATH_ORDERS


# ── 얼굴 분석 결과 ─────────────────────────────────────────────────────────────

def write_face_result(data: list) -> str:
    """얼굴 분석 결과를 저장하고 생성된 Firebase 키를 반환합니다."""
    ref = get_db().reference(PATH_FACE_RESULTS)
    pushed = ref.push(data)
    return pushed.key


def read_face_results() -> dict:
    """저장된 얼굴 분석 결과 전체를 반환합니다."""
    return get_db().reference(PATH_FACE_RESULTS).get() or {}


def get_latest_face_result() -> dict | None:
    """가장 최근 저장된 얼굴 분석 결과 1건을 반환합니다.

    Firebase Realtime DB는 push() 키가 시간순 정렬되므로
    limitToLast(1) 쿼리로 최신 항목 1개를 O(1)로 가져옵니다.
    결과가 없으면 None을 반환합니다.
    """
    ref = get_db().reference(PATH_FACE_RESULTS)
    result = ref.order_by_key().limit_to_last(1).get()
    if not result:
        return None
    # result = { "<face_key>": [...] } 형태
    face_key, data = next(iter(result.items()))
    return {"face_key": face_key, "data": data}


# ── 주문 (칵테일 추천 결과) ────────────────────────────────────────────────────

def write_order(order: dict) -> str:
    """칵테일 주문을 저장하고 생성된 Firebase 키를 반환합니다."""
    ref = get_db().reference(PATH_ORDERS)
    pushed = ref.push(order)
    return pushed.key


def read_orders() -> dict:
    """저장된 주문 내역 전체를 반환합니다."""
    return get_db().reference(PATH_ORDERS).get() or {}


def update_robot_status(order_key: str, status: str) -> None:
    """특정 주문의 로봇 서빙 상태를 업데이트합니다."""
    get_db().reference(f"{PATH_ORDERS}/{order_key}/robot_status").set(status)
