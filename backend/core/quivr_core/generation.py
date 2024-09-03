import ast
from typing import Optional, List
from langchain_core.tools import tool
try:
    from swibots import (
        Community,
        Channel,
        Group,
        Embed,
        EmbeddedMedia,
        EmbedInlineField,
        RolePermission,
        RoleMember,
        InlineKeyboardButton, InlineMarkup
    )
    from swibots.errors import NetworkError
    from swibots import Client

    bot = Client(
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6MTAyMTMsImlzX2JvdCI6dHJ1ZSwiYWN0aXZlIjp0cnVlLCJpYXQiOjE3MTM2NzIzNzUsImV4cCI6MjM0NDgyNDM3NX0.TiZLHCg5UXA6Hq89aVbwVuZUjGRzAemYC8Ih2gRzulo"
    )
except ImportError as r:
    print(r)
    bot = None

from langchain.pydantic_v1 import BaseModel

@tool
async def update_community_description(description: str, community_id: str):
    """set new community description for the current community.
    Call this only, if user asks for updating the community description.

    Args:
        description: str
        community_id: str: community id
    """
    community = await bot.get_community(community_id)
    community.description = description
    await bot.update_community(community=community)
    return (
        "Inform the user that the community description has been updated successfully."
    )


@tool
async def get_channel_list(community_id: str):
    """get all the channels in the current community. It provides list of all channels in current community

    Args:
        community_id: str: community id
    """
    return await bot.get_all_channels(community_id=community_id)


@tool
async def get_group_list(community_id: str):
    """get all the groups in the current community. It provides a list of all groups

    Args:
        community_id: str: community id
    """
    return await bot.get_all_groups(community_id=community_id)


@tool
async def create_channel(name: str, community_id: str, emoji: str):
    """creates a new channel in the current community.
    IMPORTANT: *Call this only, if user clearly states to create a new channel*.

    Args:
        name: str: channel name
        community_id: str: community id
        emoji: str: channel emoji
    """
    return await bot.create_channel(
        Channel(
            community_id=community_id,
            name=name,
            is_public=True,
            enabled_free=True,
            enabled_public=True,
            icon=emoji
        )
    )

@tool
async def create_group(name: str, community_id: str, emoji: str):
    """creates a new group in the current community.
    IMPORTANT: *Call this only, if user clearly states to create a new group*.

    Args:
        name: str: group name
        community_id: str: community id
        emoji: str: group emoji
    """
    return await bot.create_group(
        Group(
            community_id=community_id,
            name=name,
            is_public=True,
            enabled_free=True,
            enabled_public=True,
            icon=emoji,
            allowed_content=["GIFS"]
        )
    )


@tool
async def get_channel_group_history(channel_group_id: str, community_id: str):
    """get the history of the channel or group.
    This function can be called with the addition of `get_all_channels` or `get_all_groups` to get the channel or group histories through the entire communtity.

    Args:
        channel_group_id: str: channel id or group id
        community_id: str: community id
    """
    try:
        channel = await bot.get_channel(id=channel_group_id)
        return await bot.get_channel_chat_history(
            channel_id=channel_group_id, community_id=community_id
        )
    except Exception as er:
        group = await bot.get_group(id=channel_group_id)
        return await bot.get_group_chat_history(
            group_id=channel_group_id, community_id=community_id
        )


@tool
async def get_community_detail(community_id: str):
    """get the detail of the community, call this function only to get the latest information of the community

    Args:
        community_id: str: community id
    """
    community = await bot.get_community(community_id)
    return community


@tool
async def delete_channel(channel_id: str, community_id: str):
    """delete the channel from the community. Call this function only if user ask to delete a channel

    Args:
        channel_id: str: channel id
        community_id: str: community id
    """
    return await bot.delete_channel(channel_id)


@tool
async def delete_group(group_id: str, community_id: str):
    """delete the group from the community. Call this function only if user ask to delete a group

    Args:
        group_id: str: group id
        community_id: str: community id
    """
    return await bot.delete_group(group_id)


@tool
async def get_community_chat_analysis(community_id: str):
    """get the analysis of the community chat, This is a rare call, which will fetch all channels and groups and iterate through them to get the message histories.
    Dont call this function frequently, as it will take time to get the analysis of the community chat.
    This function can be called to get the analysis of the community chat

    Args:
       community_id: str: community id
    """
    details = {}
    for channel in await bot.get_all_channels(community_id):
        details[channel] = await bot.get_channel_chat_history(
            channel.id, community_id, page_limit=10
        )
    for group in await bot.get_all_groups(community_id):
        details[group] = await bot.get_group_chat_history(
            group.id, community_id, page_limit=10
        )
    return details


@tool
async def get_bots_in_community(community_id: str):
    """get all the bots in the community

    Args:
        community_id: str: community id
    """
    output = await bot.list_bots_in_community(community_id=community_id)
    return output


@tool
async def delete_all_messages(channel_group_id: str, community_id: str):
    """delete all the messages in the channel or group
    IMPORTANT: This function will delete all the messages in the channel or group. Call this function only if user clearly states to delete all the messages in the channel or group.

    Args:
        channel_group_id: str: channel id or group id
        community_id: str: community id
    """
    try:
        channel = await bot.get_channel(id=channel_group_id)
        request = bot.get_channel_chat_history
    except Exception as er:
        group = await bot.get_group(id=channel_group_id)
        request = bot.get_group_chat_history
    count = 0
    while messages := (
        await request(
            channel_group_id,
            community_id=community_id,
        )
    ).messages:
        for message in messages:
            await message.delete()
            count += 1

    return f"Deleted {count} messages"


