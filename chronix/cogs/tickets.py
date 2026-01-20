import discord
from discord.ext import commands
import io
import datetime

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Create Ticket", style=discord.ButtonStyle.green, custom_id="chronix:create_ticket", emoji="📩")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user

        # Check if ticket category is set
        # Since this view is persistent and stateless, we need to fetch config from DB inside the callback?
        # Or just create a new channel. For efficiency, let's create a channel in the same category or a new one.
        # But wait, accessing DB from View might require passing the bot instance.
        # The View is usually re-instantiated in setup_hook.
        # Let's assume we can get the bot via interaction.client

        bot = interaction.client
        ticket_channel_name = f"ticket-{user.name}"

        # Check if channel already exists
        existing = discord.utils.get(guild.text_channels, name=ticket_channel_name.lower().replace(" ", "-"))
        if existing:
            await interaction.response.send_message(f"You already have a ticket: {existing.mention}", ephemeral=True)
            return

        # Fetch configured category
        cat_id = await bot.db.fetchval("SELECT ticket_category_id FROM guilds WHERE guild_id = $1", guild.id)
        category = guild.get_channel(cat_id) if cat_id else None

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        try:
            channel = await guild.create_text_channel(
                name=ticket_channel_name,
                category=category,
                overwrites=overwrites,
                reason=f"Ticket created by {user}"
            )

            await interaction.response.send_message(f"Ticket created: {channel.mention}", ephemeral=True)

            embed = discord.Embed(
                title="Support Ticket",
                description=f"Hello {user.mention}, support will be with you shortly.\nClick the button below to close this ticket.",
                color=discord.Color.green()
            )
            await channel.send(embed=embed, view=CloseTicketView())

        except discord.Forbidden:
            await interaction.response.send_message("I don't have permission to create channels.", ephemeral=True)

class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.red, custom_id="chronix:close_ticket", emoji="🔒")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Closing ticket in 5 seconds...")

        # Generate Transcript
        messages = [message async for message in interaction.channel.history(limit=500, oldest_first=True)]

        transcript = f"Ticket Transcript - {interaction.channel.name}\n"
        transcript += f"Closed by: {interaction.user}\n"
        transcript += f"Date: {datetime.datetime.utcnow()}\n\n"

        for msg in messages:
            timestamp = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
            transcript += f"[{timestamp}] {msg.author}: {msg.clean_content}\n"
            if msg.attachments:
                transcript += f"  [Attachments: {', '.join([a.url for a in msg.attachments])}]\n"

        # Log to log channel if exists
        bot = interaction.client
        log_channel_id = await bot.db.fetchval("SELECT log_channel_id FROM guilds WHERE guild_id = $1", interaction.guild.id)
        if log_channel_id:
            log_channel = interaction.guild.get_channel(log_channel_id)
            if log_channel:
                file = discord.File(io.StringIO(transcript), filename=f"{interaction.channel.name}.txt")
                await log_channel.send(f"Ticket closed by {interaction.user.mention}", file=file)

        await discord.utils.sleep(5)
        await interaction.channel.delete()

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        # Register the persistent views so they work after restart
        self.bot.add_view(TicketView())
        self.bot.add_view(CloseTicketView())

    @commands.hybrid_command(name="settickets", description="Set the category for new tickets")
    @commands.has_permissions(administrator=True)
    async def settickets(self, ctx, category: discord.CategoryChannel):
        exists = await self.bot.db.fetchval("SELECT 1 FROM guilds WHERE guild_id = $1", ctx.guild.id)
        if exists:
            await self.bot.db.execute("UPDATE guilds SET ticket_category_id = $1 WHERE guild_id = $2", category.id, ctx.guild.id)
        else:
            await self.bot.db.execute("INSERT INTO guilds (guild_id, ticket_category_id) VALUES ($1, $2)", ctx.guild.id, category.id)

        await ctx.send(f"✅ Ticket category set to {category.name}")

    @commands.hybrid_command(name="ticketpanel", description="Send the ticket creation panel")
    @commands.has_permissions(administrator=True)
    async def ticketpanel(self, ctx):
        embed = discord.Embed(
            title="Create a Ticket",
            description="Click the button below to contact support.",
            color=discord.Color.blurple()
        )
        await ctx.send(embed=embed, view=TicketView())

async def setup(bot):
    await bot.add_cog(Tickets(bot))
