from io import BytesIO

import cv2
import qrcode
import numpy as np
from PIL import Image

class QRCodeAbu:
    BOX_SIZE = 10
    BORDER = 0
    IMAGE_PATH = 'src/plugins/qrcode/abu.png'

    @staticmethod
    def excute(data):
        qr_array = QRCodeAbu.generate_qr_code(data)
        result = QRCodeAbu.replace_qr_with_image(qr_array)
        result = QRCodeAbu.rgb_to_rgba(result)
        result_pil = Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGRA2RGBA))
        output_buffer = BytesIO()
        result_pil.save(output_buffer, format='PNG')
        output_buffer.seek(0)
        return output_buffer.getvalue()

    # 生成二维码
    @classmethod
    def generate_qr_code(cls, data):
        qr = qrcode.QRCode(
            error_correction=qrcode.ERROR_CORRECT_H,
            box_size=cls.BOX_SIZE,
            border=cls.BORDER
        )
        qr.add_data(data)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color='black', back_color='white')
        qr_img = qr_img.get_image().convert('L')
        return np.array(qr_img)

    # 替换单位色块
    @classmethod
    def replace_qr_with_image(cls, qr_array):
        # 读取并缩放素材图片
        img = cv2.imread(cls.IMAGE_PATH)
        img_resized = cv2.resize(img, (cls.BOX_SIZE, cls.BOX_SIZE))  # 缩放为单位色块大小
        
        # 创建新图像以放置替换后的内容
        qr_height, qr_width = qr_array.shape
        new_img = np.ones((qr_height, qr_width, 3), dtype=np.uint8) * 255

        for x in range(cls.BOX_SIZE * cls.BORDER, qr_height - cls.BOX_SIZE * cls.BORDER, cls.BOX_SIZE):
            for y in range(cls.BOX_SIZE * cls.BORDER, qr_height - cls.BOX_SIZE * cls.BORDER, cls.BOX_SIZE):
                if qr_array[x, y] == 0:
                    new_img[x: x + cls.BOX_SIZE, y: y + cls.BOX_SIZE] = img_resized

        return new_img

    # 转换为 RGBA
    @staticmethod
    def rgb_to_rgba(image):
        alpha_channel = np.ones(image.shape[:2], dtype=image.dtype) * 255
        white = [255, 255, 255]
        white_mask = np.all(image == white, axis=-1)
        alpha_channel[white_mask] = 0
        rgba_image = cv2.merge([image, alpha_channel])

        return rgba_image


if __name__ == '__main__':
    data = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    output = QRCodeAbu.excute(data)
    with open('src/plugins/qrcode/output.png', 'wb') as f:
        f.write(output)
    