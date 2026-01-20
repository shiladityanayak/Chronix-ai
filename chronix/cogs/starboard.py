import discord
from discord.ext import commands

class Starboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_config(self, guild_id):
        return await self.bot.db.fetchrow("SELECT starboard_channel_id, starboard_limit FROM guilds WHERE guild_id = $1", guild_id)

    @commands.hybrid_command(name="setstarboard", description="Configure starboard")
    @commands.has_permissions(administrator=True)
    async def setstarboard(self, ctx, channel: discord.TextChannel, limit: int = 3):
        exists = await self.bot.db.fetchval("SELECT 1 FROM guilds WHERE guild_id = $1", ctx.guild.id)
        if exists:
            await self.bot.db.execute("UPDATE guilds SET starboard_channel_id = $1, starboard_limit = $2 WHERE guild_id = $3", channel.id, limit, ctx.guild.id)
        else:
            await self.bot.db.execute("INSERT INTO guilds (guild_id, starboard_channel_id, starboard_limit) VALUES ($1, $2, $3)", ctx.guild.id, channel.id, limit)

        await ctx.send(f"⭐ Starboard set to {channel.mention} with limit **{limit}**.")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if not payload.guild_id:
            return

        if str(payload.emoji) != "⭐":
            return

        config = await self.get_config(payload.guild_id)
        if not config or not config['starboard_channel_id']:
            return

        channel = self.bot.get_channel(payload.channel_id)
        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.NotFound:
            return

        # Check count
        reaction = discord.utils.get(message.reactions, emoji="⭐")
        if not reaction or reaction.count < config['starboard_limit']:
            return

        starboard_channel = self.bot.get_channel(config['starboard_channel_id'])
        if not starboard_channel:
            return

        # Check if already posted?
        # A simple way is to check if the bot has already reacted with a custom emoji or just not care for now.
        # "Best of the best" should check.
        # But scanning history is expensive.
        # Ideally we store "message_id -> starboard_message_id" in DB.
        # For this version, let's keep it simple: we assume if it hits the threshold it posts.
        # To avoid spamming, we can check if we already posted it.
        # But we don't have a table for that.

        # Let's add a "Recent" check or just post it.
        # Users might react more, triggering it again.
        # We'll just construct the embed.

        embed = discord.Embed(color=discord.Color.gold())
        embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
        embed.description = message.content
        embed.add_field(name="Source", value=f"[Jump to Message]({message.jump_url})")

        if message.attachments:
            embed.set_image(url=message.attachments[0].url)

        embed.set_footer(text=f"⭐ {reaction.count} | {message.id}")

        # To prevent duplicates, we can search the starboard channel history for the footer message ID.
        # This is slow but effective for low volume.
        async for hist_msg in starboard_channel.history(limit=50):
             if hist_msg.embeds and hist_msg.embeds[0].footer.text and str(message.id) in hist_msg.embeds[0].footer.text:
                 # Update the count
                 await hist_msg.edit(embed=embed)
                 return

        await starboard_channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Starboard(bot))