@tool
async def delete_message(message_id: int):
    """delete a message from the channel or group
    IMPORTANT: This function will delete the message in the channel or group. Call this function only if user clearly states to delete the message in the channel or group.

    Args:
        message_id: int: message id
    """
    await bot.delete_message(message_id)
    return f"Deleted message with id {message_id}"


@tool
async def get_commands_in_channel_group(
    community_id: str, channel_id: str = None, group_id: str = None
):
    """get all the active commands in the channel or group

    Args:
        community_id: str: community id
        channel_id: str: channel id
        group_id: str: group id
    """
    return await bot.get_active_commands(
        community_id=community_id, channel_id=channel_id, group_id=group_id
    )


@tool
async def add_bot_to_community(community_id: str, username: str):
    """add a bot to the community from the bot username.

    Args:
        community_id: str: community id
        username: str: bot username
    """
    try:
        response = await bot.community_service.communities.client.post(
            "/v1/community/bots",
            data={"communityId": community_id, "username": username},
        )
        return response.data

    except Exception as er:
        return "Failed to add bot to the community: {}".format(er)


@tool
async def create_role(
    community_id: str,
    name: str,
    add_members: Optional[bool] = None,
    add_roles: Optional[bool] = None,
    send_messages: Optional[bool] = None,
    ban_users: Optional[bool] = None,
    change_info: Optional[bool] = None,
    delete_messages: Optional[bool] = None,
    dm_permission: Optional[bool] = None,
    pin_messages: Optional[bool] = None,
    restrict_messaging: Optional[bool] = None,
    can_deduct_xp: Optional[bool] = None,
):
    """create a new role in the community

    Args:
        community_id: str: community id
        name: str: role name

    """
    role = await bot.add_role(community_id=community_id, name=name, colour="#000000")
    permissionBool = await bot.add_permission(
        RolePermission(
            add_members=add_members,
            add_roles=add_roles,
            send_messages=send_messages,
            ban_users=ban_users,
            change_info=change_info,
            delete_messages=delete_messages,
            dm_permission=dm_permission,
            pin_messages=pin_messages,
            restrict_messaging=restrict_messaging,
            can_deduct_xp=can_deduct_xp,
            role_id=role.id,
        )
    )
    return role, permissionBool


@tool
async def add_user_to_role(community_id: str, user_id: int, role_id: int):
    """add a user to the role in the community

    Args:
        community_id: str: community id
        user_id: int: user id
        role_id: int: role id
    """
    added = await bot.add_member_to_role(
        community_id=community_id, member_id=user_id, role_ids=[role_id]
    )
    if added:
        return "User added to the role successfully"
    return "Failed to add user to the role"


@tool
async def get_roles_in_community(community_id: str):
    """get all the roles in the community

    Args:
        community_id: str: community id
    """
    return await bot.get_roles(community_id=community_id)


@tool
async def ai_generate_image(prompt: str):
    """generate image from the prompt
    
    Args:
        prompt: str: prompt for the image generation
    """
    # TODO: AI GENERATE IMAGE
    return

@tool
async def send_message(
    community_id: str,
    channel_id: str = None,
    group_id: str = None,
    message: str = None,
    media_id: Optional[int] = None,
    buttons: str = None
):
    """Send a message to the channel or group. It will send the message to the channel or group with the media and buttons if provided.
   
    Args: 
        community_id: str: community id
        channel_id: str: channel id
        group_id: str: group id
        message: str: message to send
        media_id: int: media id
        buttons: str: buttons to send
        example: '[[
            {"text": "Column 1", "callback_data": "row1"},
            {"text": "Column 2", "url": "https://example.com"}
        ], [{"text": "Row 2", "callback_data": "row2"}]]'
    """
    markup = None
    if buttons:
        buttons = ast.literal_eval(buttons)
    if buttons and isinstance(buttons, list):
        markup = InlineMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=button[0] if isinstance(button, list) else button["text"],
                        callback_data=button[0] if isinstance(button, list) else button.get("callback_data"),
                        url=button[0] if isinstance(button, list) else button.get("url"),
                    )
                    for button in row
                ]
                for row in buttons
            ]
        )
    media_info = None
    if media_id:
        media_info = await bot.get_media(media_id)

    await bot.send_message(
        community_id=community_id,
        channel_id=channel_id,
        group_id=group_id,
        message=message,
        inline_markup=markup,
        cached_media_info=media_info
    )
    return "Message sent successfully"

@tool
async def get_user_info(username: str):
    """get the user information from the username, can be used to get the user id, profile info from username

    Args:
        username: str: username
    """
    return await bot.get_user(username=username)

@tool
async def get_community_guidelines(community_id: str):
    """get the community guidelines

    Args:
        community_id: str: community id
    """
    data = await bot.community_service.communities.client.get("/v1/community/guidelines/all/{}".format(community_id))
    return data.data


@tool
async def get_community_details(id: str = None,
                                username: str = None):
    """get the community details from the id or username
    
    Args:
        id: str: community id
        username: str: community username
    """
    return await bot.get_community(id=id, username=username)

