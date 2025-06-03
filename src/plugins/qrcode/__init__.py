from nonebot.adapters.discord import MessageSegment
from nonebot.adapters.discord.api import (
    StringOption,
    File,
)
from nonebot.adapters.discord.commands import (
    CommandOption,
    on_slash_command,
)

from .config import QRCodeAbu

matcher = on_slash_command(
    name="qrcode",
    description="二維碼",
    options=[
        StringOption(name="text", description="内容", required=True)
    ],
)


@matcher.handle()
async def handle_qrcode(text: CommandOption[str]):
    await matcher.send_deferred_response()
    file = QRCodeAbu.excute(text)
    file = File(content=file, filename="qrcode.png")
    await matcher.send_followup_msg(MessageSegment.attachment(file))
