import discord
from discord.ext import commands, tasks
import datetime
import pytz
from typing import Optional

class Chronos(commands.Cog):
    """
    Time-related utilities for Chronix:
    - Timezone conversion
    - World Clock
    - Reminders
    """
    def __init__(self, bot):
        self.bot = bot
        self.common_timezones = [
            'UTC', 'US/Pacific', 'US/Eastern', 'Europe/London',
            'Europe/Paris', 'Asia/Tokyo', 'Australia/Sydney'
        ]
        self.reminder_loop.start()

    def cog_unload(self):
        self.reminder_loop.cancel()

    async def get_user_timezone(self, user_id: int) -> str:
        """Fetches the user's timezone from DB, defaults to UTC."""
        tz = await self.bot.db.fetchval(
            "SELECT timezone FROM user_settings WHERE user_id = $1", user_id
        )
        return tz or 'UTC'

    async def set_user_timezone(self, user_id: int, timezone: str):
        """Sets the user's timezone in DB."""
        # Upsert
        exists = await self.bot.db.fetchval(
            "SELECT 1 FROM user_settings WHERE user_id = $1", user_id
        )
        if exists:
            await self.bot.db.execute(
                "UPDATE user_settings SET timezone = $1 WHERE user_id = $2",
                timezone, user_id
            )
        else:
            await self.bot.db.execute(
                "INSERT INTO user_settings (user_id, timezone) VALUES ($1, $2)",
                user_id, timezone
            )

    @tasks.loop(seconds=10)
    async def reminder_loop(self):
        """Background task to check for expired reminders."""
        now = datetime.datetime.utcnow()
        try:
            # Fetch expired reminders
            rows = await self.bot.db.fetch(
                "SELECT id, user_id, channel_id, message FROM reminders WHERE expires_at <= $1",
                now
            )

            for row in rows:
                channel = self.bot.get_channel(row['channel_id'])
                user = self.bot.get_user(row['user_id'])

                if channel:
                    msg = f"⏰ **Reminder:** {row['message']}"
                    if user:
                        msg = f"{user.mention}, " + msg
                    try:
                        await channel.send(msg)
                    except discord.Forbidden:
                        pass # Can't send message

                # Delete the reminder
                await self.bot.db.execute("DELETE FROM reminders WHERE id = $1", row['id'])

        except Exception as e:
            print(f"Error in reminder loop: {e}")

    @reminder_loop.before_loop
    async def before_reminder_loop(self):
        await self.bot.wait_until_ready()

    @commands.hybrid_command(name="settimezone", description="Set your local timezone")
    async def settimezone(self, ctx, timezone: str):
        """
        Sets your timezone. Use standard names like 'US/Pacific', 'Europe/London'.
        """
        try:
            pytz.timezone(timezone)
        except pytz.UnknownTimeZoneError:
            await ctx.send("❌ Unknown timezone. Please use a valid timezone code (e.g., `US/Eastern`, `Europe/Berlin`, `UTC`).")
            return

        await self.set_user_timezone(ctx.author.id, timezone)
        await ctx.send(f"✅ Your timezone has been set to **{timezone}**.")

    @commands.hybrid_command(name="time", description="Get current time for you or another user")
    async def time_cmd(self, ctx, user: discord.Member = None):
        """
        Displays the current local time for a user.
        """
        user = user or ctx.author
        tz_name = await self.get_user_timezone(user.id)

        try:
            tz = pytz.timezone(tz_name)
            local_time = datetime.datetime.now(tz)
            fmt_time = local_time.strftime("%Y-%m-%d **%H:%M** %Z")

            await ctx.send(f"🕒 Time for **{user.display_name}**: {fmt_time}")
        except Exception as e:
            await ctx.send(f"Error retrieving time: {e}")

    @commands.hybrid_command(name="worldclock", description="Show time in major cities")
    async def worldclock(self, ctx):
        """
        Displays the current time in major global cities.
        """
        embed = discord.Embed(title="🌍 World Clock", color=discord.Color.blurple())

        for tz_name in self.common_timezones:
            tz = pytz.timezone(tz_name)
            now = datetime.datetime.now(tz)
            city = tz_name.split('/')[-1].replace('_', ' ')
            embed.add_field(name=city, value=now.strftime("%H:%M"), inline=True)

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="remindme", description="Set a reminder")
    async def remindme(self, ctx, duration: str, *, message: str):
        """
        Set a reminder. Duration format: 10s, 5m, 2h, 1d.
        """
        seconds = 0
        try:
            if duration.endswith("s"):
                seconds = int(duration[:-1])
            elif duration.endswith("m"):
                seconds = int(duration[:-1]) * 60
            elif duration.endswith("h"):
                seconds = int(duration[:-1]) * 3600
            elif duration.endswith("d"):
                seconds = int(duration[:-1]) * 86400
            else:
                # Try parsing as int (seconds default)
                seconds = int(duration)
        except ValueError:
            await ctx.send("❌ Invalid duration format. Use `10s`, `5m`, `2h`, etc.")
            return

        if seconds < 10:
            await ctx.send("❌ Minimum duration is 10 seconds.")
            return

        expires_at = datetime.datetime.utcnow() + datetime.timedelta(seconds=seconds)

        await self.bot.db.execute(
            "INSERT INTO reminders (user_id, channel_id, guild_id, message, expires_at) VALUES ($1, $2, $3, $4, $5)",
            ctx.author.id, ctx.channel.id, ctx.guild.id, message, expires_at
        )

        # Calculate human friendly time
        timestamp = int(expires_at.replace(tzinfo=datetime.timezone.utc).timestamp())
        await ctx.send(f"✅ I will remind you: **{message}** <t:{timestamp}:R>.")

async def setup(bot):
    await bot.add_cog(Chronos(bot))
