import discord
from discord.ext import commands
import yt_dlp
import asyncio
from collections import deque

# Suppress noise about console usage from errors
yt_dlp.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',  # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn',
    # Reconnect options are crucial for stability with streaming
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queues = {} # guild_id -> deque
        self.current_song = {} # guild_id -> title

    def get_queue(self, guild_id):
        if guild_id not in self.queues:
            self.queues[guild_id] = deque()
        return self.queues[guild_id]

    async def play_next(self, ctx):
        queue = self.get_queue(ctx.guild.id)
        if len(queue) > 0:
            url = queue.popleft()

            try:
                # We stream to avoid massive downloads
                player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
                ctx.voice_client.play(player, after=lambda e: self.bot.loop.create_task(self.play_next(ctx)))

                self.current_song[ctx.guild.id] = player.title
                await ctx.send(f"Now playing: **{player.title}**")
            except Exception as e:
                await ctx.send(f"An error occurred playing the song: {e}")
                # Try next song if this one fails
                await self.play_next(ctx)
        else:
            self.current_song[ctx.guild.id] = None
            # Disconnect if queue is empty? Or just wait?
            # Let's wait. But usually bots disconnect after timeout.
            pass

    @commands.hybrid_command(name="play", description="Play a song from YouTube")
    async def play(self, ctx, *, query: str):
        if not ctx.message.author.voice:
            await ctx.send("You are not connected to a voice channel.")
            return

        channel = ctx.message.author.voice.channel
        if not ctx.voice_client:
            await channel.connect()

        async with ctx.typing():
            queue = self.get_queue(ctx.guild.id)

            # If nothing is playing, play immediately
            if not ctx.voice_client.is_playing():
                try:
                    player = await YTDLSource.from_url(query, loop=self.bot.loop, stream=True)
                    ctx.voice_client.play(player, after=lambda e: self.bot.loop.create_task(self.play_next(ctx)))

                    self.current_song[ctx.guild.id] = player.title
                    await ctx.send(f"Now playing: **{player.title}**")
                except Exception as e:
                    await ctx.send(f"Error: {e}")
            else:
                # Add to queue
                queue.append(query)
                await ctx.send(f"Added to queue: **{query}**")

    @commands.hybrid_command(name="skip", description="Skip the current song")
    async def skip(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            await ctx.send("Skipped.")
        else:
            await ctx.send("Nothing is playing.")

    @commands.hybrid_command(name="stop", description="Stop music and clear queue")
    async def stop(self, ctx):
        queue = self.get_queue(ctx.guild.id)
        queue.clear()

        if ctx.voice_client:
            if ctx.voice_client.is_playing():
                ctx.voice_client.stop()
            await ctx.voice_client.disconnect()
            await ctx.send("Stopped music and disconnected.")

    @commands.hybrid_command(name="queue", description="Show the current music queue")
    async def queue(self, ctx):
        queue = self.get_queue(ctx.guild.id)
        if len(queue) == 0:
            await ctx.send("Queue is empty.")
            return

        embed = discord.Embed(title="Music Queue", color=discord.Color.purple())
        desc = ""
        for i, item in enumerate(queue, start=1):
            # Since we just store the query/url in queue for lazy loading, we might not have the title yet.
            # Showing the query string is the best we can do without fetching info for every item (slow).
            desc += f"{i}. {item}\n"

        embed.description = desc[:2000] # Limit length
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="nowplaying", description="Show current song")
    async def nowplaying(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            title = self.current_song.get(ctx.guild.id, "Unknown")
            await ctx.send(f"Now playing: **{title}**")
        else:
            await ctx.send("Nothing is playing.")

async def setup(bot):
    await bot.add_cog(Music(bot))
