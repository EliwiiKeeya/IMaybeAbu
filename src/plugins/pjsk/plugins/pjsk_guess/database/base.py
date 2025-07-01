from abc import ABC, abstractmethod
from typing import Any


class PJSKGuessDatabaseBase(ABC):
    """
    抽象基类, 定义了猜曲数据库的基本接口.
    """
    @abstractmethod
    def __init__(self) -> None:
        """
        初始化数据库连接.
        Args:
            db_config (dict): 数据库配置字典.
        """
        pass

    @abstractmethod
    async def update(self, guild_id: int, user_id: int, key: str) -> None:
        """
        更新猜曲数据.
        Args:
            guild_id (int): 群组ID.
            user_id (int): 用户ID.
            key (str): 要更新分数对应的键.
        """
        pass

    @abstractmethod
    async def get_ranking_data(
        self,
        guild_id: int,
        key: str,
        limit: int = 20
    ) -> list[dict[str, Any]]:
        """
        获取猜曲排行榜.
        Args:
            guild_id (int): 群组ID.
            limit (int): 排行榜限制数量, 默认为20.
            key (str): 排行榜分数对应的键.
        Returns:
            List[Dict]: 排行榜数据列表, 每个字典包含用户ID和分数.
        """
        pass

    @abstractmethod
    async def generate_ranking(
        self,
        guild_id: int,
        data: list[dict[str, Any]],
        key: str
    ) -> str:
        """
        生成排行榜信息字符串.
        Args:
            guild_id (int): 群组ID.
            data (List[Dict]): 排行榜数据列表.
            key (str): 排行榜分数对应的键.
        Returns:
            ranking (str): 格式化的排行榜信息字符串.
        """
        pass
