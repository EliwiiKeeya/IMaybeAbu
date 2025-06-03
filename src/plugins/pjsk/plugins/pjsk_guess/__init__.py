import asyncio
from io import BytesIO
from typing import Dict, Any

from nonebot import on_type
from nonebot.rule import startswith, fullmatch
from nonebot.adapters.discord import MessageSegment, GuildMessageCreateEvent
from nonebot.adapters.discord.api import File, MessageReference
from nonebot.adapters.discord.api.model import Snowflake

from .lib import LibPjskGuess

channel_guessing_status: Dict[Snowflake, Dict[str, Any]] = {}
guess_data = LibPjskGuess.load_music_name_data()
guess_begin = on_type(GuildMessageCreateEvent, rule=fullmatch(("pjsk猜曲", "pjskguess")))
guess_user_guess = on_type(GuildMessageCreateEvent, rule=startswith("-"))
guess_user_end = on_type(GuildMessageCreateEvent, rule=fullmatch(("结束猜曲", "endpjskguess")))

def channel_guessing_status_checkout_(event: GuildMessageCreateEvent) -> Snowflake:
    """
    检查频道猜曲状态并初始化
    如果频道猜曲状态不存在则创建一个新的状态。
    Args:
        channel_id (Snowflake): 频道ID.
    """
    if event.channel_id not in channel_guessing_status:
        channel_guessing_status[event.channel_id] = {
            "is_guessing": False,
            "is_guessing_sleep_task_handle": None,
            "jacket": None,            
            "music_name": None
        }

    return event.channel_id


@guess_begin.handle()
async def handle_guess_begin(event: GuildMessageCreateEvent) -> None:
    # 获取提示信息
    info_begin = LibPjskGuess.INFO_BEGIN
    info_on_guessing = LibPjskGuess.INFO_ON_GUESSING
    info_end_timeout = LibPjskGuess.INFO_END_TIMEOUT

    # 获取消息引用
    message_id = event.message_id
    message_reference = MessageReference(message_id=message_id)
    message_reference = MessageSegment.reference(message_reference)

    # 检查并获取频道id
    channel_id = channel_guessing_status_checkout_(event)
    if channel_guessing_status[channel_id]["is_guessing"]:
        await guess_begin.finish(message_reference + info_on_guessing)

    # 获取随机封面、裁剪后封面、曲目名称
    jacket, music_name = LibPjskGuess.get_random_jacket()
    jacket_cropped = LibPjskGuess.do_random_crop(jacket)

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
    channel_guessing_status[channel_id]["is_guessing"] = True
    channel_guessing_status[channel_id]["jacket"] = jacket
    channel_guessing_status[channel_id]["music_name"] = music_name

    # 等待用户猜测
    handle = asyncio.create_task(asyncio.sleep(50))
    channel_guessing_status[channel_id]["is_guessing_sleep_task_handle"] = handle
    await handle

    # 发送结束消息并清理状态
    if channel_guessing_status[channel_id]["is_guessing"]:
        channel_guessing_status[channel_id]["jacket"] = None        
        channel_guessing_status[channel_id]["music_name"] = None
        channel_guessing_status[channel_id]["is_guessing"] = False
        channel_guessing_status[channel_id]["is_guessing_sleep_task_handle"] = None
        music_name_edited = LibPjskGuess.get_music_name_for_message(music_name)
        info_end_timeout = f"{info_end_timeout}**{music_name_edited}**"
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
    guess_content = LibPjskGuess.zh_tw_to_zh_cn(guess_content)
    
    # 匹配用户猜测内容
    music_name = LibPjskGuess.get_best_match(guess_content, guess_data)
    music_name_edited = LibPjskGuess.get_music_name_for_message(music_name)
    if music_name == channel_guessing_status[channel_id]["music_name"]:
        # 用户猜测正确
        jacket = channel_guessing_status[channel_id]["jacket"]

        # 取消等待任务
        channel_guessing_status[channel_id]["is_guessing"] = False
        channel_guessing_status[channel_id]["is_guessing_sleep_task_handle"].cancel()

        # 清理频道猜曲状态
        channel_guessing_status[channel_id]["jacket"] = None
        channel_guessing_status[channel_id]["music_name"] = None
        channel_guessing_status[channel_id]["is_guessing_sleep_task_handle"] = None

        # 发送用户猜测正确消息
        info_correct = LibPjskGuess.INFO_CORRECT + music_name_edited
        await guess_user_guess.finish(message_reference + info_correct + jacket)
    else:
        # 发送用户猜测错误信息        
        info_incorrect = f"{LibPjskGuess.INFO_INCORRECT}**{music_name_edited}**哦"
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
    info_end_user = LibPjskGuess.INFO_END_USER
    info_not_on_guessing = LibPjskGuess.INFO_NOT_ON_GUESSING

    # 检查是否在猜曲状态
    if channel_guessing_status[channel_id]["is_guessing"]:
        # 取消等待任务
        channel_guessing_status[channel_id]["is_guessing"] = False
        channel_guessing_status[channel_id]["is_guessing_sleep_task_handle"].cancel()

        # 获取封面和曲目名称
        jacket = channel_guessing_status[channel_id]["jacket"]
        music_name = channel_guessing_status[channel_id]["music_name"]
        music_name_edited = LibPjskGuess.get_music_name_for_message(music_name)

        # 清理频道猜曲状态
        channel_guessing_status[channel_id]["jacket"] = None
        channel_guessing_status[channel_id]["music_name"] = None
        channel_guessing_status[channel_id]["is_guessing_sleep_task_handle"] = None

        # 发送结束消息
        info_end_user += music_name_edited
        await guess_user_end.finish(message_reference + info_end_user + jacket)
    else:
        await guess_user_end.finish(message_reference + info_not_on_guessing)
