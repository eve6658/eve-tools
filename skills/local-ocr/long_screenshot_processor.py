import os
import cv2
from paddleocr import PaddleOCR
from PIL import Image

# 1. 初始化 OCR (针对新版本)
ocr = PaddleOCR(use_textline_orientation=True, lang='ch', device='cpu')

def process_long_image(image_path, slice_height=1000, overlap=100):
    """
    将长截图切片识别，并合并结果
    :param slice_height: 每段切片的高度
    :param overlap: 重叠高度，防止一行数据被切断
    """
    img = Image.open(image_path)
    width, height = img.size
    results = []

    start_y = 0
    while start_y < height:
        # 计算切片区域
        end_y = min(start_y + slice_height, height)
        box = (0, start_y, width, end_y)
        slice_img = img.crop(box)
        
        # 临时保存切片（或直接转为数组）
        temp_path = "temp_slice.jpg"
        slice_img.save(temp_path)
        
        # OCR 识别
        slice_res = ocr.ocr(temp_path, cls=True)
        
        if slice_res[0]:
            for line in slice_res[0]:
                # 过滤掉重叠区域可能重复识别的行（后续需根据时间戳去重）
                text = line[1][0]
                confidence = line[1][1]
                results.append(text)
        
        start_y += (slice_height - overlap)
        
    return results

# 测试调用
# data = process_long_image("your_stock_screenshot.jpg")
# print(data)
