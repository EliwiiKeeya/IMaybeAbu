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
        raise NotImplementedError("子类必须实现 __init__ 方法")

    @abstractmethod
    async def update(self, guild_id: int, user_id: int):
        """
        连接到数据库.
        Args:
            guild_id (int): 群组ID.
            user_id (int): 用户ID.
        """
        pass

    @abstractmethod
    async def get_ranking_data(
        self,
        guild_id: int,
        limit: int = 20
    ) -> list[dict[str, Any]]:
        """
        获取猜曲排行榜.
        Args:
            guild_id (int): 群组ID.
            limit (int): 排行榜限制数量, 默认为20.
        Returns:
            List[Dict]: 排行榜数据列表, 每个字典包含用户ID和分数.
        """
        raise NotImplementedError("子类必须实现 get_ranking_data 方法")

    @abstractmethod
    async def generate_ranking(
        self,
        guild_id: int,
        data: list[dict[str, Any]]
    ) -> str:
        """
        生成排行榜信息字符串.
        Args:
            guild_id (int): 群组ID.
            data (List[Dict]): 排行榜数据列表.
        Returns:
            ranking (str): 格式化的排行榜信息字符串.
        """
        raise NotImplementedError("子类必须实现 generate_ranking 方法")
