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


class PJSKGuessGray(PJSKGuess):
    """
    PJSK阴间猜曲, 灰度曲绘竞猜.
    继承自PJSKGuess.
    """
    INFO_BEGIN = (
        "PJSK阴间曲绘竞猜 (随机裁切)\n"
        "使用横杠\"-\"加答案以参加猜曲\n\n"
        "你有60秒的时间回答\n"
        "可手动发送\"结束猜曲\"来结束猜曲\n\n"
        "Jacket guess, answer by \"-\" + song name, send \"endpjskguess\" to end"
    )

    SCORE_NAME = "score_guess_jacket_gray"

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
        size: int = 140
    ) -> PIL.Image.Image:
        """
        随机裁剪封面图片为指定大小的正方形.
        Args:
            jacket (PIL.Image.Image): 原始封面图片.
            size (int): 裁剪后的正方形大小，默认为140像素.
        Returns:
            jacket_croped (PIL.Image.Image): 裁剪后的正方形封面图片(灰度).
        """
        x_rand = random.randint(0, jacket.width - size)
        y_rand = random.randint(0, jacket.height - size)
        jacket_cropped = jacket.crop(
            (x_rand, y_rand, x_rand + size, y_rand + size))
        jacket_cropped = jacket_cropped.convert("L")
        return jacket_cropped

    def _register_matchers(self) -> None:
        """
        注册事件响应器, 在构造函数中调用.
        """
        self.match_user_begin = on_type(
            GuildMessageCreateEvent,
            rule=fullmatch(("pjsk阴间猜曲", "pjsk陰間猜曲", "pjskguessgray")),
            handlers=[self.handle_user_begin]
        )

        if self.database is not None:
            self.match_user_get_ranking = on_type(
                GuildMessageCreateEvent,
                rule=fullmatch(("阴间猜曲排行", "陰間猜曲排行")),
                handlers=[self.handle_user_get_ranking]
            )
