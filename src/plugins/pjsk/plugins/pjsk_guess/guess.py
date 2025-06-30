import os
import random
import asyncio
import requests
from io import BytesIO
from typing import Type, Tuple, List, Optional

import PIL.Image
import ujson as json

from nonebot import on_type
from nonebot.matcher import Matcher
from nonebot.rule import startswith, fullmatch
from nonebot.adapters.discord import MessageSegment, GuildMessageCreateEvent
from nonebot.adapters.discord.api import File, MessageReference

from .utils import convert_text
from .models import PJSKGuessBase
from .models import PJSKGuessStatusManager as StatusManager
from .models import PJSKGuessMetadata as Metadata
from .database.mongo import PJSKGuessDatabase as Database


class PJSKGuess(PJSKGuessBase):
    """
    PJSK猜曲, 曲绘竞猜.    
    """
    # 提示信息
    INFO_BEGIN = (
        "PJSK曲绘竞猜 (随机裁切)\n"
        "使用横杠\"-\"加答案以参加猜曲\n\n"
        "你有60秒的时间回答\n"
        "可手动发送\"结束猜曲\"来结束猜曲\n\n"
        "Jacket guess, answer by \"-\" + song name, send \"endpjskguess\" to end"
    )
    INFO_GUESSING = "已经开始猜曲!"
    INFO_CORRECT = ":white_check_mark:您猜对了(Right answer)\n"
    INFO_INCORRECT = ":x:您猜错了(Wrong answer), 答案不是"
    INFO_TIMEOUT = "时间到, 正确答案: "
    INFO_END = "正确答案: "
    INFO_NOT_GUESSING = "当前没有猜曲哦"

    # 路径和URL常量
    PATH_CACHE_DIR = "resources/pjsk/jackets"
    URL_SEIKAI_VIEWER = "https://storage.sekai.best/sekai-jp-assets/music/jacket"

    # 元数据
    METADATA: Metadata

    # 事件响应器
    match_user_begin: Type[Matcher]
    match_user_guess: Type[Matcher]
    match_user_end: Type[Matcher]
    match_user_get_ranking: Optional[Type[Matcher]]

    def __init__(
        self,
        status_manager: StatusManager,
        metadata: Metadata,
        database: Optional[Database] = None
    ) -> None:
        """
        初始化PJSKGuess实例.
        Args:
            status_manager (GuessStatusManager): 猜曲状态管理器实例.
            metadata (Optional[Metadata]): 曲目元数据实例, 如果为None则加载默认元数据.
            database (Optional[Database]): 数据库实例, 用于存储和获取猜曲
        """
        super().__init__(
            status_manager,
            metadata,
            database
        )
        self.match_user_begin = on_type(
            GuildMessageCreateEvent,
            rule=fullmatch(("pjsk猜曲", "pjskguess")),
            handlers=[self.handle_user_begin]
        )
        self.match_user_guess = on_type(
            GuildMessageCreateEvent,
            rule=startswith("-"),
            handlers=[self.handle_user_guess]
        )
        self.match_user_end = on_type(
            GuildMessageCreateEvent,
            rule=fullmatch(("结束猜曲", "結束猜曲", "endpjskguess")),
            handlers=[self.handle_user_end]
        )
        if self.database is not None:
            self.match_user_get_ranking = on_type(
                GuildMessageCreateEvent,
                rule=fullmatch(("猜曲排行")),
                handlers=[self.handle_user_get_ranking]
            )

    def get_resource(self) -> Tuple[PIL.Image.Image, List[str]]:
        """
        随机获取一个曲目的封面
        Returns:
            jacket (PIL.Image.Image): 封面图片.
            music_names (List[str]): 封面对应曲目的名称.
        """
        # 从元数据中随机选择一个曲目
        music_id, music_names = random.choice(list(self.METADATA.items()))

        # 检查封面是否已缓存，如果不存在则从sekaiviewer下载
        if not os.path.exists(self.PATH_CACHE_DIR):
            os.makedirs(self.PATH_CACHE_DIR, exist_ok=True)
        if os.path.exists(self.PATH_CACHE_DIR + f"/jacket_s_{music_id}.png"):
            jacket = PIL.Image.open(
                self.PATH_CACHE_DIR + f"/jacket_s_{music_id}.png")
        else:
            url = self.URL_SEIKAI_VIEWER + \
                f"/jacket_s_{music_id}/jacket_s_{music_id}.webp"
            src = requests.get(url, timeout=10)
            raw = BytesIO(src.content)
            jacket = PIL.Image.open(raw)
            jacket.save(
                f"{self.PATH_CACHE_DIR}/jacket_s_{music_id}.png",
                format="png"
            )

        return jacket, music_names

    def process_resource(
        self,
        jacket: PIL.Image.Image,
        size: int = 140
    ) -> PIL.Image.Image:
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

    async def handle_user_begin(
        self,
        event: GuildMessageCreateEvent
    ) -> None:
        """
        处理猜曲开始事件.
        Args:
            event (GuildMessageCreateEvent): 事件对象.
        """
        # 获取消息引用
        message_id = event.message_id
        message_reference = MessageReference(message_id=message_id)
        message_reference = MessageSegment.reference(message_reference)

        # 获取频道状态并检查, 如果频道已在猜曲中则发送消息
        channel_id = event.channel_id
        status = self.status_manager.get(channel_id)
        if status.get("is_guessing", False) is True:
            await self.match_user_begin.finish(
                message_reference
                + self.INFO_GUESSING
            )

        # 获取随机封面、裁剪后封面、曲目名称
        jacket, music_names = self.get_resource()
        jacket_cropped = self.process_resource(jacket)

        # 将封面转换为 message
        file = BytesIO()
        jacket.save(file, format="PNG")
        file = File(content=file.getvalue(), filename="jacket.png")
        jacket = MessageSegment.attachment(file)

        # 将裁剪后封面转换为 message
        file = BytesIO()
        jacket_cropped.save(file, format="PNG")
        file = File(content=file.getvalue(), filename="jacket_cropped.png")
        jacket_cropped = MessageSegment.attachment(file)

        # 设置状态
        handle = asyncio.Event()
        status.update(
            {
                "is_guessing": True,
                "resource": jacket,
                "music_names": music_names,
                "user_guess_event": handle
            }
        )

        # 发送消息
        await self.match_user_begin.send(
            message_reference + self.INFO_BEGIN + jacket_cropped
        )

        # 设置频道状态为正在猜曲
        try:
            await asyncio.wait_for(handle.wait(), timeout=60)
            await self.match_user_begin.finish()
        except asyncio.TimeoutError:
            # 超时处理, 发送结束消息并清理状态
            self.status_manager.clear(channel_id)
            await self.match_user_begin.finish(
                self.INFO_TIMEOUT
                + self.METADATA.generate_message(music_names)
                + jacket
            )

    async def handle_user_guess(self, event: GuildMessageCreateEvent) -> None:
        """
        处理用户猜测事件.
        Args:
            event (GuildMessageCreateEvent): 事件对象.
        """
        # 获取频道状态并检查, 如果频道不在猜曲中则不响应
        channel_id = event.channel_id
        status = self.status_manager.get(channel_id)
        if status["is_guessing"] is False:
            await self.match_user_guess.finish()
        else:
            assert isinstance(status["user_guess_event"], asyncio.Event), \
                "频道正处于猜曲时必须具有 user_guess_event 句柄."
            assert status["user_guess_event"].is_set() is False, \
                "频道正处于猜曲时 user_guess_event 句柄不应被置位."

        # 获取消息引用
        message_id = event.message_id
        message_reference = MessageReference(message_id=message_id)
        message_reference = MessageSegment.reference(message_reference)

        # 获取用户猜测内容
        guess_content = event.content[1:]
        guess_content = convert_text(guess_content)

        # 匹配用户猜测内容
        music_names = self.METADATA.get_best_match(guess_content)
        if status["music_names"] in music_names:
            # 取消等待任务
            status["user_guess_event"].set()

            # 构造用户猜测正确消息
            music_names_edited = \
                self.METADATA.generate_message(status["music_names"])

            # 发送用户猜测正确信息
            await self.match_user_guess.send(
                message_reference
                + self.INFO_CORRECT
                + music_names_edited
                + status["resource"]
            )

            # 清理频道猜曲状态
            self.status_manager.clear(channel_id)

            # 获取信息
            user_id = event.user_id
            user_name = event.member.nick  \
                if event.member.nick \
                else event.author.global_name
            guild_id = event.guild_id
            assert isinstance(user_name, str)

            # 更新用户成绩
            if self.database is not None:
                await self.database.update(
                    user_id=user_id,
                    guild_id=guild_id
                )

            # 结束猜曲
            await self.match_user_guess.finish()

        # status["music_names"] NOT in music_names
        else:
            # 发送用户猜测错误信息并结束猜曲
            music_names_edited = \
                self.METADATA.generate_message(music_names[0])
            info_incorrect = f"{self.INFO_INCORRECT}**{music_names_edited}**哦"
            await self.match_user_guess.finish(message_reference + info_incorrect)

    async def handle_user_end(self, event: GuildMessageCreateEvent) -> None:
        """
        处理用户结束猜曲事件.
        Args:
            event (GuildMessageCreateEvent): 事件对象.
        """
        # 获取频道状态
        channel_id = event.channel_id
        status = self.status_manager.get(channel_id)

        # 获取消息引用
        message_id = event.message_id
        message_reference = MessageReference(message_id=message_id)
        message_reference = MessageSegment.reference(message_reference)

        # 检查是否在猜曲状态
        if status["is_guessing"] is True:
            assert isinstance(status["user_guess_event"], asyncio.Event), \
                "频道正处于猜曲时必须具有 user_guess_event 句柄."
            assert status["user_guess_event"].is_set() is False, \
                "频道正处于猜曲时 user_guess_event 句柄不应被置位."

            # 取消等待任务
            status["user_guess_event"].set()

            # 获取封面和曲目名称
            assert status["resource"] is not None, \
                "频道正处于猜曲时必须具有 resource."
            assert status["music_names"] is not None, \
                "频道正处于猜曲时必须具有 music_names."

            jacket = status["resource"]
            music_names = status["music_names"]
            music_name_edited = self.METADATA.generate_message(music_names)

            # 清理频道猜曲状态
            self.status_manager.clear(channel_id)

            # 发送结束消息
            await self.match_user_end.finish(
                message_reference
                + self.INFO_END
                + music_name_edited
                + jacket
            )

        # status["is_guessing"] IS False
        else:
            await self.match_user_end.finish(
                message_reference
                + self.INFO_NOT_GUESSING
            )

    async def handle_user_get_ranking(
        self,
        event: GuildMessageCreateEvent
    ) -> None:
        """
        处理获取猜曲排行榜事件.
        Args:
            event (GuildMessageCreateEvent): 事件对象.
        """
        assert self.database is not None, "非预期的调用, 请检查配置数据库配置."
        assert self.match_user_get_ranking is not None, \
            "致命错误: 猜曲获取排行榜事件处理器未初始化."

        # 获取消息引用
        message_id = event.message_id
        message_reference = MessageReference(message_id=message_id)
        message_reference = MessageSegment.reference(message_reference)

        # 获取排行榜数据
        guild_id = event.guild_id
        data = await self.database.get_ranking_data(
            guild_id=guild_id,
            limit=20
        )

        # 构建排行榜信息
        info_ranking = await self.database.generate_ranking(guild_id, data)

        # 构建用户信息
        user_id = event.user_id
        for i, data in enumerate(data):
            if user_id == data["user_id"]:
                info_user = (
                    f'\n\n您的排名:{i + 1:>8} 位\n'
                    f'猜中次数:{data["score_guess_jacket"]:>8} 次'
                )
                break
        else:
            info_user = f"\n\n您的排名: 暂无排名"

        await self.match_user_get_ranking.finish(
            message_reference +
            "```python\n" +
            info_ranking +
            info_user +
            "\n```"
        )
