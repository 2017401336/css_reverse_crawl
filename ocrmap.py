import json
import os
from pathlib import Path
import time
import datetime
import tkinter as tk

from fontTools.ttLib import TTFont
from PIL import (
    Image, 
    ImageDraw, 
    ImageFont, 
    ImageTk
)

import ddddocr
import pytesseract

# 修改为自己Tesseract-OCR的安装路径
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

class OCRMap(object):
    def __init__(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.json_file_path = os.path.join(self.current_dir, 'word.json')

    def font_split_single_img(self, file_path=''):
        """
        拆分 woff2 文件, 保存为单个字体图片, 保存至 imgs 文件夹
        """
        if file_path:
            self.file_path = "fanqie/dc027189e0ba4cd-500.woff2"
        
        # 1. 打开 woff2 文件
        font = TTFont(self.filepath)
        
        # 2. 获取 cmap 表（Unicode 编码和 glyph 名称的映射）
        cmap = font.getBestCmap()
        
        # 3. 转换 woff2 为 TTF 文件（Pillow 不支持直接渲染 woff2，需要转换为 TTF 格式）
        ttf_path = "fanqie/temp_font.ttf"
        xml_path = "fanqie/temp_font.xml"
        font.save(ttf_path)
        font.saveXML(xml_path)
        
        # 4. 创建保存目录
        os.makedirs('imgs', exist_ok=True)

        # 5. 使用 Pillow 加载字体并渲染
        pil_font = ImageFont.truetype(ttf_path, size=64)  # 默认字体大小
        
        for index, (char_code, glyph_name) in enumerate(cmap.items(), start=1):
            char = chr(char_code)  # 获取字符

            # 测量字符边界
            img_dummy = Image.new("RGB", (1, 1), "white")  # 创建临时图片
            draw_dummy = ImageDraw.Draw(img_dummy)
            bbox = draw_dummy.textbbox((0, 0), char, font=pil_font)  # 获取边界
            
            # 根据边界调整画布大小
            width, height = bbox[2] - bbox[0], bbox[3] - bbox[1]
            img = Image.new("RGB", (width + 10, height + 10), "white")  # 增加边距
            draw = ImageDraw.Draw(img)

            # 绘制字符
            draw.text((5 - bbox[0], 5 - bbox[1]), char, font=pil_font, fill="black")
            
            # 保存图像
            img.save(f'./imgs/{char_code}_{glyph_name}.png')
            print(f"{index}/{len(cmap)}: Saved {char} as ./imgs/{char_code}_{glyph_name}.png")

    def ocr_word(self,):
        """
        使用ddddocr对拆分出来的图片进行识别
        """
        # 1.初始化ocr
        ocr = ddddocr.DdddOcr(beta=False, show_ad=False)
        
        start_time =  time.time()
        print("使用ddddocr开始识别...")

        # 2. 读取所有字体图片
        word_map = {}
        for parent, dirnames, filenames in os.walk('imgs'):
            for filename in filenames:
                k = filename.split(".")[0]
                currentPath = os.path.join(parent, filename)
                # 图片二进制传入ocr识别
                with open(currentPath, 'rb') as f:
                    image = f.read()
                    
                res = ocr.classification(image)
                res = res[0] if len(res) > 0 else '未找到'
                print(k, 'res:', res)

                # 存储数据
                word_map[k] = res
            
        end_time =  time.time()
        # OCR 识别所用时间: 0:00:01.465428
        print(f"OCR 识别所用时间: {datetime.timedelta(seconds=end_time - start_time)}")
        return word_map    
              
    def ocr_tesseract(self):
        """使用tesseract对图片进行识别

        Returns:
            _type_: _description_
        """
        word_map = {}
        print(pytesseract.pytesseract.tesseract_cmd)
        start_time = time.time()
        print("使用tesseract开始识别...")
        for parent, dirnames, filenames in os.walk('imgs'):
            for filename in filenames:
                k = filename.split(".")[0]
                currentPath = os.path.join(parent, filename)         
                image = Image.open(currentPath)   
                
                image = Image.open(currentPath)
                image = image.resize((image.width * 3, image.height * 3), Image.Resampling.LANCZOS)  # 放大三倍
                image.save("temp.png", dpi=(300, 300))  # 保存为高 DPI 图像
                res = pytesseract.image_to_string(image, lang='chi_sim', config="--psm 8")
                res = res.replace("\n", "")
                print(res)

                # 存储数据
                word_map[k] = res
        end_time =  time.time()
        # OCR 识别所用时间: 0:01:42.225910
        print(f"OCR 识别所用时间: {datetime.timedelta(seconds=end_time - start_time)}")
        return word_map

    def compare(self, word_map1, word_map2):
        """
        ddddocr识别后的结果集和tesseract识别后的结果集进行对比,
        将结果保存到当前目录下的 word.json 文件中，进行人为矫正

        Args:
            word_map1 (_type_): ddddocr识别后的结果集
            word_map2 (_type_): tesseract识别后的结果集
        """
        for k, v1 in word_map1.items():
            v2 = word_map2.get(k)
            if v1!= v2:
                print(f"{k} 文本不一致: {v1}!= {v2}")
                word_map1[k] = [v1, v2]

        with open(self.json_file_path, 'w', encoding='utf-8') as f:
            json.dump(word_map1, f, ensure_ascii=False, indent=4)

        print("文本对比结束")

    def repeat(self, scale_factor=3):
        """
        人为修改映射字典.
        注：这里使用tkinter去显示图片，而不使用 image.show()，是为了减少每次
            需要手动关闭打开的绘图，提高效率。
        """
        root = tk.Tk()
        root.title("Image Viewer")
        root.geometry("800x600")  # 设置窗口宽800，高600

        label = tk.Label(root)
        label.pack()
        
        with open(self.json_file_path, 'r', encoding='utf-8') as f:
            ocr_map = json.load(f)
        for key, value in ocr_map.items():
            if isinstance(value, list):
                currentPath = os.path.join(os.getcwd(), "imgs/" + key + '.png')
                img = Image.open(currentPath)
                # 放大图片便于查看
                new_size = (img.width * scale_factor, img.height * scale_factor)
                img = img.resize(new_size, Image.Resampling.LANCZOS)
                img_tk = ImageTk.PhotoImage(img)
                label.config(image=img_tk)  # 更新显示内容
                root.update()  # 刷新窗口
                input(f"查看图片: {currentPath}. 关闭后按 Enter 显示下一张...")
        
        root.destroy()  # 关闭窗口



if __name__ == "__main__":
    ocr_map = OCRMap()
    # ocr_map.font_split_single_img()
    # ocr_map.compare(ocr_map.ocr_word(), ocr_map.ocr_tesseract())
    ocr_map.repeat()