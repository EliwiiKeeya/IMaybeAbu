import os
import random
import asyncio
import requests
from io import BytesIO
from typing import List, Optional, Tuple

import PIL.Image
import pydub
from nonebot import on_type
from nonebot.rule import fullmatch
from nonebot.adapters.discord.api import File, MessageReference
from nonebot.adapters.discord import MessageSegment, GuildMessageCreateEvent

from .guess import PJSKGuess
from .models import PJSKGuessStatusManager as StatusManager
from .models import PJSKGuessMetadata as Metadata
from .database.mongo import PJSKGuessDatabase as Database


class PJSKGuessMusic(PJSKGuess):
    """
    PJSK听歌猜曲, 听歌识曲竞猜.
    继承自PJSKGuess.
    """
    INFO_BEGIN = (
        "PJSK听歌识曲竞猜 (随机裁切)\n"
        "使用横杠\"-\"加答案以参加猜曲\n\n"
        "你有60秒的时间回答\n"
        "可手动发送\"结束猜曲\"来结束猜曲\n\n"
        "Jacket guess, answer by \"-\" + song name, send \"endpjskguess\" to end"
    )

    # 路径和URL常量
    PATH_CACHE_DIR = "resources/pjsk"
    PATH_CACHE_DIR_MUSIC = PATH_CACHE_DIR + "/musics"
    PATH_CACHE_DIR_JACKET = PATH_CACHE_DIR + "/jackets"
    URL_SEIKAI_VIEWER = "https://storage.sekai.best/sekai-jp-assets/music"
    URL_SEIKAI_VIEWER_MUSIC = URL_SEIKAI_VIEWER + "/long"
    URL_SEIKAI_VIEWER_JACKET = URL_SEIKAI_VIEWER + "/jacket"

    # 分数键名
    SCORE_NAME = "score_guess_music"

    def __init__(
        self,
        status_manager: StatusManager,
        metadata: Metadata,
        database: Optional[Database] = None
    ):
        """
        初始化PJSK猜曲听歌模式.
        Args:
            status_manager (StatusManager): 状态管理器.
            metadata (Metadata): 元数据管理器.
            database (Database, optional): 数据库连接. 默认为None.
        """
        super().__init__(status_manager, metadata, database)

    def get_resource(self) -> Tuple[PIL.Image.Image, pydub.AudioSegment, List[str]]:
        """
        随机获取一个曲目的封面和音频.
        Returns:
            jacket (PIL.Image.Image): 封面图片.
            music (pydub.AudioSegment): 音频片段.
            music_names (List[str]): 封面对应曲目的名称.
        """
        # 从元数据中随机选择一个曲目
        music_id, music_names = random.choice(list(self.METADATA.items()))

        # 检查缓存目录是否存在
        if not os.path.exists(self.PATH_CACHE_DIR_JACKET):
            os.makedirs(self.PATH_CACHE_DIR_JACKET, exist_ok=True)
        if not os.path.exists(self.PATH_CACHE_DIR_MUSIC):
            os.makedirs(self.PATH_CACHE_DIR_MUSIC, exist_ok=True)

        # 检查封面是否已缓存，如果不存在则从sekaiviewer下载
        if os.path.exists(
                self.PATH_CACHE_DIR_JACKET + f"/jacket_s_{music_id}.png"):
            jacket = PIL.Image.open(
                self.PATH_CACHE_DIR_JACKET + f"/jacket_s_{music_id}.png")
        else:
            url = self.URL_SEIKAI_VIEWER_JACKET + \
                f"/jacket_s_{music_id}/jacket_s_{music_id}.webp"
            src = requests.get(url, timeout=10)
            raw = BytesIO(src.content)
            jacket = PIL.Image.open(raw)
            jacket.save(
                f"{self.PATH_CACHE_DIR_JACKET}/jacket_s_{music_id}.png",
                format="png"
            )

        # 检查音频文件是否已缓存，如果不存在则从sekaiviewer下载
        file_names = [
            f"/se_{music_id:0>4}_01/se_{music_id:0>4}_01.mp3",
            f"/vs_{music_id:0>4}_01/vs_{music_id:0>4}_01.mp3",
            f"/{music_id:0>4}_01/{music_id:0>4}/01.mp3"
        ]

        if os.path.exists(self.PATH_CACHE_DIR_MUSIC + f"/{music_id}_01.mp3"):
            music = pydub.AudioSegment.from_mp3(
                self.PATH_CACHE_DIR_MUSIC + f"/{music_id}_01.mp3")
        else:
            for file_name in file_names:
                url = self.URL_SEIKAI_VIEWER_MUSIC + file_name
                try:
                    src = requests.get(url, timeout=10)
                    src.raise_for_status()
                except:
                    continue
                raw = BytesIO(src.content)
                music: pydub.AudioSegment = pydub.AudioSegment.from_mp3(raw)
                music.export(
                    self.PATH_CACHE_DIR_MUSIC + f"/{music_id}_01.mp3",
                    format="mp3"
                )
                break

        return jacket, music, music_names

    def process_resource(
        self,
        music: pydub.AudioSegment,
    ) -> pydub.AudioSegment:
        """
        随机裁剪音频片段.
        Args:
            music (pydub.AudioSegment): 原始音频片段.
        Returns:
            pydub.AudioSegment: 随机裁剪后的音频片段.
        """
        length = int(music.duration_seconds)
        starttime = random.randint(20, length - 10)
        music_cropped = music[starttime * 1000: starttime * 1000 + 5000]
        assert isinstance(music_cropped, pydub.AudioSegment), \
            "裁剪后的音频片段应该是pydub.AudioSegment类型"

        return music_cropped

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

        # 获取封面、音频和曲目名称
        jacket, music, music_names = self.get_resource()
        music_cropped = self.process_resource(music)

        # 将封面转换为 message
        file = BytesIO()
        jacket.save(file, format="PNG")
        file = File(content=file.getvalue(), filename="jacket.png")
        jacket = MessageSegment.attachment(file)

        # 将音频转换为 message
        file = BytesIO()
        music.export(file, format="mp3")
        file = File(content=file.getvalue(), filename="music.mp3")
        music = MessageSegment.attachment(file)

        # 将裁剪后音频转换为 message
        file = BytesIO()
        music_cropped.export(file, format="mp3")
        file = File(content=file.getvalue(), filename="music_cropped.mp3")
        music_cropped = MessageSegment.attachment(file)

        # 设置状态
        handle = asyncio.Event()
        status.update(
            {
                "is_guessing": True,
                "resource": jacket + music,
                "music_names": music_names,
                "user_guess_event": handle,
                "score_name": self.SCORE_NAME
            }
        )

        # 发送消息
        await self.match_user_begin.send(
            message_reference + self.INFO_BEGIN + music_cropped
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
                + music
            )

    def _register_matchers(self) -> None:
        """
        注册事件响应器, 在构造函数中调用.
        """
        self.match_user_begin = on_type(
            GuildMessageCreateEvent,
            rule=fullmatch(("pjsk听歌猜曲", "pjsk聽歌猜曲", "pjskguessmusic")),
            handlers=[self.handle_user_begin]
        )

        if self.database is not None:
            self.match_user_get_ranking = on_type(
                GuildMessageCreateEvent,
                rule=fullmatch(("听歌猜曲排行", "聽歌猜曲排行")),
                handlers=[self.handle_user_get_ranking]
            )
