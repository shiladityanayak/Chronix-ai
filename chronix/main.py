import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv
from core.database import Database
from web.app import app as web_app
from hypercorn.asyncio import serve
from hypercorn.config import Config as HyperConfig

load_dotenv()

class ChronixBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned_or("chr ", "Chr "),
            intents=discord.Intents.all(),
            help_command=None,
            case_insensitive=True
        )
        self.db = Database()

    async def setup_hook(self):
        # Inject bot instance into web app
        web_app.bot = self

        # Start Web Server in background task
        self.loop.create_task(self.start_web_server())

        # Initialize Database
        try:
            await self.db.connect()
            # Initialize Schema
            with open("data/schema.sql", "r") as f:
                schema = f.read()
                # Split by semicolon to execute multiple statements if needed,
                # though asyncpg execute supports multiple statements usually.
                # simpler to just execute the block.
                await self.db.execute(schema)
            print("Database schema initialized.")
        except Exception as e:
            print(f"Failed to connect to database: {e}")
            # We don't exit here because we might want to test other things,
            # but in production, this should probably crash.

        # Load Cogs
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                await self.load_extension(f"cogs.{filename[:-3]}")
                print(f"Loaded extension: {filename}")

        # Sync Slash Commands
        await self.tree.sync()
        print("Slash commands synced.")

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print("------")

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Missing required argument: {error.param}")
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("You do not have permission to use this command.")
        else:
            await ctx.send(f"An error occurred: {error}")
            # Raise it to log it to console as well
            raise error

    async def start_web_server(self):
        config = HyperConfig()
        config.bind = ["0.0.0.0:5000"]
        await serve(web_app, config)

if __name__ == "__main__":
    bot = ChronixBot()
    token = os.getenv("DISCORD_TOKEN")
    if token == "your_token_here" or not token:
        print("Please set your DISCORD_TOKEN in .env")
    else:
        bot.run(token)
