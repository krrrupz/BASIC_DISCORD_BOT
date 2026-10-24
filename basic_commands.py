import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone
import io
import html
import asyncio
import re
import os
import json
from io import BytesIO

TOKEN = "Enter your token here"

try:
    from PIL import Image, ImageDraw, ImageFont, ImageOps
except ImportError:
    Image = ImageDraw = ImageFont = ImageOps = None

intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.voice_states = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Persistent state is stored beside this script in bot_data.json.
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot_data.json")

staff_roles = {}
ticket_claims = {}
ticket_owners = {}
ticket_locks = set()
voice_locks = set()
ticket_counter = {}


def load_state():
    """Load saved bot state. JSON object keys are strings, so convert IDs back to ints."""
    global staff_roles, ticket_claims, ticket_owners
    global ticket_locks, voice_locks, ticket_counter

    if not os.path.exists(DATA_FILE):
        print(f"No saved state found; a new one will be created at {DATA_FILE}")
        return

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        staff_roles = {
            int(guild_id): {int(role_id) for role_id in role_ids}
            for guild_id, role_ids in data.get("staff_roles", {}).items()
        }
        ticket_claims = {
            int(channel_id): int(user_id)
            for channel_id, user_id in data.get("ticket_claims", {}).items()
        }
        ticket_owners = {
            int(channel_id): int(user_id)
            for channel_id, user_id in data.get("ticket_owners", {}).items()
        }
        ticket_locks = {int(channel_id) for channel_id in data.get("ticket_locks", [])}
        voice_locks = {int(channel_id) for channel_id in data.get("voice_locks", [])}
        ticket_counter = {
            int(guild_id): int(count)
            for guild_id, count in data.get("ticket_counter", {}).items()
        }
        print(f"Loaded saved bot state from {DATA_FILE}")
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(f"Could not load {DATA_FILE}: {exc}. Starting with empty state.")


def save_state():
    """Save bot state atomically so an interrupted write is less likely to corrupt JSON."""
    data = {
        "staff_roles": {str(guild_id): sorted(role_ids) for guild_id, role_ids in staff_roles.items()},
        "ticket_claims": {str(channel_id): user_id for channel_id, user_id in ticket_claims.items()},
        "ticket_owners": {str(channel_id): user_id for channel_id, user_id in ticket_owners.items()},
        "ticket_locks": sorted(ticket_locks),
        "voice_locks": sorted(voice_locks),
        "ticket_counter": {str(guild_id): count for guild_id, count in ticket_counter.items()},
    }

    temp_path = DATA_FILE + ".tmp"
    try:
        with open(temp_path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp_path, DATA_FILE)
    except OSError as exc:
        print(f"Could not save bot state to {DATA_FILE}: {exc}")
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except OSError:
            pass


load_state()


# ---------------- WELCOME ----------------
WELCOME_BACKGROUND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "background.png")


