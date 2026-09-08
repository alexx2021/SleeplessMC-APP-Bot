import logging

import discord
from discord.ext import commands


log = logging.getLogger(__name__)


class ApplicationView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.lock = bot.application_lock

    @discord.ui.button(
        label="Apply",
        style=discord.ButtonStyle.green,
        custom_id="applications:create",
    )
    async def apply(
        self, interaction: discord.Interaction, _: discord.ui.Button
    ) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        config = self.bot.config
        guild = interaction.guild
        member = interaction.user
        if guild is None or guild.id != config.guild_id or not isinstance(member, discord.Member):
            await interaction.followup.send(
                "This application panel is not valid here.", ephemeral=True
            )
            return

        async with self.lock:
            row = await self.bot.db.execute_fetchall(
                "SELECT channel_id FROM tickets WHERE user_id = ?", (member.id,)
            )
            if row:
                existing = guild.get_channel(row[0][0])
                if existing is not None:
                    await interaction.followup.send(
                        f"You already have an application open in {existing.mention}.",
                        ephemeral=True,
                    )
                    return
                await self.bot.db.execute(
                    "DELETE FROM tickets WHERE user_id = ?", (member.id,)
                )
                await self.bot.db.commit()

            resources = {
                "application category": guild.get_channel(config.application_category_id),
                "application log channel": guild.get_channel(config.app_log_channel_id),
                "general channel": guild.get_channel(config.general_channel_id),
                "rules channel": guild.get_channel(config.rules_channel_id),
                "applicant role": guild.get_role(config.applicant_role_id),
                "member role": guild.get_role(config.member_role_id),
            }
            expected_types = {
                "application category": discord.CategoryChannel,
                "application log channel": discord.TextChannel,
                "general channel": discord.TextChannel,
                "rules channel": discord.TextChannel,
                "applicant role": discord.Role,
                "member role": discord.Role,
            }
            invalid = [
                name
                for name, resource in resources.items()
                if not isinstance(resource, expected_types[name])
            ]
            if invalid:
                await interaction.followup.send(
                    f"Applications are unavailable: missing or invalid {', '.join(invalid)}.",
                    ephemeral=True,
                )
                return

            channel = None
            role_added = False
            try:
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(view_channel=False),
                    member: discord.PermissionOverwrite(view_channel=True),
                }
                channel = await guild.create_text_channel(
                    f"app-{member.name}"[:100],
                    category=resources["application category"],
                    overwrites=overwrites,
                    reason=f"Application opened by {member}",
                )
                await member.add_roles(
                    resources["applicant role"], reason="Application opened"
                )
                role_added = True
                await channel.send(member.mention)
                await channel.send(config.application_prompt)
                await self.bot.db.execute(
                    "INSERT INTO tickets (user_id, channel_id) VALUES (?, ?)",
                    (member.id, channel.id),
                )
                await self.bot.db.commit()
            except Exception:
                await self.bot.db.rollback()
                if role_added:
                    try:
                        await member.remove_roles(
                            resources["applicant role"],
                            reason="Incomplete application setup",
                        )
                    except discord.HTTPException:
                        log.exception("Could not remove applicant role after setup failure")
                if channel is not None:
                    try:
                        await channel.delete(reason="Incomplete application setup")
                    except discord.HTTPException:
                        log.exception("Could not remove incomplete application channel")
                log.exception("Could not create application")
                await interaction.followup.send(
                    "Discord could not create your application. Please contact an administrator.",
                    ephemeral=True,
                )
                return

            await interaction.followup.send(
                f"Your application is ready in {channel.mention}.", ephemeral=True
            )


class Applications(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="setup-applications")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def setup_applications(self, ctx: commands.Context) -> None:
        """Post the persistent application panel."""
        embed = discord.Embed(
            title=f"{self.bot.config.server_name} Applications",
            description="Select **Apply** to open a private application.",
            color=discord.Color.blurple(),
        )
        await ctx.send(embed=embed, view=ApplicationView(self.bot))

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        row = await self.bot.db.execute_fetchall(
            "SELECT channel_id FROM tickets WHERE user_id = ?", (member.id,)
        )
        if not row:
            return
        channel = member.guild.get_channel(row[0][0])
        if channel is not None:
            await channel.delete(reason="Applicant left the guild")
        await self.bot.db.execute("DELETE FROM tickets WHERE user_id = ?", (member.id,))
        await self.bot.db.commit()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Applications(bot))
    bot.add_view(ApplicationView(bot))
