import discord
from discord.ext import commands
import random
import asyncio

# Define Items Configuration
ITEMS = {
    "fishing_pole": {"name": "Fishing Pole", "emoji": "🎣", "price": 5000, "type": "tool", "description": "Used to catch fish."},
    "hunting_rifle": {"name": "Hunting Rifle", "emoji": "🔫", "price": 10000, "type": "tool", "description": "Used to hunt animals."},
    "shovel": {"name": "Shovel", "emoji": "⛏️", "price": 3000, "type": "tool", "description": "Used to dig for treasure."},
    "laptop": {"name": "Laptop", "emoji": "💻", "price": 15000, "type": "tool", "description": "Used to post memes and work."},
    "fish": {"name": "Common Fish", "emoji": "🐟", "price": 50, "type": "collectible", "description": "A slippery fish."},
    "trash": {"name": "Trash", "emoji": "🗑️", "price": 0, "type": "collectible", "description": "Useless garbage."},
    "treasure_chest": {"name": "Treasure Chest", "emoji": "💰", "price": 5000, "type": "collectible", "description": "Full of gold!"},
    "deer": {"name": "Deer", "emoji": "🦌", "price": 200, "type": "collectible", "description": "A noble forest creature."}
}

class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._cd = commands.CooldownMapping.from_cooldown(1, 10.0, commands.BucketType.user)

    async def get_balance(self, user_id):
        return await self.bot.db.fetchval("SELECT balance FROM users WHERE user_id = $1", user_id) or 0

    async def update_balance(self, user_id, amount):
        await self.bot.db.execute("UPDATE users SET balance = balance + $1 WHERE user_id = $2", amount, user_id)

    async def add_item(self, user_id, item_id, amount=1):
        # Upsert inventory
        exists = await self.bot.db.fetchval("SELECT amount FROM inventory WHERE user_id = $1 AND item_id = $2", user_id, item_id)
        if exists is not None:
            await self.bot.db.execute("UPDATE inventory SET amount = amount + $1 WHERE user_id = $2 AND item_id = $3", amount, user_id, item_id)
        else:
            await self.bot.db.execute("INSERT INTO inventory (user_id, item_id, amount) VALUES ($1, $2, $3)", user_id, item_id, amount)

    async def remove_item(self, user_id, item_id, amount=1):
        current = await self.bot.db.fetchval("SELECT amount FROM inventory WHERE user_id = $1 AND item_id = $2", user_id, item_id)
        if not current or current < amount:
            return False

        if current == amount:
            await self.bot.db.execute("DELETE FROM inventory WHERE user_id = $1 AND item_id = $2", user_id, item_id)
        else:
            await self.bot.db.execute("UPDATE inventory SET amount = amount - $1 WHERE user_id = $2 AND item_id = $3", amount, user_id, item_id)
        return True

    async def has_item(self, user_id, item_id):
        count = await self.bot.db.fetchval("SELECT amount FROM inventory WHERE user_id = $1 AND item_id = $2", user_id, item_id)
        return count is not None and count > 0

    @commands.hybrid_command(name="shop", description="View items for sale")
    async def shop(self, ctx):
        embed = discord.Embed(title="🛒 Global Shop", color=discord.Color.green())

        tools = ""
        collectibles = ""

        for id, item in ITEMS.items():
            line = f"{item['emoji']} **{item['name']}** - ${item['price']:,}\n_{item['description']}_\n"
            if item['type'] == "tool":
                tools += line
            # else: We usually don't sell collectibles in the main shop, users find them.
            # But let's show them if they have a price > 0 and are meant to be bought?
            # Actually, let's only show tools for now.

        embed.add_field(name="Tools", value=tools, inline=False)
        embed.set_footer(text="Use /buy [item] to purchase!")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="buy", description="Buy an item")
    async def buy(self, ctx, item_name: str, amount: int = 1):
        item_id = item_name.lower().replace(" ", "_")

        # Fuzzy match or direct lookup
        if item_id not in ITEMS:
            # Try finding by name
            found = None
            for k, v in ITEMS.items():
                if v['name'].lower() == item_name.lower():
                    found = k
                    break
            if found:
                item_id = found
            else:
                await ctx.send("Item not found.")
                return

        item = ITEMS[item_id]
        if item['type'] != "tool":
            await ctx.send("You can only buy tools from the shop.")
            return

        cost = item['price'] * amount
        bal = await self.get_balance(ctx.author.id)

        if bal < cost:
            await ctx.send(f"You need ${cost:,} to buy {amount}x {item['name']}.")
            return

        await self.update_balance(ctx.author.id, -cost)
        await self.add_item(ctx.author.id, item_id, amount)
        await ctx.send(f"🛍️ You bought **{amount}x {item['name']}** for ${cost:,}!")

    @commands.hybrid_command(name="inventory", description="View your inventory")
    async def inventory(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        rows = await self.bot.db.fetch("SELECT item_id, amount FROM inventory WHERE user_id = $1", user.id)

        if not rows:
            await ctx.send(f"{user.display_name} has an empty inventory.")
            return

        embed = discord.Embed(title=f"{user.display_name}'s Inventory", color=discord.Color.blue())
        desc = ""
        for row in rows:
            item_id = row['item_id']
            if item_id in ITEMS:
                item = ITEMS[item_id]
                desc += f"{item['emoji']} **{item['name']}** x{row['amount']}\n"
            else:
                desc += f"❓ **Unknown Item ({item_id})** x{row['amount']}\n"

        embed.description = desc
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="sell", description="Sell an item")
    async def sell(self, ctx, item_name: str, amount: int = 1):
        item_id = item_name.lower().replace(" ", "_")

        # Lookup
        if item_id not in ITEMS:
            for k, v in ITEMS.items():
                if v['name'].lower() == item_name.lower():
                    item_id = k
                    break

        if item_id not in ITEMS:
             await ctx.send("Item not found.")
             return

        item = ITEMS[item_id]
        sell_price = int(item['price'] * 0.5) # Sell for 50%

        if sell_price <= 0:
            await ctx.send("This item cannot be sold.")
            return

        if await self.remove_item(ctx.author.id, item_id, amount):
            total = sell_price * amount
            await self.update_balance(ctx.author.id, total)
            await ctx.send(f"Sold **{amount}x {item['name']}** for ${total:,}.")
        else:
            await ctx.send("You don't have enough of that item.")

    # --- Actions ---

    @commands.hybrid_command(name="fish", description="Catch some fish")
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def fish(self, ctx):
        if not await self.has_item(ctx.author.id, "fishing_pole"):
            await ctx.send("You need a **Fishing Pole** to fish! Buy one in `/shop`.")
            return

        chance = random.randint(1, 100)
        if chance < 30:
            await ctx.send("You cast your line... but caught nothing.")
        elif chance < 80:
            # Common Fish
            await self.add_item(ctx.author.id, "fish", 1)
            await ctx.send("🎣 You caught a **Common Fish**!")
        elif chance < 95:
            # Trash
            await self.add_item(ctx.author.id, "trash", 1)
            await ctx.send("🎣 You caught... **Trash**. Eww.")
        else:
            # Treasure
            await self.add_item(ctx.author.id, "treasure_chest", 1)
            await ctx.send("🎉 **JACKPOT!** You fished up a **Treasure Chest**!")

    @commands.hybrid_command(name="hunt", description="Hunt for animals")
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def hunt(self, ctx):
        if not await self.has_item(ctx.author.id, "hunting_rifle"):
            await ctx.send("You need a **Hunting Rifle** to hunt! Buy one in `/shop`.")
            return

        chance = random.randint(1, 100)
        if chance < 40:
            await ctx.send("You wandered the woods but found nothing.")
        elif chance < 90:
            # Deer
            await self.add_item(ctx.author.id, "deer", 1)
            await ctx.send("🏹 You hunted a **Deer**!")
        else:
            # Nothing (missed) or maybe something rare?
            await ctx.send("You saw a bear! But it chased you away. You ran for your life.")

    @commands.hybrid_command(name="dig", description="Dig for treasure")
    @commands.cooldown(1, 45, commands.BucketType.user)
    async def dig(self, ctx):
        if not await self.has_item(ctx.author.id, "shovel"):
            await ctx.send("You need a **Shovel** to dig! Buy one in `/shop`.")
            return

        chance = random.randint(1, 100)
        if chance < 50:
            await ctx.send("You dug a deep hole... but found nothing.")
        elif chance < 90:
            # Small coins
            amount = random.randint(50, 200)
            await self.update_balance(ctx.author.id, amount)
            await ctx.send(f"⛏️ You dug up **${amount}**!")
        else:
            # Treasure
            await self.add_item(ctx.author.id, "treasure_chest", 1)
            await ctx.send("🎉 **LUCKY!** You dug up a **Treasure Chest**!")

async def setup(bot):
    await bot.add_cog(Shop(bot))