async def create_welcome_image(member: discord.Member) -> BytesIO:
    """Create a personalized red/black welcome card. Uses background.png if supplied."""
    if Image is None:
        raise RuntimeError("Pillow is required for welcome images. Install it with: python3 -m pip install Pillow")
    size = (900, 300)
    if os.path.exists(WELCOME_BACKGROUND):
        background = ImageOps.fit(
            Image.open(WELCOME_BACKGROUND).convert("RGBA"),
            size,
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5),
        )
    else:
        # Generate a calm red-black fallback background if background.jpg is absent.
        background = Image.new("RGBA", size, (10, 8, 12, 255))
        pixels = background.load()
        for y in range(size[1]):
            for x in range(size[0]):
                glow = max(0, 1 - abs(x - size[0] / 2) / (size[0] * 0.55))
                glow *= max(0, 1 - abs(y - size[1] * 0.55) / (size[1] * 0.9))
                pixels[x, y] = (int(12 + 45 * glow), int(7 + 2 * glow), int(10 + 5 * glow), 255)
        draw_bg = ImageDraw.Draw(background)
        draw_bg.rectangle((12, 12, size[0]-13, size[1]-13), outline=(125, 20, 32, 180), width=2)
        draw_bg.ellipse((size[0]//2-90, -90, size[0]//2+90, 90), outline=(150, 25, 40, 100), width=3)

    avatar_asset = member.display_avatar.with_size(128)
    avatar_bytes = await avatar_asset.read()
    avatar = Image.open(BytesIO(avatar_bytes)).convert("RGBA").resize((112, 112))
    mask = Image.new("L", avatar.size, 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 111, 111), fill=255)
    avatar.putalpha(mask)
    x_avatar = (size[0] - 112) // 2
    background.paste(avatar, (x_avatar, 28), avatar)

    draw = ImageDraw.Draw(background)
    def load_font(size_px):
        for path in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "arial.ttf"):
            try:
                return ImageFont.truetype(path, size_px)
            except OSError:
                pass
        return ImageFont.load_default()

    lines = [
        ("WELCOME TO TEAMGG", 34, (255, 245, 245, 255), 157),
        (member.display_name[:32], 26, (245, 180, 185, 255), 207),
        (f"Member #{member.guild.member_count or 0}", 18, (205, 190, 195, 255), 246),
    ]
    for text, font_size, color, y in lines:
        font = load_font(font_size)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        draw.text(((size[0] - text_width) // 2, y), text, font=font, fill=color,
                  stroke_width=1 if font_size >= 26 else 0, stroke_fill=(25, 5, 8, 255))

    output = BytesIO()
    background.save(output, format="PNG")
    output.seek(0)
    return output


def is_staff(member: discord.Member) -> bool:
    roles = staff_roles.get(member.guild.id, set())
    return member.guild_permissions.administrator or any(
        role.id in roles for role in member.roles
    )


def staff_check():
    async def predicate(interaction: discord.Interaction):
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return False
        return is_staff(interaction.user)
    return app_commands.check(predicate)


def safe_name(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9-]", "-", value.lower())[:80] or "user"


async def create_ticket_channel(interaction: discord.Interaction, ticket_type: str, details: dict[str, str]):
    """Create a private ticket channel after validating the user's request."""
    guild = interaction.guild
    member = interaction.user
    if not guild or not isinstance(member, discord.Member):
        return await interaction.response.send_message("This can only be used in a server.", ephemeral=True)

    existing = next((ch for ch in guild.text_channels if ticket_owners.get(ch.id) == member.id), None)
    if existing:
        return await interaction.response.send_message(f"You already have a ticket: {existing.mention}", ephemeral=True)

    await interaction.response.defer(ephemeral=True, thinking=True)
    channel = None
    try:
        roles = staff_roles.get(guild.id, set())
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, attach_files=True, embed_links=True),
        }
        bot_member = guild.me
        if bot_member:
            overwrites[bot_member] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, manage_channels=True, manage_messages=True)
        for role_id in roles:
            role = guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, manage_messages=True)

        category = discord.utils.get(guild.categories, name="Tickets")
        if category is None:
            category = await guild.create_category("Tickets")

        ticket_counter[guild.id] = ticket_counter.get(guild.id, 0) + 1
        channel_name = f"ticket-{safe_name(member.name)}-{ticket_counter[guild.id]:04d}"
        topic = f"Ticket owner ID: {member.id} | Type: {ticket_type}"
        channel = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites, topic=topic)
        ticket_owners[channel.id] = member.id
        save_state()

        embed = discord.Embed(title=f"🎫 {ticket_type}", color=discord.Color.blurple())
        embed.add_field(name="Opened by", value=member.mention, inline=False)
        for label, value in details.items():
            embed.add_field(name=label, value=value[:1024], inline=False)
        await channel.send(
            content=f"{member.mention} Welcome! Staff will assist you here.\nUse the buttons below to manage this ticket.",
            embed=embed,
            view=TicketControls(),
        )
        await interaction.followup.send(f"Your ticket has been created: {channel.mention}", ephemeral=True)
    except (discord.Forbidden, discord.HTTPException) as exc:
        print(f"Ticket creation failed: {exc}")
        if channel:
            ticket_owners.pop(channel.id, None)
            save_state()
            try:
                await channel.delete(reason="Ticket setup failed")
            except discord.HTTPException:
                pass
        await interaction.followup.send(
            "I couldn't create the ticket. Please check that I have Manage Channels, View Channel, Send Messages, and Embed Links permissions.",
            ephemeral=True,
        )


class GeneralQueryModal(discord.ui.Modal, title="General Query"):
    description = discord.ui.TextInput(
        label="Describe your query", style=discord.TextStyle.paragraph,
        placeholder="Tell us what you need help with...", min_length=1, max_length=1500,
    )

    async def on_submit(self, interaction: discord.Interaction):
        value = str(self.description).strip()
        if not value:
            return await interaction.response.send_message("Please enter a description.", ephemeral=True)
        await create_ticket_channel(interaction, "General Query", {"Query description": value})


