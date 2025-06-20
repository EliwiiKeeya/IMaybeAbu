import asyncio
from ast import literal_eval
from typing import TypedDict, List, Dict, Union, Optional


from nonebot import on_type, get_adapter
from nonebot.adapters.discord import (
    Bot,
    Adapter,
    MessageSegment,
    GuildMessageCreateEvent,
    GuildMessageReactionAddEvent,
    MessageComponentInteractionEvent,
    ApplicationCommandInteractionEvent
)
from nonebot.adapters.discord.api import (
    User,
    UserOption,
    MessageGet,
    MessageFlag,
    ComponentEmoji,
    SubCommandOption,
    ComponentType,
    SelectMenu,
    SelectOption,
    API_HANDLERS
)
from nonebot.adapters.discord.commands import (
    CommandOption,
    on_slash_command,
)
from nonebot.adapters.discord.api.model import Snowflake
from nonebot.adapters.discord.message import CustomEmojiSegment

create_reaction = API_HANDLERS["create_reaction"]
delete_own_reaction = API_HANDLERS["delete_own_reaction"]
get_guild_member = API_HANDLERS["get_guild_member"]
get_channel_messages = API_HANDLERS["get_channel_messages"]


class AddReactSessionStatus(TypedDict):
    """
    增加反应会话状态字典类型.
    Attributes:
        user_id (Snowflake): 用户ID.
        emoji (Optional[CustomEmojiSegment | str]): 表情符号消息或字符串表示的表情符号.
        trigger_react_received (asyncio.Event): 一旦 wait 被触发，表示用户已添加反应.
    """
    user_id: Snowflake
    emoji: Optional[CustomEmojiSegment | str]
    trigger_react_received: asyncio.Event


class DeleteReactSessionStatus(TypedDict):
    """
    删除反应会话状态字典类型.
    Attributes:
        user_id (Snowflake): 用户ID.        
        trigger_react_received (asyncio.Event): 一旦 wait 被触发，表示用户已添加反应.
    """
    user_id: Snowflake
    trigger_react_received: asyncio.Event


pool_react_tasks: Dict[
    Snowflake,  # 群组ID
    Dict[
        Snowflake,  # 用户ID
        List[Union[str, MessageSegment]]  # 反应列表
    ]
] = {}

pool_add_react_sessions: Dict[
    Snowflake,  # 群组ID
    Dict[
        Snowflake,  # 操作者ID
        Dict[
            Snowflake,  # 消息ID
            AddReactSessionStatus
        ]
    ]
] = {}

pool_delete_react_sessions: Dict[
    Snowflake,  # 群组ID
    Dict[
        Snowflake,  # 操作者ID
        Dict[
            Snowflake,  # 消息ID
            DeleteReactSessionStatus
        ]
    ]
] = {}


# 命令响应器
react = on_slash_command(
    name="react",
    description="自动反应",
    description_localizations={
        "zh-CN": "自动反应",
        "zh-TW": "自動反應"
    },
    options=[
        SubCommandOption(
            name="add",
            description="为一个用户添加一个自动反应",
            description_localizations={
                "zh-CN": "为一个用户添加一个自动反应",
                "zh-TW": "為一個使用者添加一個自動反應"
            },
            options=[
                UserOption(
                    name="user",
                    description="成员",
                    description_localizations={
                        "zh-CN": "成员",
                        "zh-TW": "成員"
                    },
                    required=True
                )
            ]
        ),
        SubCommandOption(
            name="remove",
            description="为一个用户移除一个自动反应",
            description_localizations={
                "zh-CN": "为一个用户移除一个自动反应",
                "zh-TW": "為一個使用者移除一個自動反應"
            },
            options=[
                UserOption(
                    name="user",
                    description="成员",
                    description_localizations={
                        "zh-CN": "成员",
                        "zh-TW": "成員"
                    },
                    required=True
                )
            ]
        )
    ]
)

# 其他响应器
react_service = on_type(types=GuildMessageCreateEvent)
react_add_sessions = on_type(types=GuildMessageReactionAddEvent)
react_delete_sessions = on_type(types=MessageComponentInteractionEvent)


