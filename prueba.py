import cv2
import easyocr

reader = easyocr.Reader(["es","en"], gpu=False)
image = cv2.imread("imagenes/placa1.jpg")
# image = cv2.imread("imagenes/placa2.jpeg")
# image = cv2.imread("imagenes/placa4.jpg")
# image = cv2.imread("imagenes/placa5.jpeg")

allowed_chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-'
result = reader.readtext(image, paragraph=False, allowlist=allowed_chars)

for res in result:
     print("res:", res)
     pt0 = res[0][0]
     pt1 = res[0][1]
     pt2 = res[0][2]
     pt3 = res[0][3]
     cv2.rectangle(image, pt0, (pt1[0], pt1[1] - 23), (166, 56, 242), -1)
     cv2.putText(image, res[1], (pt0[0], pt0[1] -3), 2, 0.8, (255, 255, 255), 1)
     cv2.rectangle(image, pt0, pt2, (166, 56, 242), 2)
     cv2.circle(image, pt0, 2, (255, 0, 0), 2)
     cv2.circle(image, pt1, 2, (0, 255, 0), 2)
     cv2.circle(image, pt2, 2, (0, 0, 255), 2)
     cv2.circle(image, pt3, 2, (0, 255, 255), 2)
     cv2.imshow("Image", image)
     cv2.waitKey(0)

cv2.destroyAllWindows()