class ServerJobModal(discord.ui.Modal, title="Server Job Request"):
    server_name = discord.ui.TextInput(
        label="Server name", placeholder="Enter the server name", min_length=1, max_length=100,
    )
    requirement = discord.ui.TextInput(
        label="Requirement", style=discord.TextStyle.paragraph,
        placeholder="Describe the job or requirement", min_length=1, max_length=1500,
    )

    async def on_submit(self, interaction: discord.Interaction):
        server = str(self.server_name).strip()
        requirement = str(self.requirement).strip()
        if not server or not requirement:
            return await interaction.response.send_message("Both fields are required.", ephemeral=True)
        await create_ticket_channel(interaction, "Server Job", {
            "Server name": server,
            "Requirement": requirement,
        })


class TicketPanelSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="General Query", description="Ask a question or request support", emoji="💬", value="general"),
            discord.SelectOption(label="Server Job", description="Submit a server job with its requirements", emoji="🛠️", value="server_job"),
        ]
        super().__init__(placeholder="Choose the type of ticket...", min_values=1, max_values=1, options=options, custom_id="tickets:type_select")

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        member = interaction.user
        if not guild or not isinstance(member, discord.Member):
            return await interaction.response.send_message("This can only be used in a server.", ephemeral=True)
        existing = next((ch for ch in guild.text_channels if ticket_owners.get(ch.id) == member.id), None)
        if existing:
            return await interaction.response.send_message(f"You already have a ticket: {existing.mention}", ephemeral=True)
        if self.values[0] == "general":
            await interaction.response.send_modal(GeneralQueryModal())
        else:
            await interaction.response.send_modal(ServerJobModal())


class TicketPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketPanelSelect())


