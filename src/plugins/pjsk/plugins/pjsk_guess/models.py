import asyncio
from abc import ABC, abstractmethod
from typing import Any, List, Tuple, TypedDict, Optional
import difflib

import ujson as json

from .database.base import PJSKGuessDatabaseBase


class PJSKGuessStatus(TypedDict):
    """
    猜曲状态类.
    Attributes:
        is_guessing (bool): 是否正在猜曲.
        resource (Any): 资源内容.
        music_names (Optional[List[str]]): 猜曲名称列表.
        user_guess_event (Optional[asyncio.Event]): 用户猜测正确事件.
        score_name (Optional[str]): 分数名称, 用于记录猜曲成绩.
    """
    is_guessing: bool
    resource: Any
    music_names: Optional[List[str]]
    user_guess_event: Optional[asyncio.Event]
    score_name: Optional[str]


class PJSKGuessStatusManager:
    """
    根据频道ID隔离管理不同频道猜曲状态的类.
    Attributes:
        _status (dict[int, PJSKGuessStatus]): 频道ID与猜曲状态的映射.
    """

    def __init__(self) -> None:
        """
        初始化猜曲状态管理器.
        """
        self._status: dict[int, PJSKGuessStatus] = {}

    def get(self, channel_id: int) -> PJSKGuessStatus:
        """
        获取指定频道的猜曲状态, 如果不存在则初始化一个新的状态.
        Args:
            channel_id (int): 频道ID.
        Returns:
            PJSKGuessStatus: 频道的猜曲状态.
        """
        if channel_id not in self._status:
            self._status[channel_id] = self._default()
        return self._status[channel_id]

    def clear(self, channel_id: int) -> None:
        """
        清理指定频道的猜曲状态, 频道必须具有状态且正处于猜曲中.
        Args:
            channel_id (int): 频道ID.
        """
        assert self._status.get(channel_id) is not None, "频道必须具有猜曲状态."
        assert self._status[channel_id]["is_guessing"] is True, "频道必须处于猜曲状态."
        self._status[channel_id] = self._default()

    def _default(self) -> PJSKGuessStatus:
        """
        返回默认猜曲状态.
        Returns:
            PJSKGuessStatus: 默认猜曲状态.
        """
        return {
            "is_guessing": False,
            "resource": None,
            "music_names": None,
            "user_guess_event": None,
            "score_name": None
        }


class PJSKGuessMetadata(dict[str, List[str]]):
    """
    PJSK猜曲元数据类, 包含曲目ID和名称的双向映射.
    正向映射为曲目ID到名称列表的字典,
    反向映射为列表中每个曲目名称单独对应到其ID的字典.
    Attributes:        
        inverse (dict[str, str]): 曲目名称与ID反向映射的字典.
    """
    inverse: dict[str, str]

    def __init__(self, path: str) -> None:
        """
        初始化PJSK猜曲元数据.
        Args:
            path (str): 元数据文件路径.        
        """
        with open(path, "r", encoding="utf-8") as f:
            metadata: dict[str, List[str]] = json.load(f)
        super().__init__(metadata)
        self.inverse = {}
        for music_id, music_names in metadata.items():
            for music_name in music_names:
                self.inverse[music_name.lower()] = music_id

    def get_best_match(self, alias: str, limits=3) -> List[List[str]]:
        """
        在数据中找到与别名最匹配的曲目id和曲目名称列表.
        Args:
            alias (str): 用户输入的别名.
            limit (int): 最多返回的匹配数量, 默认为3.
        Returns:
            music_names (List[str]): 最匹配的3个曲目名称列表.
        """
        data = self.inverse
        music_names = list(data.keys())
        best_match = difflib.get_close_matches(
            alias,
            music_names,
            n=limits,
            cutoff=0
        )
        music_ids = [data[name] for name in best_match if name in data]
        music_names = [
            self.get(music_id, list()) for music_id in music_ids
        ]

        return music_names

    def generate_message(self, music_names: List[str]) -> str:
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
                music_names_edited = \
                    f"**{music_names[0]}({music_names[1]}/{music_names[2]})**"
            case _:
                raise ValueError(
                    "致命错误: "
                    "意外的曲目名称列表长度, 只能处理1-3个曲目名称."
                )

        return music_names_edited


class PJSKGuessBase(ABC):
    """
    PJSK猜曲基础类, 定义获取和处理猜曲资源的接口.
    """
    # 提示信息
    INFO_BEGIN: str
    INFO_GUESSING: str
    INFO_TIMEOUT: str

    # 路径和URL常量
    PATH_CACHE_DIR: str
    URL_SEIKAI_VIEWER: str

    # 元数据
    METADATA: PJSKGuessMetadata

    # 数据库句柄
    database: Optional[PJSKGuessDatabaseBase]

    # 分数键名
    SCORE_NAME: str

    @abstractmethod
    def __init__(
        self,
        status_manager: PJSKGuessStatusManager,
        metadata: PJSKGuessMetadata,
        database: Optional[PJSKGuessDatabaseBase] = None
    ) -> None:
        """
        初始化PJSK猜曲基础类.
        Args:
            status_manager (PJSKGuessStatusManager): 猜曲状态管理器实例.
            metadata (dict): 元数据字典.
            database (Optional[PJSKGuessDatabaseBase]): 数据库实例, 默认为None.
        """
        pass

    @abstractmethod
    def get_resource(self, channel_id: int) -> Tuple[Any, List[str]]:
        """
        获取猜曲资源.
        Args:
            channel_id (int): 频道ID.
        Returns:
            resource (Any): 猜曲资源内容.
        """
        pass

    @abstractmethod
    def process_resource(self, resource: Any) -> Any:
        """
        对获取的资源进行处理.
        Args:
            resource (Any): 原始资源内容.
        Returns:
            resource_processed (Any): 处理后的资源内容.
        """
        pass

    @abstractmethod
    async def handle_user_begin(self, event: Any) -> None:
        """
        处理猜曲开始事件.
        Args:
            event (Any): 事件对象, 包含猜曲开始信息.
        """
        pass

    @abstractmethod
    async def handle_user_guess(self, event: Any) -> None:
        """
        处理用户猜测事件.
        Args:
            event (Any): 事件对象, 包含用户猜测信息.
        """
        pass

    @abstractmethod
    async def handle_user_end(self, event: Any) -> None:
        """
        处理猜曲结束事件.
        Args:
            event (Any): 事件对象, 包含结束猜曲信息.
        """
        pass

    @abstractmethod
    def _register_matchers(self) -> None:
        """
        注册事件响应器, 在构造函数中调用.
        """
        pass
