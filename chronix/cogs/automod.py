import discord
from discord.ext import commands
import re
import datetime

class Automod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Regex to find discord invites
        self.invite_regex = re.compile(r"(?:https?://)?(?:www\.)?(?:discord\.(?:gg|io|me|li)|discord(?:app)?\.com/invite)/([a-zA-Z0-9]+)")
        # Simple spam bucket: 5 messages in 5 seconds
        self._spam_check = commands.CooldownMapping.from_cooldown(5, 5.0, commands.BucketType.user)

    async def is_automod_enabled(self, guild_id):
        return await self.bot.db.fetchval("SELECT automod_enabled FROM guilds WHERE guild_id = $1", guild_id)

    @commands.hybrid_command(name="automod", description="Toggle automod on/off")
    @commands.has_permissions(administrator=True)
    async def automod(self, ctx, state: bool):
        exists = await self.bot.db.fetchval("SELECT 1 FROM guilds WHERE guild_id = $1", ctx.guild.id)
        if exists:
            await self.bot.db.execute("UPDATE guilds SET automod_enabled = $1 WHERE guild_id = $2", state, ctx.guild.id)
        else:
            await self.bot.db.execute("INSERT INTO guilds (guild_id, automod_enabled) VALUES ($1, $2)", ctx.guild.id, state)

        status = "enabled" if state else "disabled"
        await ctx.send(f"🛡️ Automod is now **{status}**.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.guild or message.author.bot:
            return

        if message.author.guild_permissions.administrator:
            return

        if not await self.is_automod_enabled(message.guild.id):
            return

        # 1. Anti-Invite
        if self.invite_regex.search(message.content):
            await message.delete()
            await message.channel.send(f"{message.author.mention}, invites are not allowed here!", delete_after=5)
            # Log it?
            return

        # 2. Anti-Spam
        bucket = self._spam_check.get_bucket(message)
        retry_after = bucket.update_rate_limit()
        if retry_after:
            await message.delete()
            # Mute them for 10 minutes?
            # Let's keep it simple: just delete and warn
            msg = await message.channel.send(f"{message.author.mention}, stop spamming!", delete_after=5)

            # If they are really spamming (retry_after is high), maybe timeout
            if retry_after > 2: # Logic implies they hit it hard
                try:
                    await message.author.timeout(datetime.timedelta(minutes=5), reason="Automod: Spamming")
                except:
                    pass

async def setup(bot):
    await bot.add_cog(Automod(bot))