class TicketControls(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Claim Ticket", style=discord.ButtonStyle.primary, emoji="🙋", custom_id="tickets:claim")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message("This can only be used in a server.", ephemeral=True)
        if not is_staff(interaction.user):
            return await interaction.response.send_message("Only staff can claim tickets.", ephemeral=True)
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel) or channel.id not in ticket_owners:
            return await interaction.response.send_message("This is not a recognized ticket.", ephemeral=True)
        current = ticket_claims.get(channel.id)
        if current:
            return await interaction.response.send_message(f"This ticket is already claimed by <@{current}>.", ephemeral=True)
        ticket_claims[channel.id] = interaction.user.id
        save_state()
        await interaction.response.send_message(f"🙋 Ticket claimed by {interaction.user.mention}.")

    @discord.ui.button(label="Lock Ticket", style=discord.ButtonStyle.secondary, emoji="🔒", custom_id="tickets:lock")
    async def lock(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message("This can only be used in a server.", ephemeral=True)
        if not isinstance(channel, discord.TextChannel) or channel.id not in ticket_owners:
            return await interaction.response.send_message("This is not a recognized ticket.", ephemeral=True)
        if not is_staff(interaction.user):
            return await interaction.response.send_message("Only staff can lock tickets.", ephemeral=True)
        claimer_id = ticket_claims.get(channel.id)
        if not claimer_id:
            return await interaction.response.send_message("Claim this ticket before locking it.", ephemeral=True)
        if interaction.user.id != claimer_id and not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("Only the staff member who claimed this ticket can lock it.", ephemeral=True)
        try:
            owner = interaction.guild.get_member(ticket_owners[channel.id])
            claimer = interaction.guild.get_member(claimer_id)
            # Hide the ticket from all configured staff roles; member-specific overwrites
            # then preserve access for the ticket owner, claimer, and bot.
            for role_id in staff_roles.get(interaction.guild.id, set()):
                role = interaction.guild.get_role(role_id)
                if role:
                    await channel.set_permissions(role, view_channel=False)
            if owner:
                await channel.set_permissions(owner, view_channel=True, send_messages=True, read_message_history=True)
            if claimer:
                await channel.set_permissions(claimer, view_channel=True, send_messages=True, read_message_history=True, manage_messages=True)
            ticket_locks.add(channel.id)
            save_state()
            await interaction.response.send_message(f"🔒 Locked. Only the ticket owner, {claimer.mention if claimer else f'<@{claimer_id}>'}, and the bot can access this ticket.")
        except discord.Forbidden:
            await interaction.response.send_message("I need Manage Channels permission to lock this ticket.", ephemeral=True)
        except discord.HTTPException as exc:
            print(f"Ticket lock failed: {exc}")
            await interaction.response.send_message("Discord couldn't lock this ticket. Please try again.", ephemeral=True)

    @discord.ui.button(label="Unlock Ticket", style=discord.ButtonStyle.success, emoji="🔓", custom_id="tickets:unlock")
    async def unlock(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message("This can only be used in a server.", ephemeral=True)
        if not isinstance(channel, discord.TextChannel) or channel.id not in ticket_owners:
            return await interaction.response.send_message("This is not a recognized ticket.", ephemeral=True)
        if not is_staff(interaction.user):
            return await interaction.response.send_message("Only staff can unlock tickets.", ephemeral=True)
        claimer_id = ticket_claims.get(channel.id)
        if claimer_id and interaction.user.id != claimer_id and not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("Only the staff member who claimed this ticket can unlock it.", ephemeral=True)
        try:
            for role_id in staff_roles.get(interaction.guild.id, set()):
                role = interaction.guild.get_role(role_id)
                if role:
                    await channel.set_permissions(role, view_channel=True, send_messages=True, read_message_history=True, manage_messages=True)
            owner = interaction.guild.get_member(ticket_owners[channel.id])
            if owner:
                await channel.set_permissions(owner, view_channel=True, send_messages=True, read_message_history=True, attach_files=True, embed_links=True)
            if claimer_id:
                claimer = interaction.guild.get_member(claimer_id)
                if claimer:
                    await channel.set_permissions(claimer, overwrite=None)
            ticket_locks.discard(channel.id)
            save_state()
            await interaction.response.send_message("🔓 Ticket unlocked. Configured staff access has been restored.")
        except discord.Forbidden:
            await interaction.response.send_message("I need Manage Channels permission to unlock this ticket.", ephemeral=True)
        except discord.HTTPException as exc:
            print(f"Ticket unlock failed: {exc}")
            await interaction.response.send_message("Discord couldn't unlock this ticket. Please try again.", ephemeral=True)

    @discord.ui.button(label="Transcript", style=discord.ButtonStyle.secondary, emoji="📄", custom_id="tickets:transcript")
    async def transcript(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message("This can only be used in a server.", ephemeral=True)
        if not isinstance(channel, discord.TextChannel) or channel.id not in ticket_owners:
            return await interaction.response.send_message("This is not a recognized ticket.", ephemeral=True)
        owner_id = ticket_owners[channel.id]
        if not is_staff(interaction.user) and interaction.user.id != owner_id:
            return await interaction.response.send_message("Only the ticket owner and staff can create a transcript.", ephemeral=True)
        await interaction.response.defer(ephemeral=True, thinking=True)
        messages = []
        async for message in channel.history(limit=None, oldest_first=True):
            timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
            content = html.escape(message.content or "")
            attachments = "".join(f'<p><a href="{html.escape(a.url, quote=True)}">{html.escape(a.filename)}</a></p>' for a in message.attachments)
            embeds = "".join(f"<p>[Embed: {html.escape(e.title or 'Untitled')}]</p>" for e in message.embeds)
            messages.append(f"<article><b>{html.escape(str(message.author))}</b> <small>{timestamp}</small><p>{content}</p>{attachments}{embeds}</article><hr>")
        document = f"""<!doctype html><html><head><meta charset="utf-8"><title>Transcript - {html.escape(channel.name)}</title><style>body{{font-family:Arial,sans-serif;max-width:1000px;margin:30px auto;padding:0 16px;background:#f5f5f5;color:#222}}article{{background:white;padding:14px;border-radius:8px;overflow-wrap:anywhere}}small{{color:#666;margin-left:8px}}hr{{border:0;margin:12px}}</style></head><body><h1>Transcript: {html.escape(channel.name)}</h1><p>Server: {html.escape(interaction.guild.name)}</p>{''.join(messages)}</body></html>"""
        file = discord.File(io.BytesIO(document.encode("utf-8")), filename=f"{safe_name(channel.name)}-transcript.html")
        await interaction.followup.send("Transcript generated:", file=file, ephemeral=True)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="tickets:close")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message("This can only be used in a server.", ephemeral=True)
        if not isinstance(channel, discord.TextChannel) or channel.id not in ticket_owners:
            return await interaction.response.send_message("This is not a recognized ticket.", ephemeral=True)
        owner_id = ticket_owners[channel.id]
        if interaction.user.id != owner_id and not is_staff(interaction.user):
            return await interaction.response.send_message("Only the ticket owner or staff can close this ticket.", ephemeral=True)
        await interaction.response.send_message("Closing ticket in 5 seconds. Generate a transcript first if needed.")
        await asyncio.sleep(5)
        ticket_owners.pop(channel.id, None)
        ticket_claims.pop(channel.id, None)
        ticket_locks.discard(channel.id)
        save_state()
        try:
            await channel.delete(reason=f"Ticket closed by {interaction.user}")
        except discord.HTTPException as exc:
            print(f"Ticket deletion failed: {exc}")


@bot.event
async def on_member_join(member: discord.Member):
    try:
        welcome_channel = discord.utils.find(
            lambda channel: "welcome" in channel.name.lower(),
            member.guild.text_channels,
        )

        if welcome_channel is None:
            print(
                f'No text channel containing "welcome" found '
                f'in guild {member.guild.id}.'
            )
            return

        image_buffer = await create_welcome_image(member)

        embed = discord.Embed(
            description=(
                "📢 Stay Updated Through "
                "<#1562449175667408937>\n"
                "📜 Check Server Rules "
                "<#1562449384703008839>\n"
                "💬 Interact with members "
                "<#1562470041436422204>"
            ),
            color=discord.Color.blurple()
        )

        embed.set_image(url="attachment://welcome.png")

        await welcome_channel.send(
            content=f"**Welcome To Team GG {member.mention}!**\n\n",
            embed=embed,
            file=discord.File(image_buffer, filename="welcome.png"),
        )

    except Exception as exc:
        print(
            f"[WELCOME JOIN ERROR] Guild {member.guild.id}, "
            f"member {member.id}: {exc}"
        )

@bot.event
async def setup_hook():
    bot.add_view(TicketPanel())
    bot.add_view(TicketControls())


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")

    # Recover ticket owners from channel topics as a fallback for tickets created
    # before JSON persistence was added. Newly created tickets store this topic.
    changed = False
    valid_channel_ids = {channel.id for guild in bot.guilds for channel in guild.channels}
    for guild in bot.guilds:
        for channel in guild.text_channels:
            topic = channel.topic or ""
            match = re.search(r"Ticket owner ID:\s*(\d+)", topic)
            if match and channel.id not in ticket_owners:
                ticket_owners[channel.id] = int(match.group(1))
                changed = True

    # Remove stale records if a ticket channel was deleted while the bot was offline.
    for channel_id in list(ticket_owners):
        if channel_id not in valid_channel_ids:
            ticket_owners.pop(channel_id, None)
            ticket_claims.pop(channel_id, None)
            ticket_locks.discard(channel_id)
            changed = True
    if changed:
        save_state()

    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands.")
    except discord.HTTPException as exc:
        print(f"Command sync failed: {exc}")


# ---------------- BASIC COMMANDS ----------------
@bot.tree.command(name="renamebot", description="Change the bot's username")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(name="The new bot username")
async def renamebot(interaction: discord.Interaction, name: str):
    await interaction.response.defer(ephemeral=True, thinking=True)

    try:
        await bot.user.edit(username=name)

        await interaction.edit_original_response(
            content=f"✅ Bot username changed to **{name}**!"
        )

    except discord.HTTPException as exc:
        await interaction.edit_original_response(
            content=f"❌ Failed to rename the bot: {exc}"
        )
@bot.tree.command(
    name="setpfp",
    description="Change the bot's profile picture"
)
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(image="New profile picture")
async def setpfp(
    interaction: discord.Interaction,
    image: discord.Attachment
):
    if image.content_type not in (
        "image/png",
        "image/jpeg",
        "image/webp",
        "image/gif",
    ):
        return await interaction.response.send_message(
            "Please upload a PNG, JPEG, WEBP, or GIF image.",
            ephemeral=True
        )

    await interaction.response.defer(ephemeral=True)

    try:
        image_bytes = await image.read()
        await bot.user.edit(avatar=image_bytes)

        await interaction.followup.send(
            "✅ Bot profile picture updated!",
            ephemeral=True
        )

    except discord.HTTPException as exc:
        await interaction.followup.send(
            f"Failed to update the profile picture: {exc}",
            ephemeral=True
        )

@bot.tree.command(name="help", description="Show all bot commands and features")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 Bot Help Menu",
        description="Here are all the available commands.",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="📌 General Commands",
        value=(
            "`/help` — Show this help menu\n"
            "`/ping` — Check bot latency\n"
            "`/serverinfo` — Server information\n"
            "`/userinfo` — Member information\n"
            "`/avatar` — View a member's avatar"
        ),
        inline=False
    )

    embed.add_field(
        name="🛡️ Moderation",
        value=(
            "`/kick` — Kick a member\n"
            "`/ban` — Ban a member\n"
            "`/timeout` — Timeout a member\n"
            "`/untimeout` — Remove a timeout\n"
            "`/purge` — Delete recent messages\n"
            "`/slowmode` — Set channel slowmode\n"
            "`/warn` — Send a warning by DM"
        ),
        inline=False
    )

    embed.add_field(
        name="🎫 Tickets",
        value=(
            "`/ticketpanel` — Post the ticket panel\n"
            "`/close` — Close and delete a ticket\n"
            "**Ticket buttons:** Create, Claim, Lock, Unlock, Transcript, Close"
        ),
        inline=False
    )

    embed.add_field(
        name="🔊 Voice Commands",
        value=(
            "`/lockvc` — Lock your current voice channel\n"
            "`/unlockvc` — Unlock your current voice channel"
        ),
        inline=False
    )

    embed.add_field(
        name="⚙️ Staff Setup",
        value=(
            "`/setup` — Configure staff roles\n"
            "`/staffroles` — View configured staff roles"
        ),
        inline=False
    )

    embed.set_footer(text="Some commands require staff permissions.")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="ping", description="Check bot latency")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(
        f"Pong! `{round(bot.latency * 1000)} ms`"
    )


