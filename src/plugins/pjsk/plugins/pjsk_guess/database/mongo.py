from typing import Any

import pymongo
from pymongo import AsyncMongoClient
from nonebot import on_type, get_adapter, get_bot
from nonebot.adapters.discord.api import GuildMember, API_HANDLERS

from .base import PJSKGuessDatabaseBase as DatabaseBase

get_guild_member = API_HANDLERS["get_guild_member"]


class PJSKGuessDatabase(DatabaseBase, AsyncMongoClient):
    """
    MongoDB实现的PJSK猜曲数据库.
    继承自PJSKGuessDatabaseBase, 实现了MongoDB特定的连接和操作方法.
    用于更新和获取猜曲成绩数据.
    """

    def __init__(self, uri: str, score_name: str = "score_guess_jacket") -> None:
        """
        初始化MongoDB连接.
        Args:
            uri (str): MongoDB连接URI.
            score_name (str): 关键字, 用于指定分数名称.
        """
        AsyncMongoClient.__init__(self, uri)
        self._key = score_name

    async def update(
        self,
        guild_id: int,
        user_id: int
    ):
        """
        更新状态.
        Args:
            user_id (int): 用户ID.            
            guild_id (str): 服务器ID.
        """
        # 查找用户字段
        collection = self["PJSK-Guess"][str(guild_id)]
        data = await collection.find_one({"user_id": user_id})

        # 更新猜谱面成绩
        if data is not None:
            if self._key in data.keys():
                await collection.update_one(
                    data,
                    {
                        "$set": {
                            self._key: data["score_guess_jacket"] + 1
                        }
                    }
                )
            else:  # self._key not in data.keys()
                await collection.update_one(
                    data,
                    {
                        "$set": {
                            self._key: 1
                        }
                    }
                )

        # data IS None
        else:
            await collection.insert_one(
                {
                    "user_id": user_id,
                    self._key: 1
                }
            )

    async def get_ranking_data(
        self,
        guild_id: int,
        limit: int = 20
    ) -> list[dict[str, Any]]:
        """
        获取猜曲排行榜数据.
        Args:
            guild_id (int): 群组ID.
            limit (int): 排行榜限制数量, 默认为20.
        Returns:
            data (List[Dict[str, Any]]): 群组前20名排行字典列表.
        """
        collection = self["PJSK-Guess"][str(guild_id)]
        cursor = collection.find() \
                           .sort(self._key, pymongo.DESCENDING) \
                           .limit(limit)
        data = cursor.to_list()
        return await data

    async def generate_ranking(
        self,
        guild_id: int,
        data: list[dict[str, Any]]
    ) -> str:
        """
        生成猜谱面成绩排行.
        Args:
            guild_id (int): 群组ID.
            data (List[Dict[str, Any]]): 群组前20名排行字典列表.
        Returns:
            ranking (str): 群组前20名排行信息.
        """
        # 获取句柄参数
        bot = get_bot()
        adapter = get_adapter("Discord")

        # 构建排行榜信息
        info_ranking = f"{'排 名': <4}{'次 数':>8}{'ID':>8}\n"
        for i, item in enumerate(data):
            user: GuildMember = await get_guild_member(adapter, bot, guild_id, item["user_id"])
            user_name = user.nick if user.nick else user.user.global_name
            info_ranking += (
                f"{str(i + 1):>4}"
                "  "
                f"{str(item[self._key]) + ' 次':>8}"
                "      "
                f"{user_name}\n"
            )

        # 删除最后的换行符并返回
        return info_ranking.strip("\n")
