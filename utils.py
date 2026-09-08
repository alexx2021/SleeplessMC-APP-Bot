import aiosqlite
import discord


async def migrate_tickets(db: aiosqlite.Connection) -> None:
    await db.execute("BEGIN IMMEDIATE")
    try:
        exists = await db.execute_fetchall(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'tickets'"
        )
        rows = []
        if exists:
            rows = await db.execute_fetchall(
                "SELECT rowid, user_id, channel_id FROM tickets "
                "WHERE user_id > 0 AND channel_id > 0 ORDER BY rowid DESC"
            )

        await db.execute("DROP TABLE IF EXISTS tickets_new")
        await db.execute(
            "CREATE TABLE tickets_new ("
            "user_id INTEGER NOT NULL UNIQUE, channel_id INTEGER NOT NULL UNIQUE)"
        )
        used_users: set[int] = set()
        used_channels: set[int] = set()
        newest = []
        for _, user_id, channel_id in rows:
            if user_id not in used_users and channel_id not in used_channels:
                newest.append((user_id, channel_id))
                used_users.add(user_id)
                used_channels.add(channel_id)
        await db.executemany(
            "INSERT INTO tickets_new (user_id, channel_id) VALUES (?, ?)",
            reversed(newest),
        )
        if exists:
            await db.execute("DROP TABLE tickets")
        await db.execute("ALTER TABLE tickets_new RENAME TO tickets")
        await db.commit()
    except Exception:
        await db.rollback()
        raise


async def get_or_fetch_member(
    guild: discord.Guild, member_id: int
) -> discord.Member | None:
    member = guild.get_member(member_id)
    if member is not None:
        return member
    try:
        return await guild.fetch_member(member_id)
    except discord.NotFound:
        return None


async def get_or_fetch_channel(
    guild: discord.Guild, channel_id: int
) -> discord.abc.GuildChannel | None:
    channel = guild.get_channel(channel_id)
    if channel is not None:
        return channel
    try:
        return await guild.fetch_channel(channel_id)
    except discord.NotFound:
        return None


async def get_or_fetch_role(guild: discord.Guild, role_id: int) -> discord.Role | None:
    role = guild.get_role(role_id)
    if role is not None:
        return role
    return next((role for role in await guild.fetch_roles() if role.id == role_id), None)