@bot.tree.command(name="serverinfo", description="Show server information")
async def serverinfo(interaction: discord.Interaction):
    guild = interaction.guild
    if not guild:
        return await interaction.response.send_message(
            "Use this in a server.", ephemeral=True
        )

    embed = discord.Embed(
        title=guild.name,
        color=discord.Color.blurple(),
        timestamp=datetime.now(timezone.utc)
    )
    embed.add_field(name="Members", value=str(guild.member_count))
    embed.add_field(name="Channels", value=str(len(guild.channels)))
    embed.add_field(name="Roles", value=str(len(guild.roles)))
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="userinfo", description="Show information about a member")
@app_commands.describe(member="Member to inspect")
async def userinfo(interaction: discord.Interaction, member: discord.Member = None):
    member = member or interaction.user
    embed = discord.Embed(
        title=str(member),
        color=discord.Color.blurple(),
        timestamp=datetime.now(timezone.utc)
    )
    embed.add_field(name="User ID", value=str(member.id))
    embed.add_field(
        name="Joined server",
        value=discord.utils.format_dt(member.joined_at, style="F")
        if member.joined_at else "Unknown",
        inline=False
    )
    embed.add_field(name="Account created", value=discord.utils.format_dt(member.created_at, style="F"), inline=False)
    embed.add_field(name="Roles", value=", ".join(r.mention for r in member.roles[1:]) or "None", inline=False)
    embed.set_thumbnail(url=member.display_avatar.url)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="avatar", description="Show a member's avatar")
