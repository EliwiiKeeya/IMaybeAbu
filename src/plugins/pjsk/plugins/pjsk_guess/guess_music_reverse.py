import random

import pydub
from nonebot import on_type
from nonebot.rule import fullmatch
from nonebot.adapters.discord import GuildMessageCreateEvent

from .guess_music import PJSKGuessMusic


class PJSKGuessMusicReverse(PJSKGuessMusic):
    """
    PJSK倒放猜曲, 倒放识曲竞猜.
    继承自PJSKGuess.
    """
    INFO_BEGIN = (
        "PJSK倒放识曲竞猜 (随机裁切)\n"
        "使用横杠\"-\"加答案以参加猜曲\n\n"
        "你有60秒的时间回答\n"
        "可手动发送\"结束猜曲\"来结束猜曲\n\n"
        "Jacket guess, answer by \"-\" + song name, send \"endpjskguess\" to end"
    )

    # 分数键名
    SCORE_NAME = "score_guess_music_reverse"

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

        return music_cropped.reverse()

    def _register_matchers(self) -> None:
        """
        注册事件响应器, 在构造函数中调用.
        """
        self.match_user_begin = on_type(
            GuildMessageCreateEvent,
            rule=fullmatch(("pjsk倒放猜曲", "pjskguessmusicreverse")),
            handlers=[self.handle_user_begin]
        )

        if self.database is not None:
            self.match_user_get_ranking = on_type(
                GuildMessageCreateEvent,
                rule=fullmatch(("倒放猜曲排行")),
                handlers=[self.handle_user_get_ranking]
            )
