import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone
import io
import html
import asyncio
import re

TOKEN = "Enter your token here"

intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.voice_states = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# In-memory settings
staff_roles = {}
ticket_claims = {}
ticket_owners = {}
ticket_locks = set()
voice_locks = set()
ticket_counter = {}


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


class TicketControls(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Claim Ticket",
        style=discord.ButtonStyle.primary,
        emoji="🙋",
        custom_id="tickets:claim"
    )
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "This can only be used in a server.", ephemeral=True
            )

        if not is_staff(interaction.user):
            return await interaction.response.send_message(
                "Only staff can claim tickets.", ephemeral=True
            )

        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel) or channel.id not in ticket_owners:
            return await interaction.response.send_message(
                "This is not a recognized ticket.", ephemeral=True
            )

        current = ticket_claims.get(channel.id)
        if current:
            return await interaction.response.send_message(
                f"This ticket is already claimed by <@{current}>.", ephemeral=True
            )

        ticket_claims[channel.id] = interaction.user.id
        await interaction.response.send_message(
            f"🙋 Ticket claimed by {interaction.user.mention}."
        )

    @discord.ui.button(
        label="Lock Ticket",
        style=discord.ButtonStyle.secondary,
        emoji="🔒",
        custom_id="tickets:lock"
    )
    async def lock(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "This can only be used in a server.", ephemeral=True
            )

        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel) or channel.id not in ticket_owners:
            return await interaction.response.send_message(
                "This is not a recognized ticket.", ephemeral=True
            )

        if not is_staff(interaction.user):
            return await interaction.response.send_message(
                "Only staff can lock tickets.", ephemeral=True
            )

        owner_id = ticket_owners[channel.id]
        owner = interaction.guild.get_member(owner_id)

        try:
            if owner:
                await channel.set_permissions(
                    owner,
                    view_channel=True,
                    send_messages=False,
                    read_message_history=True
                )
            ticket_locks.add(channel.id)
            await interaction.response.send_message(
                f"🔒 Ticket locked by {interaction.user.mention}."
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "I need Manage Channels permission to lock this ticket.",
                ephemeral=True
            )

    @discord.ui.button(
        label="Unlock Ticket",
        style=discord.ButtonStyle.success,
        emoji="🔓",
        custom_id="tickets:unlock"
    )
    async def unlock(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "This can only be used in a server.", ephemeral=True
            )

        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel) or channel.id not in ticket_owners:
            return await interaction.response.send_message(
                "This is not a recognized ticket.", ephemeral=True
            )

        if not is_staff(interaction.user):
            return await interaction.response.send_message(
                "Only staff can unlock tickets.", ephemeral=True
            )

        owner = interaction.guild.get_member(ticket_owners[channel.id])

        try:
            if owner:
                await channel.set_permissions(
                    owner,
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True
                )
            ticket_locks.discard(channel.id)
            await interaction.response.send_message(
                f"🔓 Ticket unlocked by {interaction.user.mention}."
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "I need Manage Channels permission to unlock this ticket.",
                ephemeral=True
            )

    @discord.ui.button(
        label="Transcript",
        style=discord.ButtonStyle.secondary,
        emoji="📄",
        custom_id="tickets:transcript"
    )
    async def transcript(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "This can only be used in a server.", ephemeral=True
            )

        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel) or channel.id not in ticket_owners:
            return await interaction.response.send_message(
                "This is not a recognized ticket.", ephemeral=True
            )

        owner_id = ticket_owners[channel.id]
        if not is_staff(interaction.user) and interaction.user.id != owner_id:
            return await interaction.response.send_message(
                "Only the ticket owner and staff can create a transcript.",
                ephemeral=True
            )

        await interaction.response.defer(ephemeral=True, thinking=True)

        messages = []
        async for message in channel.history(limit=None, oldest_first=True):
            timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
            content = html.escape(message.content or "")
            attachments = "".join(
                f'<p><a href="{html.escape(a.url, quote=True)}">'
                f'{html.escape(a.filename)}</a></p>'
                for a in message.attachments
            )
            embeds = "".join(
                f"<p>[Embed: {html.escape(e.title or 'Untitled')}]</p>"
                for e in message.embeds
            )
            messages.append(
                f"<article><b>{html.escape(str(message.author))}</b> "
                f"<small>{timestamp}</small><p>{content}</p>"
                f"{attachments}{embeds}</article><hr>"
            )

        document = f"""<!doctype html>
<html><head><meta charset="utf-8">
<title>Transcript - {html.escape(channel.name)}</title>
<style>
body{{font-family:Arial,sans-serif;max-width:1000px;margin:30px auto;padding:0 16px;background:#f5f5f5;color:#222}}
article{{background:white;padding:14px;border-radius:8px;overflow-wrap:anywhere}}
small{{color:#666;margin-left:8px}}hr{{border:0;margin:12px}}
</style></head><body>
<h1>Transcript: {html.escape(channel.name)}</h1>
<p>Server: {html.escape(interaction.guild.name)}</p>
{''.join(messages)}
</body></html>"""

        file = discord.File(
            io.BytesIO(document.encode("utf-8")),
            filename=f"{safe_name(channel.name)}-transcript.html"
        )
        await interaction.followup.send(
            "Transcript generated:", file=file, ephemeral=True
        )


class TicketPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Create Ticket",
        style=discord.ButtonStyle.success,
        emoji="🎫",
        custom_id="tickets:create"
    )
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        if not guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "This can only be used in a server.", ephemeral=True
            )

        existing = next(
            (
                channel for channel in guild.text_channels
                if ticket_owners.get(channel.id) == interaction.user.id
            ),
            None
        )
        if existing:
            return await interaction.response.send_message(
                f"You already have a ticket: {existing.mention}", ephemeral=True
            )

        roles = staff_roles.get(guild.id, set())
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True
            )
        }

        for role_id in roles:
            role = guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    manage_messages=True
                )

        category = discord.utils.get(guild.categories, name="Tickets")
        if category is None:
            try:
                category = await guild.create_category("Tickets")
            except discord.Forbidden:
                return await interaction.response.send_message(
                    "I need Manage Channels permission to create tickets.",
                    ephemeral=True
                )

        ticket_counter[guild.id] = ticket_counter.get(guild.id, 0) + 1
        channel_name = (
            f"ticket-{safe_name(interaction.user.name)}-"
            f"{ticket_counter[guild.id]:04d}"
        )

        try:
            channel = await guild.create_text_channel(
                channel_name,
                category=category,
                overwrites=overwrites,
                topic=f"Ticket owner ID: {interaction.user.id}"
            )
        except discord.Forbidden:
            return await interaction.response.send_message(
                "I need Manage Channels permission to create tickets.",
                ephemeral=True
            )

        ticket_owners[channel.id] = interaction.user.id

        await channel.send(
            f"{interaction.user.mention} Welcome! Staff will assist you here.\n"
            "Use the buttons below to manage this ticket.",
            view=TicketControls()
        )
        await interaction.response.send_message(
            f"Your ticket has been created: {channel.mention}",
            ephemeral=True
        )


@bot.event
async def setup_hook():
    bot.add_view(TicketPanel())
    bot.add_view(TicketControls())


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands.")
    except discord.HTTPException as exc:
        print(f"Command sync failed: {exc}")


# ---------------- BASIC COMMANDS ----------------
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
            "**Ticket buttons:** Create, Claim, Lock, Unlock, Transcript"
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
    try:
        await member.timeout(discord.utils.utcnow() + discord.timedelta(minutes=minutes), reason=reason)
        await interaction.response.send_message(
            f"⏳ Timed out {member.mention} for {minutes} minutes. Reason: {reason}"
        )
    except (discord.Forbidden, AttributeError):
        from datetime import timedelta
        try:
            await member.timeout(discord.utils.utcnow() + timedelta(minutes=minutes), reason=reason)
            await interaction.response.send_message(
                f"⏳ Timed out {member.mention} for {minutes} minutes. Reason: {reason}"
            )
        except discord.Forbidden:
            await interaction.response.send_message("I cannot timeout that member.", ephemeral=True)


@bot.tree.command(name="untimeout", description="Remove a member's timeout")
@app_commands.checks.has_permissions(moderate_members=True)
async def untimeout(interaction: discord.Interaction, member: discord.Member):
    try:
        await member.timeout(None, reason=f"Removed by {interaction.user}")
        await interaction.response.send_message(f"Timeout removed for {member.mention}.")
    except discord.Forbidden:
        await interaction.response.send_message("I cannot modify that member.", ephemeral=True)


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
    await interaction.channel.edit(slowmode_delay=seconds)
    await interaction.response.send_message(f"Slowmode set to {seconds} seconds.")


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
    staff_roles[interaction.guild.id] = roles

    mentions = ", ".join(f"<@&{rid}>" for rid in roles)
    await interaction.response.send_message(
        f"✅ Staff roles configured: {mentions}\n"
        "Staff can now claim, lock, and manage tickets.",
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
        description="Click the button below to open a private support ticket.",
        color=discord.Color.blurple()
    )
    await interaction.channel.send(embed=embed, view=TicketPanel())
    await interaction.response.send_message("Ticket panel posted.", ephemeral=True)


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
    try:
        await channel.set_permissions(
            interaction.guild.default_role,
            connect=False
        )
        voice_locks.add(channel.id)
        await interaction.response.send_message(
            f"🔒 Locked {channel.mention}. Members cannot join until it is unlocked."
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            "I need Manage Channels permission.", ephemeral=True
        )


@bot.tree.command(name="unlockvc", description="Unlock your current voice channel")
@staff_check()
async def unlockvc(interaction: discord.Interaction):
    member = interaction.user
    if not isinstance(member, discord.Member) or not member.voice or not member.voice.channel:
        return await interaction.response.send_message(
            "Join a voice channel first.", ephemeral=True
        )

    channel = member.voice.channel
    try:
        await channel.set_permissions(
            interaction.guild.default_role,
            connect=None
        )
        voice_locks.discard(channel.id)
        await interaction.response.send_message(f"🔓 Unlocked {channel.mention}.")
    except discord.Forbidden:
        await interaction.response.send_message(
            "I need Manage Channels permission.", ephemeral=True
        )


# ---------------- TICKET CLOSE ----------------

@bot.tree.command(name="close", description="Close and delete the current ticket")
async def close(interaction: discord.Interaction):
    channel = interaction.channel
    if not isinstance(channel, discord.TextChannel) or channel.id not in ticket_owners:
        return await interaction.response.send_message("This is not a ticket.", ephemeral=True)

    owner_id = ticket_owners[channel.id]
    if interaction.user.id != owner_id and not is_staff(interaction.user):
        return await interaction.response.send_message(
            "Only the ticket owner or staff can close this ticket.", ephemeral=True
        )

    await interaction.response.send_message(
        "Closing ticket in 5 seconds. Generate a transcript first if needed."
    )
    await asyncio.sleep(5)

    ticket_owners.pop(channel.id, None)
    ticket_claims.pop(channel.id, None)
    ticket_locks.discard(channel.id)
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


# Paste your bot token here
bot.run(token=TOKEN)