@app_commands.describe(member="Member whose avatar you want")
async def avatar(interaction: discord.Interaction, member: discord.Member = None):
    member = member or interaction.user
    embed = discord.Embed(title=f"{member}'s avatar")
    embed.set_image(url=member.display_avatar.url)
    await interaction.response.send_message(embed=embed)


# ---------------- MODERATION ----------------

@bot.tree.command(name="kick", description="Kick a member")
@app_commands.checks.has_permissions(kick_members=True)
@app_commands.describe(member="Member to kick", reason="Reason for the kick")
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    if member.id == interaction.user.id or member.top_role >= interaction.user.top_role:
        return await interaction.response.send_message(
            "You cannot kick yourself or a member with an equal/higher role.",
            ephemeral=True
        )
    try:
        await member.kick(reason=f"{interaction.user} | {reason}")
        await interaction.response.send_message(f"👢 Kicked {member.mention}. Reason: {reason}")
    except discord.Forbidden:
        await interaction.response.send_message("I cannot kick that member.", ephemeral=True)


@bot.tree.command(name="ban", description="Ban a member")
@app_commands.checks.has_permissions(ban_members=True)
@app_commands.describe(member="Member to ban", reason="Reason for the ban")
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    if member.id == interaction.user.id or member.top_role >= interaction.user.top_role:
        return await interaction.response.send_message(
            "You cannot ban yourself or a member with an equal/higher role.",
            ephemeral=True
        )
    try:
        await member.ban(reason=f"{interaction.user} | {reason}")
        await interaction.response.send_message(f"🔨 Banned {member.mention}. Reason: {reason}")
    except discord.Forbidden:
        await interaction.response.send_message("I cannot ban that member.", ephemeral=True)


@bot.tree.command(name="timeout", description="Timeout a member")
@app_commands.checks.has_permissions(moderate_members=True)
@app_commands.describe(member="Member to timeout", minutes="Duration in minutes", reason="Reason")
async def timeout(
    interaction: discord.Interaction,
    member: discord.Member,
    minutes: app_commands.Range[int, 1, 40320],
    reason: str = "No reason provided"
):
    if member.id == interaction.user.id or member.top_role >= interaction.user.top_role:
        return await interaction.response.send_message(
            "You cannot timeout yourself or a member with an equal/higher role.",
            ephemeral=True
        )
    from datetime import timedelta
    await interaction.response.defer(thinking=True)
    try:
        await member.timeout(discord.utils.utcnow() + timedelta(minutes=minutes), reason=reason)
        await interaction.followup.send(
            f"⏳ Timed out {member.mention} for {minutes} minutes. Reason: {reason}"
        )
    except discord.Forbidden:
        await interaction.followup.send("I cannot timeout that member.", ephemeral=True)
    except discord.HTTPException as exc:
        print(f"Timeout failed: {exc}")
        await interaction.followup.send("Discord couldn't apply the timeout.", ephemeral=True)


