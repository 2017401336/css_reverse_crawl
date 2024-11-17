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
        # for char in content_string:
        #     print(f"{ord(char)} --> {char}")
        #     print()
        print(transform(content_string))
    else:
        print(f"Request failed with status code: {response.status_code}")
