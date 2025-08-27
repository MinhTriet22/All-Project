import cv2
import numpy as np

DIGITS_LOOKUP = {
    (1, 1, 1, 0, 1, 1, 1): 0,
    (0, 0, 1, 0, 0, 1, 0): 1,
    (1, 0, 1, 1, 1, 0, 1): 2,
    (1, 0, 1, 1, 0, 1, 1): 3,
    (0, 1, 1, 1, 0, 1, 0): 4,
    (1, 1, 0, 1, 0, 1, 1): 5,
    (1, 1, 0, 1, 1, 1, 1): 6,
    (1, 0, 1, 0, 0, 1, 0): 7,
    (1, 1, 1, 1, 1, 1, 1): 8,
    (1, 1, 1, 1, 0, 1, 1): 9
}

img = cv2.imread(
    '/home/le_minh_triet/Documents/Python/Img_test/d54cc0a5f575262b7f643.jpg')
img = cv2.resize(img, (600, 800))
output_final = img.copy()
# Xy ly anh tong the : doi sang mau xam, lam mo, lay duong bien
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
blurred = cv2.GaussianBlur(gray, (5, 5), 0)
edged = cv2.Canny(blurred, 50, 150)
# cv2.imshow("Anh sau khi xu ly tong the", edged)
contours, _ = cv2.findContours(
    edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
screen_contour = None
# Loc tim contours LCD
if len(contours) > 0:
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]
    for c in contours:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4:
            screen_contour = approx
            break
# Lay toa do va kich thuoc cua vung LCD
(x, y, w, h) = cv2.boundingRect(screen_contour)
# thay doi kich thuoc de crop LCD
left_trim = int(w * 0.1)
right_trim = int(w * 0.1)
top_trim = int(h * 0.30)
bottom_trim = int(h * 0.10)
# Tinh toan lat toa do va kich thuoc moi cua vung crop
x_new = x + left_trim
y_new = y + top_trim
w_new = w - left_trim - right_trim
h_new = h - top_trim - bottom_trim

lcd_crop_gray = gray[y_new:y_new+h_new, x_new:x_new+w_new]
lcd_crop_color = img[y_new:y_new+h_new, x_new:x_new+w_new]
# Bat dau xu ly anh tren LCD
thresh = cv2.adaptiveThreshold(lcd_crop_gray, 255,
                               cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                               cv2.THRESH_BINARY_INV, 41, 5)

kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
digit_contours, _ = cv2.findContours(
    closed.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

# Chỉ giữ lại contour diện tích lớn hơn 2% LCD
lcd_h, lcd_w = lcd_crop_gray.shape
min_area = 0.02 * lcd_h * lcd_w
digitCnts = []
for contour in digit_contours:
    area = cv2.contourArea(contour)
    if area < min_area:
        continue
    digitCnts.append(contour)

# Sắp xếp contour số từ trái qua phải


def x_sort_key(c):
    x, y, w, h = cv2.boundingRect(c)
    return x


digitCnts = sorted(digitCnts, key=x_sort_key)
# Nhận diện từng số LED 7 đoạn
digits = []
for c in digitCnts:
    (x, y, w, h) = cv2.boundingRect(c)
    roi = closed[y:y + h, x:x + w]

    (roiH, roiW) = roi.shape
    (dW, dH) = (int(roiW * 0.25), int(roiH * 0.15))
    dHC = int(roiH * 0.05)
# Tạo các segment của LED 7 đoạn
    segments = [
        ((0, 0), (w, dH)),                        # top
        ((0, 0), (dW, h // 2)),                   # top-left
        ((w - dW, 0), (w, h // 2)),               # top-right
        ((0, (h // 2) - dHC), (w, (h // 2) + dHC)),  # center
        ((0, h // 2), (dW, h)),                   # bottom-left
        ((w - dW, h // 2), (w, h)),               # bottom-right
        ((0, h - dH), (w, h))                     # bottom
    ]
    on = [0] * len(segments)
    for (i, ((xA, yA), (xB, yB))) in enumerate(segments):
        segROI = roi[yA:yB, xA:xB]
        area_seg = (xB - xA) * (yB - yA)
        if area_seg == 0:
            continue
        total = cv2.countNonZero(segROI)
        if total / float(area_seg) > 0.3:
            on[i] = 1
    digit = DIGITS_LOOKUP.get(tuple(on), '?')
    digits.append(str(digit))
    print("Segment pattern:", tuple(on))

    # Hien thi so tren LCD
    cv2.rectangle(lcd_crop_color, (x, y), (x + w, y + h), (0, 255, 0), 2)
    cv2.putText(lcd_crop_color, str(digit), (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)

print("Dãy số nhận diện được:", "".join(digits))

cv2.imshow("Anh sau khi xu li ", closed)
cv2.imshow("Ket qua cuoi cung", lcd_crop_color)
cv2.waitKey(0)
cv2.destroyAllWindows()