@bot.tree.command(name="untimeout", description="Remove a member's timeout")
@app_commands.checks.has_permissions(moderate_members=True)
async def untimeout(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.defer(thinking=True)
    try:
        await member.timeout(None, reason=f"Removed by {interaction.user}")
        await interaction.followup.send(f"Timeout removed for {member.mention}.")
    except discord.Forbidden:
        await interaction.followup.send("I cannot modify that member.", ephemeral=True)
    except discord.HTTPException as exc:
        print(f"Untimeout failed: {exc}")
        await interaction.followup.send("Discord couldn't remove the timeout.", ephemeral=True)


@bot.tree.command(name="purge", description="Delete recent messages")
@app_commands.checks.has_permissions(manage_messages=True)
@app_commands.describe(amount="Number of messages to delete (1–100)")
async def purge(interaction: discord.Interaction, amount: app_commands.Range[int, 1, 100]):
    if not isinstance(interaction.channel, discord.TextChannel):
        return await interaction.response.send_message("Use this in a text channel.", ephemeral=True)

    await interaction.response.defer(ephemeral=True)
    try:
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"🧹 Deleted {len(deleted)} messages.", ephemeral=True)
    except discord.Forbidden:
        await interaction.followup.send("I need Manage Messages permission.", ephemeral=True)


@bot.tree.command(name="slowmode", description="Set channel slowmode")
@app_commands.checks.has_permissions(manage_channels=True)
@app_commands.describe(seconds="Slowmode seconds (0–21600)")
async def slowmode(interaction: discord.Interaction, seconds: app_commands.Range[int, 0, 21600]):
    if not isinstance(interaction.channel, discord.TextChannel):
        return await interaction.response.send_message("Use this in a text channel.", ephemeral=True)
    await interaction.response.defer(thinking=True)
    try:
        await interaction.channel.edit(slowmode_delay=seconds)
        await interaction.followup.send(f"Slowmode set to {seconds} seconds.")
    except discord.Forbidden:
        await interaction.followup.send("I need Manage Channels permission.", ephemeral=True)
    except discord.HTTPException as exc:
        print(f"Slowmode update failed: {exc}")
        await interaction.followup.send("Discord couldn't update slowmode.", ephemeral=True)


@bot.tree.command(name="warn", description="Send a moderation warning to a member")
@app_commands.checks.has_permissions(manage_messages=True)
async def warn(interaction: discord.Interaction,member: discord.Member,reason: str = "No reason provided"):
    try:
        await member.send(
            f"⚠️ You were warned in **{interaction.guild.name}**.\n"
            f"Reason: {reason}")
        dm_status = "Warning sent by DM."
    except discord.Forbidden:
        dm_status = "Could not DM the member; their DMs may be disabled."
    except discord.HTTPException:
        dm_status = "Failed to send the warning DM."

    await interaction.response.send_message(
        f"⚠️ {member.mention} — {dm_status}\nReason: {reason}",ephemeral=True)


# ---------------- STAFF SETUP ----------------

@bot.tree.command(name="setup", description="Configure staff roles for tickets")
@app_commands.describe(role1="First staff role", role2="Optional second staff role", role3="Optional third staff role")
@app_commands.checks.has_permissions(administrator=True)
async def setup(
    interaction: discord.Interaction,
    role1: discord.Role,
    role2: discord.Role = None,
    role3: discord.Role = None
):
    roles = {role.id for role in (role1, role2, role3) if role is not None}
    guild = interaction.guild
    if guild is None:
        return await interaction.response.send_message("Use this command inside a server.", ephemeral=True)

    previous = staff_roles.get(guild.id)
    staff_roles[guild.id] = roles
    if not save_state():
        if previous is None:
            staff_roles.pop(guild.id, None)
        else:
            staff_roles[guild.id] = previous
        return await interaction.response.send_message(
            "❌ Staff roles were not saved. Check the bot folder's write permissions and console output.",
            ephemeral=True,
        )

    mentions = ", ".join(f"<@&{rid}>" for rid in sorted(roles))
    await interaction.response.send_message(
        f"✅ Staff roles saved for **{guild.name}**: {mentions}\n"
        f"Saved file: `{DATA_FILE}`",
        ephemeral=True
    )


