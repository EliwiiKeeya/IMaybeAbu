import random
from typing import Optional

import PIL.Image
from nonebot import on_type
from nonebot.rule import fullmatch
from nonebot.adapters.discord import GuildMessageCreateEvent

from .guess import PJSKGuess
from .models import PJSKGuessStatusManager as StatusManager
from .models import PJSKGuessMetadata as Metadata
from .database.mongo import PJSKGuessDatabase as Database


class PJSKGuessHard(PJSKGuess):
    """
    PJSK非人类猜曲, 困难曲绘竞猜.
    继承自PJSKGuess.
    """
    INFO_BEGIN = (
        "PJSK非人类曲绘竞猜 (随机裁切)\n"
        "使用横杠\"-\"加答案以参加猜曲\n\n"
        "你有60秒的时间回答\n"
        "可手动发送\"结束猜曲\"来结束猜曲\n\n"
        "Jacket guess, answer by \"-\" + song name, send \"endpjskguess\" to end"
    )

    SCORE_NAME = "score_guess_jacket_hard"

    def __init__(
        self,
        status_manager: StatusManager,
        metadata: Metadata,
        database: Optional[Database] = None
    ):
        """
        初始化PJSK猜曲灰色模式.
        Args:
            status_manager (StatusManager): 状态管理器.
            metadata (Metadata): 元数据管理器.
            database (Database, optional): 数据库连接. 默认为None.
        """
        super().__init__(status_manager, metadata, database)

    def process_resource(
        self,
        jacket: PIL.Image.Image,
        size: int = 30
    ) -> PIL.Image.Image:
        """
        随机裁剪封面图片为指定大小的正方形.
        Args:
            jacket (PIL.Image.Image): 原始封面图片.
            size (int): 裁剪后的正方形大小，默认为30像素.
        Returns:
            jacket_croped (PIL.Image.Image): 裁剪后的正方形封面图片(灰度).
        """
        x_rand = random.randint(0, jacket.width - size)
        y_rand = random.randint(0, jacket.height - size)
        jacket_cropped = jacket.crop(
            (x_rand, y_rand, x_rand + size, y_rand + size))
        return jacket_cropped

    def _register_matchers(self) -> None:
        """
        注册事件响应器, 在构造函数中调用.
        """
        self.match_user_begin = on_type(
            GuildMessageCreateEvent,
            rule=fullmatch(("pjsk非人类猜曲", "pjsk非人類猜曲", "pjskguesshard")),
            handlers=[self.handle_user_begin]
        )

        if self.database is not None:
            self.match_user_get_ranking = on_type(
                GuildMessageCreateEvent,
                rule=fullmatch(("非人类猜曲排行", "非人類猜曲排行")),
                handlers=[self.handle_user_get_ranking]
            )
