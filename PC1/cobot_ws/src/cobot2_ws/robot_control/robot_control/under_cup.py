import cv2
import numpy as np


def _extract_main_contour(img):
    """Return the most plausible cup contour from both binary modes."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    h, w = gray.shape[:2]
    image_area = float(h * w)
    best = None
    best_area = 0.0

    # Depending on lighting/background, cup can be foreground in either mode.
    threshold_modes = [cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU, cv2.THRESH_BINARY + cv2.THRESH_OTSU]
    for mode in threshold_modes:
        _, thresh = cv2.threshold(blurred, 0, 255, mode)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in contours:
            area = cv2.contourArea(c)
            if area < 100.0:
                continue

            x, y, cw, ch = cv2.boundingRect(c)
            touches_border = x <= 1 or y <= 1 or (x + cw) >= (w - 1) or (y + ch) >= (h - 1)
            covers_whole_image = area > image_area * 0.90

            # Reject likely background contour.
            if touches_border and covers_whole_image:
                continue

            if area > best_area:
                best = c
                best_area = area

    return best


def _band_width(contour, y_start, y_end):
    xs = [point[0][0] for point in contour if y_start <= point[0][1] <= y_end]
    if len(xs) < 2:
        return 0.0

    xs = np.array(xs, dtype=np.float32)
    # Percentile width is less sensitive to outlier pixels than min/max width.
    return float(np.percentile(xs, 95) - np.percentile(xs, 5))

def align_cup(image_path):
    """컵 이미지를 수직으로 정렬하여 반환"""
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"ROI image not found: {image_path}")

    largest_contour = _extract_main_contour(img)
    if largest_contour is None:
        raise ValueError("No valid contour found for cup alignment")

    # 2. 중심점 및 회전 각도 계산 (가로가 더 길면 90도 추가 회전하여 세움)
    (cx, cy), (w, h), angle = cv2.minAreaRect(largest_contour)
    correction_angle = angle + 90 if w > h else angle

    # 3. 아핀 변환을 통한 이미지 회전
    rotation_matrix = cv2.getRotationMatrix2D((int(cx), int(cy)), correction_angle, 1.0)
    aligned_img = cv2.warpAffine(img, rotation_matrix, (img.shape[1], img.shape[0]), 
                                 borderMode=cv2.BORDER_REPLICATE)
                                 
    return aligned_img

def check_cup_status(aligned_img):
    """수직 정렬된 컵의 상/하단 너비를 비교하여 정방향(True) 여부 반환"""
    c = _extract_main_contour(aligned_img)
    if c is None:
        raise ValueError("No valid contour found for cup status")
    
    # 2. 바운딩 박스를 통해 컵의 상위 20%, 하위 20% Y축 경계 계산
    _, y, _, h = cv2.boundingRect(c)
    top_y_start = int(y + (h * 0.10))
    top_y_end = int(y + (h * 0.30))
    bot_y_start = int(y + (h * 0.70))
    bot_y_end = int(y + (h * 0.90))

    # 3. 상/하단 밴드 폭 계산 (아웃라이어에 강건한 퍼센타일 기반)
    top_width = _band_width(c, top_y_start, top_y_end)
    bot_width = _band_width(c, bot_y_start, bot_y_end)

    # 4. 폭 차이가 너무 작으면 모호한 케이스로 보고 안전 기본값(True) 사용
    margin = max(4.0, 0.05 * max(top_width, bot_width, 1.0))
    if abs(top_width - bot_width) < margin:
        return True

    # 5. 상단이 하단보다 넓으면 정방향(True), 아니면 역방향(False) 반환
    return top_width > bot_width

# # --- 실행 예시 ---
# aligned = align_cup("cup_0.png")
# is_upright = check_cup_status(aligned)
# print("정방향" if is_upright else "역방향")