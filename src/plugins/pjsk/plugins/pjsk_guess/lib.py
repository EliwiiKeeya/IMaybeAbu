import io
import os
import random
import difflib
import requests
import unicodedata
from typing import Tuple, List, Dict, Optional, Any

import opencc
import pymongo
import PIL.Image
import ujson as json

# 读取元数据
PATH_METADATA_ = "src/plugins/pjsk/plugins/pjsk_guess/sekai_viewer_jackets.json"
with open(PATH_METADATA_, 'r', encoding='utf-8') as f:
    METADATA_: Dict[str, List[str]] = json.load(f)

# MongoDB 数据库配置 (可选, 猜曲排行依赖)
MONGO_DB_URI_ = ""
MONGO_DB_CLIENT_: Optional[pymongo.AsyncMongoClient] = None
if MONGO_DB_URI_:
    try:
        MONGO_DB_CLIENT_ = pymongo.AsyncMongoClient(MONGO_DB_URI_)
    except:
        pass


class LibPJSKGuess(Exception):
    # 信息常量
    INFO_BEGIN = "PJSK曲绘竞猜 (随机裁切)\n使用横杠\"-\"加答案以参加猜曲\n\n你有60秒的时间回答\n可手动发送“结束猜曲”来结束猜曲\n\nJacket guess, answer by \"-\" + song name, send \"endpjskguess\" to end"
    INFO_ON_GUESSING = "已经开始猜曲!"
    INFO_CORRECT = ":white_check_mark:您猜对了(Right answer)\n"
    INFO_INCORRECT = ":x:您猜错了(Wrong answer), 答案不是"
    INFO_END_TIMEOUT = "时间到, 正确答案: "
    INFO_END_USER = "正确答案: "
    INFO_NOT_ON_GUESSING = "当前没有猜曲哦"

    # 状态位常量
    IS_MONGO_DB_ENABLED = True if MONGO_DB_CLIENT_ else False

    @staticmethod
    def convert_text(text: str) -> str:
        """
        将繁体中文文本转换为简体中文文本, 将大写字母转换为小写.
        Args:
            text (str): 文本.
        Returns:
            text_converted: 转换后文本.
        """
        text_converted = opencc.OpenCC('t2s').convert(text)
        text_converted = text_converted.lower()
        return text_converted

    @staticmethod
    def get_random_jacket() -> Tuple[PIL.Image.Image, List[str]]:
        """
        随机获取一个曲目的封面
        Returns:
            jacket (PIL.Image.Image): 封面图片.
            music_names (List[str]): 封面对应曲目的名称.
        """
        PATH_JACKET_CACHE_DIR = "resources/pjsk/jackets"
        URL_SEKAI_VIEWER_JACKET = "https://storage.sekai.best/sekai-jp-assets/music/jacket"

        # 从元数据中随机选择一个曲目
        music_id, music_names = random.choice(list(METADATA_.items()))

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

        return jacket, music_names

    @staticmethod
    def do_random_crop(jacket: PIL.Image.Image, size: int = 140) -> PIL.Image.Image:
        """
        随机裁剪封面图片为指定大小的正方形.
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
    def load_music_name_data() -> Dict[str, str]:
        """
        加载曲目名称数据.
        Returns:
            data (Dict[str, str]): 曲目名称数据列表.
        """
        data: Dict[str, str] = {}
        for music_id, music_names in METADATA_.items():
            for music_name in music_names:
                data[music_name.lower()] = music_id

        return data

    @staticmethod
    def get_best_match(alias: str, data: Dict[str, str]) -> List[List[str]]:
        """
        在数据中找到与别名最匹配的曲目id和曲目名称列表.
        Args:
            alias (str): 用户输入的别名.
            data (list): 曲目数据列表.            
        Returns:
            music_names (List[str]): 最匹配的3个曲目名称列表.
        """
        music_names = list(data.keys())
        best_match = difflib.get_close_matches(
            alias.lower(),
            music_names,
            n=3,
            cutoff=0
        )
        music_ids = [data[name] for name in best_match if name in data]
        music_names = [
            METADATA_.get(music_id, list()) for music_id in music_ids
        ]

        return music_names

    @staticmethod
    def get_music_names_for_message(music_names: List[str]) -> str:
        """
        编辑曲目名称以适应显示.
        Args:
            music_names (str): 原始曲目名称.
        Returns:
            music_names_edited (str): 编辑后的曲目名称.
        """
        match len(music_names):
            case 1:
                music_names_edited = f"**{music_names[0]}**"
            case 2:
                music_names_edited = f"**{music_names[0]}({music_names[1]})**"
            case 3:
                music_names_edited = f"**{music_names[0]}({music_names[1]}/{music_names[2]})**"

        return music_names_edited

    @staticmethod
    async def update_score_guess_jacket(user_id: int, user_name: str, guild_id: str) -> None:
        """
        更新猜谱面成绩, 需MongoDB使能打开.
        Args:
            user_id (int): 用户id.
            user_name (str): 要使用的用户昵称.
            guild_id (str): 群组id.
        """
        # 查找用户字段
        assert \
            isinstance(MONGO_DB_CLIENT_, pymongo.AsyncMongoClient), \
            "非预期的MongoDB调用, 请检查配置."
        collection = MONGO_DB_CLIENT_["PJSK-Guess"][guild_id]
        data = await collection.find_one({"user_id": user_id})

        # 更新猜谱面成绩
        if data:
            if "score_guess_jacket" in data.keys():
                await collection.update_one(
                    data,
                    {
                        "$set": {
                            "user_name": user_name,
                            "score_guess_jacket": data["score_guess_jacket"] + 1
                        }
                    }
                )
            else:  # "score_guess_jacket" not in data.keys()
                await collection.update_one(
                    data,
                    {
                        "$set": {
                            "user_name": user_name,
                            "score_guess_jacket": 1
                        }
                    }
                )
        else:   # data is None
            await collection.insert_one(
                {
                    "user_id": user_id,
                    "user_name": user_name,
                    "score_guess_jacket": 1
                }
            )

    @staticmethod
    async def get_ranking_guess_jacket(guild_id: str) -> List[Dict[str, Any]]:
        """
        获取猜谱面成绩排行, 需MongoDB使能打开.
        Args:
            guild_id (str): 群组id.
        Returns:
            ranking (List[Dict[str, Any]]): 群组前20名排行字典列表.
        """
        # 获取成绩
        assert \
            isinstance(MONGO_DB_CLIENT_, pymongo.AsyncMongoClient), \
            "非预期的MongoDB调用, 请检查配置."
        collection = MONGO_DB_CLIENT_["PJSK-Guess"][guild_id]
        cursor = collection.find({"score_guess_jacket": {"$exists": True}}) \
                           .sort("score_guess_jacket", pymongo.DESCENDING) \
                           .limit(20)
        ranking = [item async for item in cursor]

        return ranking

    @staticmethod
    async def gen_ranking_guess_jacket_info(guild_id: str, data: List[Dict[str, Any]]) -> str:
        """
        生成猜谱面成绩排行, 需MongoDB使能打开.
        Args:
            guild_id (str): 群组id.
            data (List[Dict[str, Any]]): 群组前20名排行字典列表.
        Returns:
            info_ranking (str): 群组前20名排行信息.
        """
        # 构建排行榜信息
        info_ranking = f"{'排 名': <4}{'次 数':>8}{'ID':>8}\n"
        for i, item in enumerate(data):
            info_ranking += (
                f"{str(i + 1):>4}"
                "  "
                f"{str(item['score_guess_jacket']) + ' 次':>8}"
                "      "
                f"{item['user_name']}\n"
            )

        return info_ranking.strip("\n")


if __name__ == '__main__':
    # 谱面抽取测试
    # jacket, music_name = LibPJSKGuess.get_random_jacket()
    # print(f"Music Name: {music_name}")
    # jacket.show()
    # jacket = LibPJSKGuess.do_random_crop(jacket, size=140)
    # jacket.show()

    # 曲名数据读取测试
    # import sys
    # music_name_data = LibPJSKGuess.load_music_name_data()
    # print(f"Loaded {len(music_name_data)} music names.")
    # print(f"music_name_data size: {sys.getsizeof(music_name_data)} bytes")
    # print(f"Sample data: {list(music_name_data.items())[:5]}")

    # 测试简体中文转换
    # text_tw = "世劃啟動"
    # text_cn = LibPJSKGuess.zh_tw_to_zh_cn(text_tw)
    # print(f"繁体中文: {text_tw} -> 简体中文: {text_cn}")

    # 测试最佳匹配
    # data = LibPJSKGuess.load_music_name_data()
    # alias = "喵"
    # best_match = LibPJSKGuess.get_best_match(alias, data)
    # print(f"Best match for '{alias}': {best_match[0]}, Names: {best_match}")

    # 测试数据库连接
    # import asyncio
    # async def test_mongo_db_connect():
    #     assert \
    #         isinstance(MONGO_DB_CLIENT_, pymongo.AsyncMongoClient), \
    #         "非预期的MongoDB调用, 请检查配置."
    #     collection = database['dev']
    #     item = {"context": "Hello World!"}

    #     await collection.insert_one(item)
    #     result = await collection.find_one(item)
    #     await collection.delete_one(item)
    #     await client.close()
    #     print(result)

    # asyncio.run(test_mongo_db_connect())

    # 测试更新谱面成绩
    # import asyncio

    # async def test_update_score_guess_jacket():
    #     assert \
    #         isinstance(MONGO_DB_CLIENT_, pymongo.AsyncMongoClient), \
    #         "非预期的MongoDB调用, 请检查配置."
    #     client = MONGO_DB_CLIENT_
    #     await LibPJSKGuess.update_score_guess_jacket(2, "IMaybeAbu", "dev")
    #     await client.close()
    #     print("Done.")

    # asyncio.run(test_update_score_guess_jacket())

    # 测试排行榜
    import asyncio

    async def test_get_ranking_guess_jacket():
        assert \
            isinstance(MONGO_DB_CLIENT_, pymongo.AsyncMongoClient), \
            "非预期的MongoDB调用, 请检查配置."
        client = MONGO_DB_CLIENT_
        guild_id = "dev"
        data = await LibPJSKGuess.get_ranking_guess_jacket(guild_id)
        info_ranking = await LibPJSKGuess.gen_ranking_guess_jacket_info(guild_id, data)
        await client.close()

        print(info_ranking)

    asyncio.run(test_get_ranking_guess_jacket())

    pass
