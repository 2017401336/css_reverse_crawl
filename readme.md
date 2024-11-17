# CSS 反爬简介和解决方法

## 1. 常见的字体文件
> 简介：为了解决解决各平台字体表现不统一的问题，引入了字体文件。常见的字体文件TTF、OTF、WOFF、WOFF2。（详情链接：https://zhuanlan.zhihu.com/p/463273013），以下为摘要
- TTF
    - TrueType Font:由美国苹果公司和微软公司共同开发的一种电脑轮廓字体（曲线描边字）类型标准。
    - 特征：这种类型字体文件的扩展名是 .ttf，类型代码是 tfil。
- OTF
    - OpenType: 是 Adobe 和 Microsoft 联合开发的跨平台字体文件格式，也叫 Type 2 字体，它的字体格式采用 Unicode 编码，是一种兼容各种语言的字体格式。
    - 特征：文件后缀 .ttf、.OTF、.TTC
- WOFF
    - Web 开放字体格式是一种网页所采用的字体格式标准。此字体格式发展于 2009 年，现在正由万维网联盟的 Web 字体工作小组标准化，以求成为推荐标准。
    - 特征：文件后缀 .woff
- WOFF2
    - WOFF 2 标准在 WOFF1 的基础上，进一步优化了体积压缩，带宽需求更少，同时可以在移动设备上快速解压。
    - 特征：文件后缀 .woff2

# 2. woff文件构造映射示例
> 使用字体文件简述：
>
> 1. HTML使用加密后的字符编码（即html源码中的乱码）
> 2. 在html中 style 下声明了 @font-face，并在其中给出了字体文件的路径。
> 3. 浏览器解析时会根据字体文件当中的映射关系，去将html中的乱码一一翻译成可识别内容。
> 
> 爬虫需要怎么做？
>
> 爬虫爬取到的html源码是加密后的字符编码，咱们需要将字体文件下载到本地，通过有效手段（ocr或者人工标注）提取映射关系，然后根据映射关系还原内容。
>
> 以该网站示例：aHR0cHM6Ly9mYW5xaWVub3ZlbC5jb20vcmVhZGVyLzcxNzMyMTYwODkxMjI0Mzk3MTE=

### 1. 请求并提取正文内容
``` python
# spider.py
import json
import requests
import base64
from lxml import etree

headers = {
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
}


# url = base64.base64encode("aHR0cHM6Ly9mYW5xaWVub3ZlbC5jb20vcmVhZGVyLzcxNzMyMTYwODkxMjI0Mzk3MTE=")
url = base64.urlsafe_b64decode("aHR0cHM6Ly9mYW5xaWVub3ZlbC5jb20vcmVhZGVyLzcxNzMyMTYwODkxMjI0Mzk3MTE=").decode('utf-8')

def transform(content_string):
    with open("./word.json", 'r', encoding='utf-8') as f:
        map = json.load(f)
        
    # 将键变为Unicode
    glyph_map = {code.split('_')[0]: value for code, value in map.items()}

    new_content = ''.join(
        glyph_map.get(str(ord(char)), char)  # 如果映射存在则转换，否则保留原字符
        for char in content_string
    )
    return new_content
        
    
if __name__ == '__main__':
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        html = etree.HTML(response.text)
        content = html.xpath('//div[@class="muye-reader-content noselect"]//text()')
        content_string = '\n'.join(content)
        for char in content_string:
            print(f"{ord(char)} --> {char}")
        # print(transform(content_string))
    else:
        print(f"Request failed with status code: {response.status_code}")
```
上面的代码运行后，会发现将单个字符转换为其对应的 Unicode 码后，5开头的基本上对应的就是乱码，所以这部分是从字体文件中进行的映射。查看该请求该网址时，发送的font请求，将所有的font请求下载，使用 FontCreator进行查看，找到对应的woff文件提取其中的映射。
<hr>
<hr>
下面的python代码所做的事情：

1. 通过fontTools库读取woff文件，并对其中的图片进行了自适应保存
2. 使用ddddocr和pytesseract对图片进行了识别，保存为字典，其中的内容： key: unicode码_字形名字 value: ocr识别后的字符串
3. 对比两种ocr的内容，会将同一张图片识别到的不同内容进行保存，存储为json文件。（注：概率极小的情况。此处还有可能两个ocr对同一张图片都识别错误，但错误一致。如图片：3， ddddocr和pytesseract都识别为5。那么后续映射就会存在问题。）
4. 修改：打开3中保存好的json文件，和打开的图形界面中的图片进行比对。最终结果以人工识别为准（图片为3， 但是ddddocr识别为 4， pytesseract识别为5，那么json文件中的值修改为3）。修改完一个值后，需要通过回车键展示下一个问题图片。直到所有的全部修改完成

``` python
# ocr_map.py
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
            self.file_path = "./dc027189e0ba4cd-500.woff2"
        
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
    ocr_map.font_split_single_img()
    ocr_map.compare(ocr_map.ocr_word(), ocr_map.ocr_tesseract())
    ocr_map.repeat()
```

运行如下代码，查看引入字体文本映射后的正文内容。
``` python
# 取消 spider.py中的37行的注释即可

```