@react.handle_sub_command("add")
async def handle_react_add(event: ApplicationCommandInteractionEvent, user: CommandOption[User]) -> None:
    """
    添加自动反应.
    Args:
        event (ApplicationCommandInteractionEvent): 事件对象.
        user (CommandOption[User]): 成员选项.
    """
    # 发送延迟响应
    await react.send_deferred_response()

    # 获取群组ID, 操作者ID和用户ID
    guild_id = event.guild_id
    operator_id = event.member.user.id
    user_id = user.id

    # 检查群组是否具有状态, 没有则创建空状态
    global pool_add_react_sessions, pool_react_tasks
    if pool_add_react_sessions.get(guild_id) is None:
        pool_add_react_sessions[guild_id] = {}
    if pool_react_tasks.get(guild_id) is None:
        pool_react_tasks[guild_id] = {}

    # 检查操作者是否具有会话状态, 没有则创建空会话
    if pool_add_react_sessions[guild_id].get(operator_id) is None:
        pool_add_react_sessions[guild_id][operator_id] = {}

    # 建立会话
    session = await react.send_followup_msg(
        "请将期望的反应添加到此消息下.",
        flags=MessageFlag.EPHEMERAL
    )

    # 初始化并更新状态
    timer = asyncio.create_task(asyncio.sleep(30))
    trigger = asyncio.Event()
    pool_add_react_sessions[guild_id][operator_id][session.id] = {
        "user_id": user_id,
        "emoji": None,
        "trigger_react_received": trigger
    }

    # 等待用户添加反应
    await asyncio.wait(
        [trigger.wait(), timer],
        return_when=asyncio.FIRST_COMPLETED
    )

    # 如果操作者添加了反应, 则会触发事件将定时器取消
    if trigger.is_set():
        # 获取表情符号
        emoji = pool_add_react_sessions[guild_id][operator_id][session.id]["emoji"]
        assert emoji is not None, "用户添加反应后, 表情符号必定非空."

        # 检查用户是否具有反应任务, 没有则创建空任务
        if pool_react_tasks[guild_id].get(user_id) is None:
            pool_react_tasks[guild_id][user_id] = []

        # 检查反应是否已存在于用户任务中, 如果存在则返回消息
        elif emoji in pool_react_tasks[guild_id][user_id]:
            await react.edit_followup_msg(
                session.id,
                "反应 " + emoji +
                " 已存在于自动为" + MessageSegment.mention_user(user_id) +
                "添加的反应中."
            )
            await react_add_sessions.finish()

        # 添加反应到用户任务中
        pool_react_tasks[guild_id][user_id].append(emoji)

        # 释放会话
        pool_add_react_sessions[guild_id][operator_id].pop(session.id)

        # 发送成功消息
        msg_user = MessageSegment.mention_user(user_id)
        await react.edit_followup_msg(
            session.id,
            "将自动为" + msg_user + "添加反应: " + emoji
        )

    # not trigger.is_set()
    else:
        pool_add_react_sessions[guild_id][operator_id].pop(session.id)
        await react.edit_followup_msg(session.id, f"请求超时, 请重试.")

    # 结束响应器
    await react.finish()


