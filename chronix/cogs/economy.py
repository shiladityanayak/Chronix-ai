import discord
from discord.ext import commands
from discord import app_commands
import random
from datetime import datetime, timedelta

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_account(self, user_id):
        # Fetch user account, create if not exists
        row = await self.bot.db.fetchval("SELECT balance FROM users WHERE user_id = $1", user_id)
        if row is None:
            await self.bot.db.execute("INSERT INTO users (user_id) VALUES ($1)", user_id)
            return {"balance": 0, "bank": 0}

        # We need more than just balance usually, let's fetch the whole row
        data = await self.bot.db.fetch("SELECT * FROM users WHERE user_id = $1", user_id)
        return data[0]

    @commands.hybrid_command(name="balance", description="Check your balance")
    async def balance(self, ctx, user: discord.User = None):
        user = user or ctx.author
        account = await self.get_account(user.id)

        embed = discord.Embed(title=f"{user.name}'s Balance", color=discord.Color.green())
        embed.add_field(name="Wallet", value=f"${account['balance']}")
        embed.add_field(name="Bank", value=f"${account['bank']}")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="daily", description="Claim your daily reward")
    async def daily(self, ctx):
        user_id = ctx.author.id
        account = await self.get_account(user_id)

        last_daily = account['last_daily']
        if last_daily:
            # Check if 24h passed
            diff = datetime.utcnow() - last_daily
            if diff.total_seconds() < 86400:
                retry_after = timedelta(seconds=86400 - diff.total_seconds())
                await ctx.send(f"You can claim your daily in {retry_after}.")
                return

        amount = random.randint(100, 500)
        await self.bot.db.execute(
            "UPDATE users SET balance = balance + $1, last_daily = $2 WHERE user_id = $3",
            amount, datetime.utcnow(), user_id
        )
        await ctx.send(f"You claimed ${amount}!")

    @commands.hybrid_command(name="deposit", description="Deposit money into your bank")
    async def deposit(self, ctx, amount: str):
        account = await self.get_account(ctx.author.id)
        balance = account['balance']

        if amount.lower() == "all":
            to_deposit = balance
        else:
            try:
                to_deposit = int(amount)
            except ValueError:
                await ctx.send("Please enter a valid amount.")
                return

        if to_deposit > balance:
            await ctx.send("You don't have that much money.")
            return

        if to_deposit <= 0:
            await ctx.send("Amount must be positive.")
            return

        await self.bot.db.execute(
            "UPDATE users SET balance = balance - $1, bank = bank + $1 WHERE user_id = $2",
            to_deposit, ctx.author.id
        )
        await ctx.send(f"Deposited ${to_deposit} into your bank.")

    @commands.hybrid_command(name="withdraw", description="Withdraw money from your bank")
    async def withdraw(self, ctx, amount: str):
        account = await self.get_account(ctx.author.id)
        bank = account['bank']

        if amount.lower() == "all":
            to_withdraw = bank
        else:
            try:
                to_withdraw = int(amount)
            except ValueError:
                await ctx.send("Please enter a valid amount.")
                return

        if to_withdraw > bank:
            await ctx.send("You don't have that much in your bank.")
            return

        if to_withdraw <= 0:
            await ctx.send("Amount must be positive.")
            return

        await self.bot.db.execute(
            "UPDATE users SET bank = bank - $1, balance = balance + $1 WHERE user_id = $2",
            to_withdraw, ctx.author.id
        )
        await ctx.send(f"Withdrew ${to_withdraw} from your bank.")

    @commands.hybrid_command(name="pay", description="Pay another user")
    async def pay(self, ctx, user: discord.User, amount: int):
        if user.id == ctx.author.id:
            await ctx.send("You can't pay yourself.")
            return

        if amount <= 0:
            await ctx.send("Amount must be positive.")
            return

        sender_account = await self.get_account(ctx.author.id)
        if sender_account['balance'] < amount:
            await ctx.send("You don't have enough money.")
            return

        # Ensure receiver exists
        await self.get_account(user.id)

        # Transaction
        try:
            # We use a transaction to ensure money isn't lost
            async with self.bot.db.pool.acquire() as conn:
                async with conn.transaction():
                    await conn.execute("UPDATE users SET balance = balance - $1 WHERE user_id = $2", amount, ctx.author.id)
                    await conn.execute("UPDATE users SET balance = balance + $1 WHERE user_id = $2", amount, user.id)

            await ctx.send(f"You paid {user.mention} ${amount}.")
        except Exception as e:
            await ctx.send("Transaction failed.")
            print(f"Transaction error: {e}")

    @commands.hybrid_command(name="leaderboard", description="Show top richest users")
    async def leaderboard(self, ctx):
        rows = await self.bot.db.fetch("SELECT user_id, balance + bank as total FROM users ORDER BY total DESC LIMIT 10")

        embed = discord.Embed(title="Global Leaderboard", color=discord.Color.gold())
        for idx, row in enumerate(rows, start=1):
            user = self.bot.get_user(row['user_id'])
            name = user.name if user else f"Unknown ({row['user_id']})"
            embed.add_field(name=f"{idx}. {name}", value=f"${row['total']}", inline=False)

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Economy(bot))
