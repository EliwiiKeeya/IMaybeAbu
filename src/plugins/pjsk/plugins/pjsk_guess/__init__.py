import asyncio
from io import BytesIO
from typing import Dict, Any

from nonebot import on_type
from nonebot.rule import startswith, fullmatch
from nonebot.adapters.discord import MessageSegment, GuildMessageCreateEvent
from nonebot.adapters.discord.api import File, MessageReference
from nonebot.adapters.discord.api.model import Snowflake

from .lib import LibPJSKGuess

channel_guessing_status: Dict[Snowflake, Dict[str, Any]] = {}
guess_data = LibPJSKGuess.load_music_name_data()
guess_begin = on_type(
    GuildMessageCreateEvent,
    rule=fullmatch(("pjsk猜曲", "pjskguess"))
)
guess_user_guess = on_type(
    GuildMessageCreateEvent,
    rule=startswith("-")
)
guess_user_end = on_type(
    GuildMessageCreateEvent,
    rule=fullmatch(("结束猜曲", "結束猜曲", "endpjskguess"))
)

# 猜曲排行需要MongoDB使能
guess_get_ranking = on_type(
    GuildMessageCreateEvent,
    rule=fullmatch(("猜曲排行", "pjskguessranking"))
)


def channel_guessing_status_checkout_(event: GuildMessageCreateEvent) -> Snowflake:
    """
    检查频道猜曲状态并初始化,
    如果频道猜曲状态不存在则创建一个新的状态.
    Args:
        channel_id (Snowflake): 频道ID.
    """
    if event.channel_id not in channel_guessing_status:
        channel_guessing_status[event.channel_id] = {
            "is_guessing": False,
            "is_guessing_sleep_task_handle": None,
            "jacket": None,
            "music_names": None
        }

    return event.channel_id


@guess_begin.handle()
async def handle_guess_begin(event: GuildMessageCreateEvent) -> None:
    # 获取提示信息
    info_begin = LibPJSKGuess.INFO_BEGIN
    info_on_guessing = LibPJSKGuess.INFO_ON_GUESSING
    info_end_timeout = LibPJSKGuess.INFO_END_TIMEOUT

    # 获取消息引用
    message_id = event.message_id
    message_reference = MessageReference(message_id=message_id)
    message_reference = MessageSegment.reference(message_reference)

    # 检查并获取频道id
    channel_id = channel_guessing_status_checkout_(event)
    if channel_guessing_status[channel_id]["is_guessing"]:
        await guess_begin.finish(message_reference + info_on_guessing)
    else:
        channel_guessing_status[channel_id]["is_guessing"] = True

    # 获取随机封面、裁剪后封面、曲目名称
    jacket, music_names = LibPJSKGuess.get_random_jacket()
    jacket_cropped = LibPJSKGuess.do_random_crop(jacket)

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

    # 发送消息并处理状态
    await guess_begin.send(message_reference + info_begin + jacket_cropped)
    channel_guessing_status[channel_id]["jacket"] = jacket
    channel_guessing_status[channel_id]["music_names"] = music_names

    # 等待用户猜测
    handle = channel_guessing_status[channel_id]["is_guessing_sleep_task_handle"]
    if handle is not None and not handle.done():
        handle.cancel()
    handle = asyncio.create_task(asyncio.sleep(60))
    channel_guessing_status[channel_id]["is_guessing_sleep_task_handle"] = handle
    await handle

    # 发送结束消息并清理状态
    if channel_guessing_status[channel_id]["is_guessing"]:
        channel_guessing_status[channel_id]["jacket"] = None
        channel_guessing_status[channel_id]["music_names"] = None
        channel_guessing_status[channel_id]["is_guessing"] = False
        channel_guessing_status[channel_id]["is_guessing_sleep_task_handle"] = None
        music_names_edited = LibPJSKGuess.get_music_names_for_message(
            music_names)
        info_end_timeout = f"{info_end_timeout}**{music_names_edited}**"
        await guess_begin.finish(info_end_timeout + jacket)
    else:
        await guess_begin.finish()


