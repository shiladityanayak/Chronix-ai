import discord
from discord.ext import commands
import random
import math
from collections import defaultdict
import time

class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._cd = commands.CooldownMapping.from_cooldown(1, 60.0, commands.BucketType.user)

    async def get_user_data(self, user_id):
        # Fetch user, create if not exists
        row = await self.bot.db.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
        if row is None:
            await self.bot.db.execute("INSERT INTO users (user_id) VALUES ($1)", user_id)
            # Return default values mimicking the row
            return {"user_id": user_id, "balance": 0, "bank": 0, "xp": 0, "level": 1}
        return row

    def get_ratelimit(self, message):
        bucket = self._cd.get_bucket(message)
        return bucket.update_rate_limit()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        # Check cooldown (1 minute)
        retry_after = self.get_ratelimit(message)
        if retry_after:
            return

        # Give XP
        xp_gain = random.randint(15, 25)

        # We need to fetch current data first to check for level up
        user_data = await self.get_user_data(message.author.id)
        current_xp = user_data['xp']
        current_lvl = user_data['level']

        new_xp = current_xp + xp_gain

        # Formula: XP needed for next level = 50 * (Current_Level^2) + (50 * Current_Level)
        # Actually simpler standard formula: Total XP needed for level N = 50 * N^2
        # Let's check if new_xp >= 50 * ((current_lvl + 1) ** 2)

        next_level_xp = 50 * ((current_lvl + 1) ** 2)

        if new_xp >= next_level_xp:
            new_lvl = current_lvl + 1
            await self.bot.db.execute(
                "UPDATE users SET xp = $1, level = $2 WHERE user_id = $3",
                new_xp, new_lvl, message.author.id
            )
            await message.channel.send(f"🎉 {message.author.mention} has leveled up to **Level {new_lvl}**!")
        else:
            await self.bot.db.execute(
                "UPDATE users SET xp = $1 WHERE user_id = $2",
                new_xp, message.author.id
            )

    @commands.hybrid_command(name="rank", description="Check your rank and level")
    async def rank(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        data = await self.get_user_data(user.id)

        xp = data['xp']
        lvl = data['level']

        # Calculate progress
        # Prev level total XP requirement
        prev_level_xp_req = 50 * (lvl ** 2)
        next_level_xp_req = 50 * ((lvl + 1) ** 2)

        # XP needed for this specific level's progression
        xp_needed_for_level = next_level_xp_req - prev_level_xp_req
        # XP earned within this level
        xp_progress = xp - prev_level_xp_req

        # Handle edge case for level 0 or 1 if math gets weird, but standard 50*n^2 works fine.
        # Level 1 starts at 0 XP.
        # Next level (2) needs 50 * 4 = 200 Total XP.
        # Progress: 0/200.

        percent = min(round((xp_progress / xp_needed_for_level) * 100), 100)

        embed = discord.Embed(title=f"Rank: {user.display_name}", color=discord.Color.blue())
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="Level", value=str(lvl), inline=True)
        embed.add_field(name="Total XP", value=f"{xp}", inline=True)
        embed.add_field(name="Progress", value=f"{xp_progress}/{xp_needed_for_level} ({percent}%)", inline=False)

        # Visual Bar
        bar_len = 20
        filled = int(percent / (100 / bar_len))
        bar = "█" * filled + "░" * (bar_len - filled)
        embed.add_field(name="Next Level", value=f"`{bar}`", inline=False)

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="levels", description="XP Leaderboard")
    async def levels(self, ctx):
        rows = await self.bot.db.fetch("SELECT user_id, level, xp FROM users ORDER BY xp DESC LIMIT 10")

        embed = discord.Embed(title="Global Level Leaderboard", color=discord.Color.magenta())
        for idx, row in enumerate(rows, start=1):
            user = self.bot.get_user(row['user_id'])
            name = user.name if user else f"Unknown ({row['user_id']})"
            embed.add_field(name=f"{idx}. {name}", value=f"Level {row['level']} | {row['xp']} XP", inline=False)

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Leveling(bot))
