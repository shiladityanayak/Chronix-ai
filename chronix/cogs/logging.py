import discord
from discord.ext import commands
import datetime

class Logging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_log_channel(self, guild_id):
        channel_id = await self.bot.db.fetchval("SELECT log_channel_id FROM guilds WHERE guild_id = $1", guild_id)
        if channel_id:
            return self.bot.get_channel(channel_id)
        return None

    @commands.hybrid_command(name="setlogs", description="Set the channel for logging events")
    @commands.has_permissions(administrator=True)
    async def setlogs(self, ctx, channel: discord.TextChannel):
        # Upsert logic
        exists = await self.bot.db.fetchval("SELECT 1 FROM guilds WHERE guild_id = $1", ctx.guild.id)
        if exists:
            await self.bot.db.execute("UPDATE guilds SET log_channel_id = $1 WHERE guild_id = $2", channel.id, ctx.guild.id)
        else:
            await self.bot.db.execute("INSERT INTO guilds (guild_id, log_channel_id) VALUES ($1, $2)", ctx.guild.id, channel.id)

        await ctx.send(f"✅ Logging channel set to {channel.mention}")

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot or not message.guild:
            return

        channel = await self.get_log_channel(message.guild.id)
        if not channel:
            return

        embed = discord.Embed(title="Message Deleted", color=discord.Color.red())
        embed.add_field(name="Author", value=f"{message.author} ({message.author.id})", inline=False)
        embed.add_field(name="Channel", value=message.channel.mention, inline=False)
        # Content might be empty (embed/image only), handle that
        content = message.content or "*[Image/Embed/No Content]*"
        embed.add_field(name="Content", value=content[:1024], inline=False)
        embed.timestamp = datetime.datetime.utcnow()

        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.bot or not before.guild:
            return

        if before.content == after.content:
            return

        channel = await self.get_log_channel(before.guild.id)
        if not channel:
            return

        embed = discord.Embed(title="Message Edited", color=discord.Color.blue())
        embed.add_field(name="Author", value=f"{before.author} ({before.author.id})", inline=False)
        embed.add_field(name="Channel", value=before.channel.mention, inline=False)
        embed.add_field(name="Before", value=before.content[:1024] or "*[Empty]*", inline=False)
        embed.add_field(name="After", value=after.content[:1024] or "*[Empty]*", inline=False)
        embed.add_field(name="Jump Link", value=f"[Go to Message]({after.jump_url})", inline=False)
        embed.timestamp = datetime.datetime.utcnow()

        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        channel = await self.get_log_channel(member.guild.id)
        if not channel:
            return

        embed = discord.Embed(title="Member Joined", color=discord.Color.green())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="User", value=f"{member} ({member.id})", inline=False)
        embed.add_field(name="Account Created", value=member.created_at.strftime("%Y-%m-%d"), inline=False)
        embed.timestamp = datetime.datetime.utcnow()

        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        channel = await self.get_log_channel(member.guild.id)
        if not channel:
            return

        embed = discord.Embed(title="Member Left", color=discord.Color.dark_red())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="User", value=f"{member} ({member.id})", inline=False)
        embed.timestamp = datetime.datetime.utcnow()

        await channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Logging(bot))