@react.handle_sub_command("remove")
async def handle_react_remove(
    bot: Bot,
    event: ApplicationCommandInteractionEvent,
    user: CommandOption[User]
) -> None:
    """
    移除自动反应.
    Args:
        event (ApplicationCommandInteractionEvent): 事件对象.
    """
    # 发送延迟响应
    await react.send_deferred_response()

    # 获取适配器
    adapter = get_adapter("Discord")
    assert isinstance(adapter, Adapter), "适配器必须是Discord适配器."

    # 获取群组ID, 操作者ID和用户ID
    guild_id = event.guild_id
    operator_id = event.member.user.id
    user_id = user.id
    member = await get_guild_member(adapter, bot, guild_id, user_id)

    # 获取用户名
    if member.nick is not None:
        user_name = member.nick
    elif member.user.global_name is not None:
        user_name = member.user.global_name
    else:
        user_name = member.user.username
    user_name = member.user.username if user_name is None else user_name
    assert isinstance(user_name, str), "用户名称必须是字符串."

    # 检查群组是否具有状态, 没有则创建空状态
    global pool_delete_react_sessions, pool_react_tasks
    if pool_react_tasks.get(guild_id) is None:
        pool_react_tasks[guild_id] = {}
    if pool_delete_react_sessions.get(guild_id) is None:
        pool_delete_react_sessions[guild_id] = {}

    # 获取任务, 若无任务则结束事件
    tasks = pool_react_tasks[guild_id].get(user_id)
    if tasks is None:
        await react.finish("没有为" + user_name + "设置自动添加的反应.")

    # 检查操作者是否具有会话状态, 没有则创建空会话
    if pool_delete_react_sessions[guild_id].get(operator_id) is None:
        pool_delete_react_sessions[guild_id][operator_id] = {}

    # 构造会话的选择菜单和按钮
    options: List[SelectOption] = [SelectOption(label="选择全部", value="all")]
    for emoji in tasks:
        if isinstance(emoji, MessageSegment):
            options.append(
                SelectOption(
                    label=f"{emoji.data['name']}",
                    value=str(
                        {
                            'name': emoji.data['name'],
                            'emoji_id': emoji.data['id']
                        }
                    ),
                    emoji=ComponentEmoji(
                        id=emoji.data["id"],
                        name=emoji.data["name"]
                    )
                )
            )
        else:
            assert isinstance(emoji, str), "表情符号必须是字符串或MessageSegment."
            options.append(
                SelectOption(
                    label=emoji,
                    value=emoji,
                    emoji={"name": emoji}
                )
            )

    # 初始化并建立会话
    select = MessageSegment.component(
        SelectMenu(
            type=ComponentType.StringSelect,
            custom_id="react_delete_select",
            options=options,
            placeholder="请选择要删除的表情符号",
            min_values=1,
            max_values=len(options)
        )
    )
    session = await react.send_followup_msg(
        "请选择你要删除的表情符号." + select
    )

    # 初始化并更新状态
    timer = asyncio.create_task(asyncio.sleep(30))
    trigger = asyncio.Event()
    pool_delete_react_sessions[guild_id][operator_id][session.id] = {
        "user_id": user_id,
        "trigger_react_received": trigger
    }

    # 等待用户添加反应
    await asyncio.wait(
        [trigger.wait(), timer],
        return_when=asyncio.FIRST_COMPLETED
    )

    # 超时处理
    if not trigger.is_set():
        pool_delete_react_sessions[guild_id][operator_id].pop(session.id)
        await react.edit_followup_msg(session.id, f"请求超时, 请重试.")

    # 结束响应器
    await react.finish()


@react_service.handle()
async def handle_react_service(bot: Bot, event: GuildMessageCreateEvent) -> None:
    """
    自动反应服务处理.
    Args:
        event (GuildMessageReactionAddEvent): 事件对象.
    """
    # 获取适配器
    adapter = get_adapter("Discord")
    assert isinstance(adapter, Adapter), "适配器必须是Discord适配器."

    # 获取群组ID, 频道ID, 消息ID和用户ID
    guild_id = event.guild_id
    channel_id = event.channel_id
    message_id = event.message_id
    user_id = event.user_id

    # 检查群组是否具有全局状态, 没有则创建空状态
    global pool_react_tasks
    if pool_react_tasks.get(guild_id) is None:
        pool_react_tasks[guild_id] = {}

    # 检查用户是否具有反应任务, 没有则结束事件
    if pool_react_tasks[guild_id].get(user_id) is None:
        await react_service.finish()

    # 获取上次消息
    last_message: MessageGet = (
        await get_channel_messages(
            adapter,
            bot,
            channel_id,
            before=message_id,
            limit=1,
        )
    ).pop()

    # 如果上次消息的作者ID与用户ID相同, 则删除自己的反应
    if user_id == last_message.author.id:
        for emoji in pool_react_tasks[guild_id][user_id]:
            if isinstance(emoji, MessageSegment):
                name = emoji.data["name"]
                emoji_id = emoji.data["id"]

            # 如果是字符串, 则直接使用
            else:
                name = emoji
                emoji_id = None

            # 删除自己的反应
            try:
                await delete_own_reaction(adapter, bot, channel_id, last_message.id, name, emoji_id)
            except Exception as e:
                # 如果删除反应失败, 则打印错误并继续
                print(
                    f"Failed to delete reaction {emoji} from message {last_message.id}: {e}"
                )

    # 遍历所有表情符号
    for emoji in pool_react_tasks[guild_id][user_id]:
        if isinstance(emoji, MessageSegment):
            name = emoji.data["name"]
            emoji_id = emoji.data["id"]

        # 如果是字符串, 则直接使用
        else:
            name = emoji
            emoji_id = None

        # 创建反应
        try:
            await create_reaction(adapter, bot, channel_id, message_id, name, emoji_id)
        except Exception as e:
            # 如果添加反应失败, 则打印错误并继续
            print(
                f"Failed to add reaction {emoji} to message {message_id}: {e}"
            )

    # 结束响应器
    await react_service.finish()


