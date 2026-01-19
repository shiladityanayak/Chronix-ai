import discord
from discord.ext import commands
import datetime

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="warn", description="Warn a user")
    @commands.has_permissions(manage_messages=True)
    async def warn(self, ctx, user: discord.Member, *, reason: str = "No reason provided"):
        if user.top_role >= ctx.author.top_role:
            await ctx.send("You cannot warn this user due to role hierarchy.")
            return

        # Log warning to DB
        await self.bot.db.execute(
            "INSERT INTO warns (user_id, guild_id, reason, moderator_id) VALUES ($1, $2, $3, $4)",
            user.id, ctx.guild.id, reason, ctx.author.id
        )

        # Notify
        embed = discord.Embed(title="User Warned", color=discord.Color.orange())
        embed.add_field(name="User", value=f"{user} ({user.id})")
        embed.add_field(name="Reason", value=reason)
        embed.add_field(name="Moderator", value=ctx.author.mention)
        await ctx.send(embed=embed)

        try:
            await user.send(f"You were warned in **{ctx.guild.name}** for: {reason}")
        except discord.Forbidden:
            pass

        # Check warn count for auto-punishment (Deep Feature)
        count = await self.bot.db.fetchval(
            "SELECT COUNT(*) FROM warns WHERE user_id = $1 AND guild_id = $2",
            user.id, ctx.guild.id
        )

        if count >= 3:
            await ctx.send(f"{user.mention} has reached 3 warnings. Consider kicking or muting them.")

    @commands.hybrid_command(name="warnings", description="View warnings for a user")
    @commands.has_permissions(manage_messages=True)
    async def warnings(self, ctx, user: discord.Member):
        rows = await self.bot.db.fetch(
            "SELECT reason, moderator_id, created_at FROM warns WHERE user_id = $1 AND guild_id = $2 ORDER BY created_at DESC",
            user.id, ctx.guild.id
        )

        if not rows:
            await ctx.send(f"{user.display_name} has no warnings.")
            return

        embed = discord.Embed(title=f"Warnings for {user.display_name}", color=discord.Color.yellow())
        for row in rows:
            mod = self.bot.get_user(row['moderator_id'])
            mod_name = mod.name if mod else "Unknown"
            date_str = row['created_at'].strftime("%Y-%m-%d %H:%M:%S")
            embed.add_field(name=f"{date_str} - Mod: {mod_name}", value=row['reason'], inline=False)

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="clearwarns", description="Clear all warnings for a user")
    @commands.has_permissions(administrator=True)
    async def clearwarns(self, ctx, user: discord.Member):
        await self.bot.db.execute("DELETE FROM warns WHERE user_id = $1 AND guild_id = $2", user.id, ctx.guild.id)
        await ctx.send(f"Cleared all warnings for {user.display_name}.")

    @commands.hybrid_command(name="kick", description="Kick a user")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, user: discord.Member, *, reason: str = "No reason provided"):
        if user.top_role >= ctx.author.top_role:
            await ctx.send("You cannot kick this user.")
            return

        await user.kick(reason=reason)
        await ctx.send(f"Kicked {user.mention}. Reason: {reason}")

    @commands.hybrid_command(name="ban", description="Ban a user")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, user: discord.Member, *, reason: str = "No reason provided"):
        if user.top_role >= ctx.author.top_role:
            await ctx.send("You cannot ban this user.")
            return

        await user.ban(reason=reason)
        await ctx.send(f"Banned {user.mention}. Reason: {reason}")

    @commands.hybrid_command(name="timeout", description="Timeout a user (duration in minutes)")
    @commands.has_permissions(moderate_members=True)
    async def timeout(self, ctx, user: discord.Member, minutes: int, *, reason: str = "No reason provided"):
        if user.top_role >= ctx.author.top_role:
            await ctx.send("You cannot timeout this user.")
            return

        duration = datetime.timedelta(minutes=minutes)
        await user.timeout(duration, reason=reason)
        await ctx.send(f"Timed out {user.mention} for {minutes} minutes. Reason: {reason}")

    @commands.hybrid_command(name="unban", description="Unban a user")
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, user_id: str):
        # User might not be in the server, so we take ID
        try:
            user = await self.bot.fetch_user(int(user_id))
            await ctx.guild.unban(user)
            await ctx.send(f"Unbanned {user.mention}.")
        except:
            await ctx.send("User not found or not banned.")

async def setup(bot):
    await bot.add_cog(Moderation(bot))
