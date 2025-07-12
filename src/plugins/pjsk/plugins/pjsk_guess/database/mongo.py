from typing import Any

import pymongo
from pymongo import AsyncMongoClient
from nonebot import get_adapter, get_bot
from nonebot.adapters.discord.api import GuildMember, API_HANDLERS

from .base import PJSKGuessDatabaseBase as DatabaseBase

get_guild_member = API_HANDLERS["get_guild_member"]


class PJSKGuessDatabase(DatabaseBase, AsyncMongoClient):
    """
    MongoDB实现的PJSK猜曲数据库.
    继承自PJSKGuessDatabaseBase, 实现了MongoDB特定的连接和操作方法.
    用于更新和获取猜曲成绩数据.
    """

    def __init__(self, uri: str) -> None:
        """
        初始化MongoDB连接.
        Args:
            uri (str): MongoDB连接URI.
        """
        AsyncMongoClient.__init__(self, uri)

    async def update(
        self,
        guild_id: int,
        user_id: int,
        key: str
    ):
        """
        更新状态.
        Args:
            user_id (int): 用户ID.            
            guild_id (str): 服务器ID.
            key (str): 要更新分数对应的键.
        """
        collection = self["PJSK-Guess"][str(guild_id)]
        await collection.update_one(
            {"user_id": user_id},
            {"$inc": {key: 1}},
            upsert=True
        )

    async def get_ranking_data(
        self,
        guild_id: int,
        key: str,
        limit: int = 20
    ) -> list[dict[str, Any]]:
        """
        获取猜曲排行榜数据.
        Args:
            guild_id (int): 群组ID.
            limit (int): 排行榜限制数量, 默认为20.
            key (str): 排行榜分数对应的键.
        Returns:
            data (List[Dict[str, Any]]): 群组前20名排行字典列表.
        """
        collection = self["PJSK-Guess"][str(guild_id)]
        cursor = collection.find({key: {"$exists": True}}) \
                           .sort(key, pymongo.DESCENDING) \
                           .limit(limit)
        data = cursor.to_list()
        return await data

    async def generate_ranking(
        self,
        guild_id: int,
        data: list[dict[str, Any]],
        key: str
    ) -> str:
        """
        生成猜谱面成绩排行.
        Args:
            guild_id (int): 群组ID.
            data (List[Dict[str, Any]]): 群组前20名排行字典列表.
            key (str): 排行榜分数对应的键.
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
                f"{str(item[key]) + ' 次':>8}"
                "      "
                f"{user_name}\n"
            )

        # 删除最后的换行符并返回
        return info_ranking.strip("\n")