@react_add_sessions.handle()
async def handle_react_add_sessions(event: GuildMessageReactionAddEvent) -> None:
    """
    增加反应会话处理.
    Args:
        event (GuildMessageReactionAddEvent): 事件对象.
    """
    # 获取群组ID, 操作者ID和消息ID
    guild_id = event.guild_id
    operator_id = event.user_id
    message_id = event.message_id

    # 检查群组是否具有全局状态, 没有则创建空状态
    global pool_add_react_sessions, pool_react_tasks
    if pool_add_react_sessions.get(guild_id) is None:
        pool_add_react_sessions[guild_id] = {}

    # 检查操作者是否具有会话状态, 没有则结束事件
    if pool_add_react_sessions[guild_id].get(operator_id) is None:
        await react_add_sessions.finish()

    # 根据消息ID匹配用户ID
    user_id = pool_add_react_sessions[guild_id][operator_id].get(message_id)
    if user_id is None:
        await react_add_sessions.finish()  # 无匹配结果, 结束事件

    # 创建表情符号
    emoji: Union[str, MessageSegment]
    if event.emoji.name and event.emoji.id is not None:
        emoji = MessageSegment.custom_emoji(
            name=event.emoji.name,
            emoji_id=event.emoji.id
        )
    else:
        assert event.emoji.name is not None, "自定义表情符号一定具有名称和ID."
        emoji = event.emoji.name

    # 更新会话状态
    pool_add_react_sessions[guild_id][operator_id][message_id]["emoji"] = emoji
    pool_add_react_sessions[guild_id][operator_id][message_id]["trigger_react_received"] \
        .set()

    # 结束响应器
    await react_add_sessions.finish()


@react_delete_sessions.handle()
async def handle_react_delete_sessions(event: MessageComponentInteractionEvent) -> None:
    """
    删除反应会话处理.
    Args:
        event (MessageComponentInteractionEvent): 事件对象.
    """
    # 获取群组ID, 操作者ID和消息ID
    guild_id = event.guild_id
    operator_id = event.member.user.id
    session_id = event.message.id

    # 检查群组是否具有全局状态, 没有则创建空状态
    global pool_delete_react_sessions, pool_react_tasks
    if pool_delete_react_sessions.get(guild_id) is None:
        pool_delete_react_sessions[guild_id] = {}

    # 检查操作者是否具有会话状态, 没有则结束事件
    if pool_delete_react_sessions[guild_id].get(operator_id) is None:
        await react_delete_sessions.finish()

    # 获取状态
    status = pool_delete_react_sessions[guild_id][operator_id].get(session_id)
    assert status is not None, "会话状态必非空."

    # 获取用户ID
    user_id = status["user_id"]

    # 构造提及用户消息
    msg_user = MessageSegment.mention_user(user_id)

    # 删除所有反应
    if "all" in event.data.values:
        pool_react_tasks[guild_id].pop(user_id, None)
        await react_delete_sessions.finish(
            "已为" + msg_user + "删除所有自动添加的反应."
        )

    # 删除指定反应
    else:
        emojis: List[CustomEmojiSegment | str] = []
        for emoji in event.data.values:
            try:
                emojis.append(
                    MessageSegment.custom_emoji(**literal_eval(emoji))
                )
            except:
                emojis.append(emoji)

        for emoji in emojis:
            pool_react_tasks[guild_id][user_id].remove(emoji)

        # 如果无剩余反应, 则删除用户任务
        if pool_react_tasks[guild_id][user_id] == []:
            pool_react_tasks[guild_id].pop(user_id, None)

    msg_emoji = " ".join([str(emoji) for emoji in emojis])
    await react_delete_sessions.send(
        "已为" + msg_user + "删除自动添加的反应: " + msg_emoji
    )

    # 释放会话
    pool_delete_react_sessions[guild_id][operator_id][session_id]["trigger_react_received"] \
        .set()
    pool_delete_react_sessions[guild_id][operator_id].pop(session_id, None)

    # 结束会话状态
    await react_delete_sessions.finish()
