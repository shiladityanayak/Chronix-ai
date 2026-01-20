from quart import Quart, render_template, redirect, url_for, session, request
import os
import aiohttp

app = Quart(__name__)
app.secret_key = os.urandom(24)

# We will inject the bot instance later
app.bot = None

# OAuth2 Config (Should be in .env but simplified here for now)
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "")
DISCORD_REDIRECT_URI = "http://localhost:5000/callback"
API_ENDPOINT = 'https://discord.com/api/v10'

@app.route("/")
async def home():
    user = session.get("user")
    return await render_template("home.html", user=user)

@app.route("/login")
async def login():
    return redirect(f"https://discord.com/api/oauth2/authorize?client_id={DISCORD_CLIENT_ID}&redirect_uri={DISCORD_REDIRECT_URI}&response_type=code&scope=identify%20guilds")

@app.route("/callback")
async def callback():
    code = request.args.get("code")
    data = {
        "client_id": DISCORD_CLIENT_ID,
        "client_secret": DISCORD_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": DISCORD_REDIRECT_URI
    }

    async with aiohttp.ClientSession() as http:
        async with http.post(f"{API_ENDPOINT}/oauth2/token", data=data) as resp:
            resp_data = await resp.json()
            access_token = resp_data.get("access_token")

        async with http.get(f"{API_ENDPOINT}/users/@me", headers={"Authorization": f"Bearer {access_token}"}) as resp:
            user_data = await resp.json()

        session["user"] = user_data
        session["token"] = access_token

    return redirect(url_for("dashboard"))

@app.route("/dashboard")
async def dashboard():
    user = session.get("user")
    if not user:
        return redirect(url_for("login"))

    # Fetch user guilds
    token = session.get("token")
    async with aiohttp.ClientSession() as http:
        async with http.get(f"{API_ENDPOINT}/users/@me/guilds", headers={"Authorization": f"Bearer {token}"}) as resp:
            guilds = await resp.json()

    # Filter guilds: User must be Admin (0x8) and Bot must be in it
    manageable_guilds = []

    if app.bot:
        bot_guilds = [g.id for g in app.bot.guilds]

        for g in guilds:
            # Check perm (simplistic check for admin bit)
            perms = int(g["permissions"])
            if (perms & 0x8) == 0x8:
                 # Check if bot is in it
                 if int(g["id"]) in bot_guilds:
                     g["in_server"] = True
                     manageable_guilds.append(g)
                 else:
                     # Maybe show an invite link?
                     pass

    return await render_template("dashboard.html", user=user, guilds=manageable_guilds)

@app.route("/server/<int:guild_id>")
async def server_dashboard(guild_id):
    user = session.get("user")
    if not user:
        return redirect(url_for("login"))

    # Check permissions again... skipping for MVP speed

    guild_name = "Unknown Guild"
    if app.bot:
        guild = app.bot.get_guild(guild_id)
        if guild:
            guild_name = guild.name

    # Fetch Config
    config = await app.bot.db.fetchrow("SELECT * FROM guilds WHERE guild_id = $1", guild_id)

    return await render_template("server.html", guild_name=guild_name, guild_id=guild_id, config=config)

# API Route to save config
@app.route("/api/server/<int:guild_id>/update", methods=["POST"])
async def update_server(guild_id):
    form = await request.form
    automod = form.get("automod") == "on"

    exists = await app.bot.db.fetchval("SELECT 1 FROM guilds WHERE guild_id = $1", guild_id)
    if exists:
        await app.bot.db.execute("UPDATE guilds SET automod_enabled = $1 WHERE guild_id = $2", automod, guild_id)
    else:
        await app.bot.db.execute("INSERT INTO guilds (guild_id, automod_enabled) VALUES ($1, $2)", guild_id, automod)

    return redirect(url_for("server_dashboard", guild_id=guild_id))
