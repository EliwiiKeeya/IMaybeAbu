from nonebot.adapters.discord import (
    ApplicationCommandInteractionEvent
)
from nonebot.adapters.discord.api import StringOption
from nonebot.adapters.discord.commands import (
    CommandOption,
    on_slash_command,
)

# 命令响应器
echo = on_slash_command(
    name="echo",
    description="发送消息",
    description_localizations={
        "zh-CN": "发送消息",
        "zh-TW": "發送消息"
    },
    options=[
        StringOption(
            name="content",
            description="要发送的消息内容",
            description_localizations={
                "zh-CN": "要发送的消息内容",
                "zh-TW": "要發送的消息內容"
            },
            required=True
        )
    ]
)


@echo.handle()
async def handle_echo(
    event: ApplicationCommandInteractionEvent,
    content: CommandOption[str]
) -> None:
    """
    添加自动反应.
    Args:
        event (ApplicationCommandInteractionEvent): 事件对象.
        content (StringOption): 要发送的消息内容.
    """
    # 发送延迟响应
    await echo.send_deferred_response()

    content = (
        content.replace("\\n", "\n")
               .replace("\\t", "\t")
               .replace("\\r", "\r")
               .replace("\\\\", "\\")
    )

    # 发送消息
    await echo.finish(message=content, channel=event.channel_id)