@bot.tree.command(name="staffroles", description="Show configured staff roles")
@app_commands.checks.has_permissions(administrator=True)
async def staffroles(interaction: discord.Interaction):
    roles = staff_roles.get(interaction.guild.id, set())
    mentions = [f"<@&{rid}>" for rid in roles if interaction.guild.get_role(rid)]
    await interaction.response.send_message(
        "Configured staff roles: " + (", ".join(mentions) if mentions else "None"),
        ephemeral=True
    )


@bot.tree.command(name="ticketpanel", description="Post the ticket creation panel")
@app_commands.checks.has_permissions(administrator=True)
async def ticketpanel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎫 Support Tickets",
        description="Choose a ticket type from the menu below. General Query asks for a description; Server Job asks for the server name and requirement.",
        color=discord.Color.blurple()
    )
    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        if interaction.channel is None:
            return await interaction.followup.send("This channel is unavailable.", ephemeral=True)
        await interaction.channel.send(embed=embed, view=TicketPanel())
        await interaction.followup.send("Ticket panel posted.", ephemeral=True)
    except discord.Forbidden:
        await interaction.followup.send("I cannot post in this channel.", ephemeral=True)
    except discord.HTTPException as exc:
        print(f"Ticket panel failed: {exc}")
        await interaction.followup.send("Could not post the ticket panel.", ephemeral=True)


# ---------------- VOICE CHANNEL LOCK ----------------

@bot.tree.command(name="lockvc", description="Lock your current voice channel")
@staff_check()
async def lockvc(interaction: discord.Interaction):
    member = interaction.user
    if not isinstance(member, discord.Member) or not member.voice or not member.voice.channel:
        return await interaction.response.send_message(
            "Join a voice channel first.", ephemeral=True
        )

    channel = member.voice.channel
    await interaction.response.defer(thinking=True)
    try:
        await channel.set_permissions(interaction.guild.default_role, connect=False)
        voice_locks.add(channel.id)
        save_state()
        await interaction.followup.send(
            f"🔒 Locked {channel.mention}. Members cannot join until it is unlocked."
        )
    except discord.Forbidden:
        await interaction.followup.send(
            "I need Manage Channels permission.", ephemeral=True
        )
    except discord.HTTPException as exc:
        print(f"Voice lock failed: {exc}")
        await interaction.followup.send("Discord couldn't lock this voice channel.", ephemeral=True)


@bot.tree.command(name="unlockvc", description="Unlock your current voice channel")
@staff_check()
async def unlockvc(interaction: discord.Interaction):
    member = interaction.user
    if not isinstance(member, discord.Member) or not member.voice or not member.voice.channel:
        return await interaction.response.send_message(
            "Join a voice channel first.", ephemeral=True
        )

    channel = member.voice.channel
    await interaction.response.defer(thinking=True)
    try:
        await channel.set_permissions(interaction.guild.default_role, connect=None)
        voice_locks.discard(channel.id)
        save_state()
        await interaction.followup.send(f"🔓 Unlocked {channel.mention}.")
    except discord.Forbidden:
        await interaction.followup.send(
            "I need Manage Channels permission.", ephemeral=True
        )
    except discord.HTTPException as exc:
        print(f"Voice unlock failed: {exc}")
        await interaction.followup.send("Discord couldn't unlock this voice channel.", ephemeral=True)


# ---------------- TICKET CLOSE ----------------

@bot.tree.command(name="close", description="Close and delete the current ticket")
async def close(interaction: discord.Interaction):
    channel = interaction.channel
    if not isinstance(channel, discord.TextChannel) or channel.id not in ticket_owners:
        return await interaction.response.send_message("This is not a ticket.", ephemeral=True)

    owner_id = ticket_owners[channel.id]
    if interaction.user.id != owner_id and not is_staff(interaction.user):
        return await interaction.response.send_message("Only the ticket owner or staff can close this ticket.", ephemeral=True)

    await interaction.response.send_message("Closing ticket in 5 seconds. Generate a transcript first if needed.")
    await asyncio.sleep(5)

    ticket_owners.pop(channel.id, None)
    ticket_claims.pop(channel.id, None)
    ticket_locks.discard(channel.id)
    save_state()
    try:
        await channel.delete(reason=f"Ticket closed by {interaction.user}")
    except discord.Forbidden:
        pass


# ---------------- ERROR HANDLING ----------------

@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError
):
    if isinstance(error, app_commands.MissingPermissions):
        message = "You don't have the required Discord permissions."
    elif isinstance(error, app_commands.CheckFailure):
        message = "You don't have permission to use this command."
    else:
        print(f"Command error: {error}")
        message = "An error occurred while executing this command."

    try:
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)
    except discord.HTTPException:
        pass


bot.run(token=TOKEN)
