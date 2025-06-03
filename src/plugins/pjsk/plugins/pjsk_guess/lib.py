import io
import os
import random
import difflib
import requests
from typing import Tuple, List, Dict

import opencc
import PIL.Image
import ujson as json

PATH_METADATA__ = "src/plugins/pjsk/plugins/pjsk_guess/sekai_viewer_jackets.json"
with open(PATH_METADATA__, 'r', encoding='utf-8') as f:
    METADATA_: Dict[str, List[str]] = json.load(f)

class LibPjskGuess(Exception):
    INFO_BEGIN = "PJSK曲绘竞猜 (随机裁切)\n使用横杠\"-\"加答案以参加猜曲\n\n你有50秒的时间回答\n可手动发送“结束猜曲”来结束猜曲\n\nJacket guess, answer by \"-\" + song name, send \"endpjskguess\" to end"
    INFO_ON_GUESSING = "已经开始猜曲!"
    INFO_CORRECT = ":white_check_mark:您猜对了(Right answer)"
    INFO_INCORRECT = ":x:您猜错了(Wrong answer), 答案不是"
    INFO_END_TIMEOUT = "时间到, 正确答案: "
    INFO_END_USER = "正确答案: "
    INFO_NOT_ON_GUESSING = "当前没有猜曲哦"

    @staticmethod
    def get_random_jacket() -> Tuple[PIL.Image.Image, List[str]]:
        """
        随机获取一个曲目的封面
        Returns:
            jacket (PIL.Image.Image): 封面图片.
            music_name (List[str]): 封面对应曲目的名称.
        """
        PATH_JACKET_CACHE_DIR = "resources/jackets"
        URL_SEKAI_VIEWER_JACKET = "https://storage.sekai.best/sekai-jp-assets/music/jacket"

        # 从元数据中随机选择一个曲目
        music_id, music_name = random.choice(list(METADATA_.items()))

        # 检查封面是否已缓存，如果不存在则从sekaiviewer下载
        if not os.path.exists(PATH_JACKET_CACHE_DIR):
            os.makedirs(PATH_JACKET_CACHE_DIR, exist_ok=True)
        if os.path.exists(PATH_JACKET_CACHE_DIR + f"/jacket_s_{music_id}.png"):
            jacket = PIL.Image.open(
                PATH_JACKET_CACHE_DIR + f"/jacket_s_{music_id}.png")
        else:
            url = URL_SEKAI_VIEWER_JACKET + \
                f"/jacket_s_{music_id}/jacket_s_{music_id}.webp"
            src = requests.get(url, timeout=10)
            raw = io.BytesIO(src.content)
            jacket = PIL.Image.open(raw)
            jacket.save(
                f"{PATH_JACKET_CACHE_DIR}/jacket_s_{music_id}.png", format="png")

        return jacket, music_name

    @staticmethod
    def do_random_crop(jacket: PIL.Image.Image, size: int = 140) -> PIL.Image.Image:
        """
        随机裁剪封面图片为指定大小的正方形。
        Args:
            jacket (PIL.Image.Image): 原始封面图片.
            size (int): 裁剪后的正方形大小，默认为140像素.
        Returns:
            jacket_croped (PIL.Image.Image): 裁剪后的正方形封面图片.
        """
        x_rand = random.randint(0, jacket.width - size)
        y_rand = random.randint(0, jacket.height - size)
        jacket_cropped = jacket.crop(
            (x_rand, y_rand, x_rand + size, y_rand + size))
        return jacket_cropped

    @staticmethod
    def zh_tw_to_zh_cn(text: str) -> str:
        """
        将繁体中文转换为简体中文。
        Args:
            text (str): 繁体中文文本.
        Returns:
            text_converted: 简体中文文本.
        """
        text_converted = opencc.OpenCC('t2s').convert(text)
        return text_converted

    @staticmethod
    def load_music_name_data() -> Dict[str, str]:
        """
        加载曲目名称数据。
        Returns:
            data (Dict[str, str]): 曲目名称数据列表.
        """        
        data: Dict[str, str] = {}
        for music_id, music_names in METADATA_.items():
            for music_name in music_names:
                data[music_name] = music_id
        
        return data

    from typing import Optional

    @staticmethod
    def get_best_match(alias: str, data: Dict[str, str]) -> List[str]:
        """
        在数据中找到与别名最匹配的曲目id和曲目名称列表。
        Args:
            alias (str): 用户输入的别名.
            data (list): 曲目数据列表.            
        Returns:
            music_names (List[str]): 最匹配的曲目名称列表.
        """        
        music_names = list(data.keys())
        best_match = max(music_names, key=lambda x: difflib.SequenceMatcher(None, alias, x).ratio())
        music_id = data[best_match]
        music_names = METADATA_[music_id]

        return music_names
    
    @staticmethod
    def get_music_name_for_message(music_name: List[str]) -> str:
        """
        编辑曲目名称以适应显示。
        Args:
            music_name (str): 原始曲目名称.
        Returns:
            music_name_edited (str): 编辑后的曲目名称.
        """
        match len(music_name):
            case 1:
                music_name_edited = f"**{music_name[0]}**"
            case 2:
                music_name_edited = f"**{music_name[0]}({music_name[1]})**"
            case 3:
                music_name_edited = f"**{music_name[0]}({music_name[1]}/{music_name[2]})**"
        return music_name_edited


if __name__ == '__main__':
    # 谱面抽取测试
    jacket, music_name = LibPjskGuess.get_random_jacket()
    print(f"Music Name: {music_name}")
    jacket.show()
    jacket = LibPjskGuess.do_random_crop(jacket, size=140)
    jacket.show()

    # 曲名数据读取测试
    import sys
    music_name_data = LibPjskGuess.load_music_name_data()
    print(f"Loaded {len(music_name_data)} music names.")
    print(f"music_name_data size: {sys.getsizeof(music_name_data)} bytes")
    print(f"Sample data: {list(music_name_data.items())[:5]}")

    # 测试简体中文转换
    text_tw = "世劃啟動"
    text_cn = LibPjskGuess.zh_tw_to_zh_cn(text_tw)
    print(f"繁体中文: {text_tw} -> 简体中文: {text_cn}")

    # 测试最佳匹配
    data = LibPjskGuess.load_music_name_data()
    alias = "喵"
    best_match = LibPjskGuess.get_best_match(alias, data)
    print(f"Best match for '{alias}': {best_match[0]}, Names: {best_match[1]}")

    pass
