from nonebot.adapters.discord import MessageSegment
from nonebot.adapters.discord.api import File, StringOption
from nonebot.adapters.discord.commands import CommandOption, on_slash_command

from .models import PJSKProfileCN, PJSKProfileTW, PJSKProfileJP
from .card import PJSKProfileCard

base_url = ""

profile_tw = PJSKProfileTW(base_url)
profile_jp = PJSKProfileJP(base_url)
profile_cn = PJSKProfileCN(base_url)

cnpjskprofile = on_slash_command(
    name="cnpjskprofile",
    name_localizations={
        "zh-CN": "cn个人信息",
        "zh-TW": "cn個人資訊"
    },
    description="pjsk 简中服个人信息",
    description_localizations={
        "zh-CN": "pjsk 简中服个人信息",
        "zh-TW": "pjsk 简中服個人資訊"
    },
    options=[
        StringOption(
            name="user_id",
            description="用户ID",
            description_localizations={
                "zh-CN": "用户ID",
                "zh-TW": "使用者ID"
            },
            required=True
        )
    ]
)


@cnpjskprofile.handle()
async def handle_cnpjskprofile(
    user_id: CommandOption[str]
) -> None:
    """
    处理用户个人信息请求.
    Args:
        user_id (CommandOption[str]): 用户ID.
    """
    await cnpjskprofile.send_deferred_response()
    profile = profile_cn.get_profile(user_id)
    if profile is not None:
        card = PJSKProfileCard(profile)
        card = File(content=card.getvalue(), filename="card.png")
        card = MessageSegment.attachment(card)
        await cnpjskprofile.finish(card)
    else:
        await cnpjskprofile.finish("获取失败喵")

twpjskprofile = on_slash_command(
    name="twpjskprofile",
    name_localizations={
        "zh-CN": "tw个人信息",
        "zh-TW": "tw個人資訊"
    },
    description="pjsk 繁中服个人信息",
    description_localizations={
        "zh-CN": "pjsk 繁中服个人信息",
        "zh-TW": "pjsk 繁中服個人資訊"
    },
    options=[
        StringOption(
            name="user_id",
            description="用户ID",
            description_localizations={
                "zh-CN": "用户ID",
                "zh-TW": "使用者ID"
            },
            required=True
        )
    ]
)

@twpjskprofile.handle()
async def handle_twpjskprofile(
    user_id: CommandOption[str]
) -> None:
    await twpjskprofile.send_deferred_response()
    profile = profile_tw.get_profile(user_id)
    if profile is not None:
        card = PJSKProfileCard(profile)
        card = File(content=card.getvalue(), filename="card.png")
        card = MessageSegment.attachment(card)
        await twpjskprofile.finish(card)
    else:
        await twpjskprofile.finish("获取失败喵")

jppjskprofile = on_slash_command(
    name="jppjskprofile",
    name_localizations={
        "zh-CN": "jp个人信息",
        "zh-TW": "jp個人資訊"
    },
    description="pjsk 日服个人信息",
    description_localizations={
        "zh-CN": "pjsk 日服个人信息",
        "zh-TW": "pjsk 日服個人資訊"
    },
    options=[
        StringOption(
            name="user_id",
            description="用户ID",
            description_localizations={
                "zh-CN": "用户ID",
                "zh-TW": "使用者ID"
            },
            required=True
        )
    ]
)

@jppjskprofile.handle()
async def handle_jppjskprofile(
    user_id: CommandOption[str]
) -> None:
    await jppjskprofile.send_deferred_response()
    profile = profile_jp.get_profile(user_id)
    if profile is not None:
        card = PJSKProfileCard(profile)
        card = File(content=card.getvalue(), filename="card.png")
        card = MessageSegment.attachment(card)
        await jppjskprofile.finish(card)
    else:
        await jppjskprofile.finish("获取失败喵")
