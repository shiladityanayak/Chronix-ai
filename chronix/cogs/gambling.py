import discord
from discord.ext import commands
import random
import asyncio

class Gambling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_balance(self, user_id):
        return await self.bot.db.fetchval("SELECT balance FROM users WHERE user_id = $1", user_id) or 0

    async def update_balance(self, user_id, amount):
        # Amount can be negative
        await self.bot.db.execute(
            "UPDATE users SET balance = balance + $1 WHERE user_id = $2",
            amount, user_id
        )

    @commands.hybrid_command(name="coinflip", description="Flip a coin to double your bet")
    async def coinflip(self, ctx, amount: int, choice: str):
        choice = choice.lower()
        if choice not in ["heads", "tails"]:
            await ctx.send("Please choose 'heads' or 'tails'.")
            return

        if amount <= 0:
            await ctx.send("Bet must be positive.")
            return

        bal = await self.get_balance(ctx.author.id)
        if bal < amount:
            await ctx.send("You don't have enough money.")
            return

        outcome = random.choice(["heads", "tails"])

        if outcome == choice:
            await self.update_balance(ctx.author.id, amount)
            await ctx.send(f"🪙 It was **{outcome.title()}**! You won **${amount}**!")
        else:
            await self.update_balance(ctx.author.id, -amount)
            await ctx.send(f"🪙 It was **{outcome.title()}**... You lost **${amount}**.")

    @commands.hybrid_command(name="dice", description="Roll a dice. 4, 5, 6 wins.")
    async def dice(self, ctx, amount: int):
        if amount <= 0:
            await ctx.send("Bet must be positive.")
            return

        bal = await self.get_balance(ctx.author.id)
        if bal < amount:
            await ctx.send("You don't have enough money.")
            return

        roll = random.randint(1, 6)

        if roll >= 4:
            await self.update_balance(ctx.author.id, amount)
            await ctx.send(f"🎲 You rolled a **{roll}**. You won **${amount}**!")
        else:
            await self.update_balance(ctx.author.id, -amount)
            await ctx.send(f"🎲 You rolled a **{roll}**. You lost **${amount}**.")

    @commands.hybrid_command(name="slots", description="Play slots. Match 2 or 3 symbols.")
    async def slots(self, ctx, amount: int):
        if amount <= 0:
            await ctx.send("Bet must be positive.")
            return

        bal = await self.get_balance(ctx.author.id)
        if bal < amount:
            await ctx.send("You don't have enough money.")
            return

        # Deduct bet first to prevent spamming while running
        await self.update_balance(ctx.author.id, -amount)

        emojis = ["🍎", "🍊", "🍇", "🍒", "💎", "7️⃣"]
        # Bias the slots slightly against the user or fair? Let's keep it pure random for now.
        row = [random.choice(emojis) for _ in range(3)]

        # Calculate payout
        payout = 0
        multiplier = 0

        if row[0] == row[1] == row[2]:
            if row[0] == "7️⃣":
                multiplier = 10
            elif row[0] == "💎":
                multiplier = 5
            else:
                multiplier = 3
        elif row[0] == row[1] or row[1] == row[2] or row[0] == row[2]:
             multiplier = 1.5

        payout = int(amount * multiplier)

        embed = discord.Embed(title="🎰 Slots 🎰", color=discord.Color.gold())
        embed.description = f"**| {row[0]} | {row[1]} | {row[2]} |**"

        if payout > 0:
            profit = payout # Since we already deducted the bet, we just give back the payout.
            # Wait, standard gambling:
            # If I bet 100, and win 2x. I get 200 back. Net +100.
            # So I need to add payout back to balance.
            await self.update_balance(ctx.author.id, payout)
            embed.add_field(name="Result", value=f"You won **${payout}**!")
        else:
            embed.add_field(name="Result", value="You lost.")

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Gambling(bot))
