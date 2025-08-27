import cv2
import numpy as np
from pypylon import pylon

camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
camera.Open()

new_width = camera.Width.Value - camera.Width.Inc
if new_width >= camera.Width.Min:
    camera.Width.Value = new_width

camera.PixelFormat.Value = "BayerBG8"
camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

try:
    while camera.IsGrabbing():
        grabResult = camera.RetrieveResult(
            5000, pylon.TimeoutHandling_ThrowException)
        if grabResult.GrabSucceeded():
            img = grabResult.Array
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BayerBG2RGB)
            hsv_image = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2HSV)

            upper_red1 = np.array([10, 255, 255])
            lower_red1 = np.array([0, 100, 100])
            lower_red2 = np.array([160, 100, 100])
            upper_red2 = np.array([179, 255, 255])

            mask1 = cv2.inRange(hsv_image, lower_red1, upper_red1)
            mask2 = cv2.inRange(hsv_image, lower_red2, upper_red2)

            red_mask = cv2.bitwise_or(mask1, mask2)

            filtered_image = cv2.bitwise_and(img_rgb, img_rgb, mask=red_mask)

            contours, _ = cv2.findContours(
                red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for contour in contours:

                if cv2.contourArea(contour) > 500:

                    M = cv2.moments(contour)
                    if M["m00"] != 0:
                        cX = int(M["m10"] / M["m00"])
                        cY = int(M["m01"] / M["m00"])

                        cv2.drawContours(
                            img_rgb, [contour], -1, (0, 255, 0), 2)
                        cv2.circle(img_rgb, (cX, cY), 5, (0, 0, 255), -1)
                        cv2.putText(img_rgb, f"Centroid: ({cX}, {cY})", (cX - 50, cY - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

            cv2.imshow('Original Image', img_rgb)
            cv2.imshow('Red Mask', red_mask)
            cv2.imshow('Filtered Red Color', filtered_image)

            if cv2.waitKey(1) & 0xFF == ord('s'):
                break

        grabResult.Release()
finally:
    camera.StopGrabbing()
    camera.Close()
    cv2.destroyAllWindows()