@guess_user_guess.handle()
async def handle_guess_user_guess(event: GuildMessageCreateEvent) -> None:
    # 检查并获取频道id
    channel_id = channel_guessing_status_checkout_(event)
    if channel_guessing_status[channel_id]["is_guessing"] is False:
        await guess_user_guess.finish()

    # 获取消息引用
    message_id = event.message_id
    message_reference = MessageReference(message_id=message_id)
    message_reference = MessageSegment.reference(message_reference)

    # 获取用户猜测内容
    guess_content = event.content[1:]
    guess_content = LibPJSKGuess.convert_text(guess_content)

    # 匹配用户猜测内容
    music_names = LibPJSKGuess.get_best_match(guess_content, guess_data)
    if channel_guessing_status[channel_id]["music_names"] in music_names:
        # 用户猜测正确
        jacket = channel_guessing_status[channel_id]["jacket"]

        # 取消等待任务
        channel_guessing_status[channel_id]["is_guessing"] = False
        channel_guessing_status[channel_id]["is_guessing_sleep_task_handle"] \
            .cancel()

        # 发送用户猜测正确消息
        music_names_edited = LibPJSKGuess.get_music_names_for_message(
            channel_guessing_status[channel_id]["music_names"]
        )
        info_correct = LibPJSKGuess.INFO_CORRECT + music_names_edited
        await guess_user_guess.send(message_reference + info_correct + jacket)

        # 清理频道猜曲状态
        channel_guessing_status[channel_id]["jacket"] = None
        channel_guessing_status[channel_id]["music_names"] = None
        channel_guessing_status[channel_id]["is_guessing_sleep_task_handle"] = None

        # 获取信息
        user_id = event.user_id
        user_name = event.member.nick if event.member.nick else event.author.global_name
        guild_id = str(event.guild_id)
        assert isinstance(user_name, str)

        # 更新用户成绩
        if LibPJSKGuess.IS_MONGO_DB_ENABLED:
            await LibPJSKGuess.update_score_guess_jacket(user_id, user_name, guild_id)

        # 结束猜曲
        await guess_user_guess.finish()
    else:
        # 发送用户猜测错误信息并结束猜曲
        music_name_edited = \
            LibPJSKGuess.get_music_names_for_message(music_names[0])
        info_incorrect = f"{LibPJSKGuess.INFO_INCORRECT}**{music_name_edited}**哦"
        await guess_user_guess.finish(message_reference + info_incorrect)


@guess_user_end.handle()
async def handle_guess_user_end(event: GuildMessageCreateEvent) -> None:
    # 检查并获取频道id
    channel_id = channel_guessing_status_checkout_(event)

    # 获取消息引用
    message_id = event.message_id
    message_reference = MessageReference(message_id=message_id)
    message_reference = MessageSegment.reference(message_reference)

    # 获取提示信息
    info_end_user = LibPJSKGuess.INFO_END_USER
    info_not_on_guessing = LibPJSKGuess.INFO_NOT_ON_GUESSING

    # 检查是否在猜曲状态
    if channel_guessing_status[channel_id]["is_guessing"]:
        # 取消等待任务
        channel_guessing_status[channel_id]["is_guessing"] = False
        channel_guessing_status[channel_id]["is_guessing_sleep_task_handle"] \
            .cancel()

        # 获取封面和曲目名称
        jacket = channel_guessing_status[channel_id]["jacket"]
        music_names = channel_guessing_status[channel_id]["music_names"]
        music_name_edited = LibPJSKGuess.get_music_names_for_message(
            music_names)

        # 清理频道猜曲状态
        channel_guessing_status[channel_id]["jacket"] = None
        channel_guessing_status[channel_id]["music_names"] = None
        channel_guessing_status[channel_id]["is_guessing_sleep_task_handle"] = None

        # 发送结束消息
        info_end_user += music_name_edited
        await guess_user_end.finish(message_reference + info_end_user + jacket)
    else:
        await guess_user_end.finish(message_reference + info_not_on_guessing)


@guess_get_ranking.handle()
async def handle_guess_get_ranking(event: GuildMessageCreateEvent) -> None:
    # 获取消息引用
    message_id = event.message_id
    message_reference = MessageReference(message_id=message_id)
    message_reference = MessageSegment.reference(message_reference)

    # 获取排行榜数据
    guild_id = str(event.guild_id)
    data = await LibPJSKGuess.get_ranking_guess_jacket(guild_id)

    # 构建排行榜信息
    info_ranking = await LibPJSKGuess.gen_ranking_guess_jacket_info(guild_id, data)

    # 构建用户信息
    user_id = event.user_id
    for i, data in enumerate(data):
        if user_id == data["user_id"]:
            info_user = f'\n\n您的排名:{i + 1:>8} 位\n猜中次数:{data["score_guess_jacket"]:>8} 次'
            break
    else:
        info_user = f"\n\n您的排名: 暂无排名"

    await guess_user_end.finish(
        message_reference +
        "```python\n" +
        info_ranking +
        info_user +
        "\n```"
    )
