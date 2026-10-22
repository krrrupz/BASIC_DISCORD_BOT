 <div align="center">

# 🤖 Discord.py Moderation & Ticket Bot

### A Discord bot with slash commands, moderation tools, staff roles, private tickets, and voice-channel controls.

<p>
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Library-discord.py-5865F2?style=for-the-badge&logo=discord&logoColor=white" alt="discord.py">
  <img src="https://img.shields.io/badge/Commands-Slash%20Commands-8A2BE2?style=for-the-badge" alt="Slash Commands">
  <img src="https://img.shields.io/badge/Features-Moderation%20%7C%20Tickets-2EA44F?style=for-the-badge" alt="Features">
</p>

</div>

---

## 📌 About

This project is a `discord.py` bot featuring basic moderation, utility commands, staff-role configuration, a button-based ticket system, and voice-channel locking.

Administrators can configure staff roles through a slash command. Members can create private support tickets, while authorized staff can claim, lock, unlock, and generate HTML transcripts for tickets.

## ✨ Features

- **Slash commands:** Commands for bot latency, server information, member information, and avatars.
- **Moderation:** Kick, ban, timeout, remove timeouts, purge messages, set slowmode, and send warning DMs.
- **Staff management:** Configure up to three staff roles using `/setup`.
- **Ticket system:** Create private tickets using an interactive button panel.
- **Ticket controls:** Claim tickets, lock or unlock them, generate HTML transcripts, and close tickets.
- **Voice controls:** Lock and unlock the voice channel the staff member is currently connected to.
- **Permission checks:** Restrict moderation and ticket-management operations according to Discord permissions and configured staff roles.
- **Embeds:** Display organized information and help menus.

## 📋 Commands

### General Commands

| Command | Description |
|---|---|
| `/help` | Display the bot's command list. |
| `/ping` | Display the bot's Gateway latency. |
| `/serverinfo` | Show server information. |
| `/userinfo` | Show information about a member. |
| `/avatar` | Display a member's avatar. |

### 🛡️ Moderation Commands

| Command | Description | Permission |
|---|---|---|
| `/kick` | Kick a member from the server. | Kick Members |
| `/ban` | Ban a member from the server. | Ban Members |
| `/timeout` | Timeout a member for a specified duration. | Moderate Members |
| `/untimeout` | Remove a member's timeout. | Moderate Members |
| `/purge` | Delete between 1 and 100 recent messages. | Manage Messages |
| `/slowmode` | Set the channel's slowmode delay. | Manage Channels |
| `/clearwarn` | Send a warning to a member via DM. | Manage Messages |

### ⚙️ Staff Setup Commands

| Command | Description |
|---|---|
| `/setup` | Configure up to three staff roles. |
| `/staffroles` | Display the configured staff roles. |
| `/ticketpanel` | Post the ticket creation panel. |

The `/setup` command requires administrator permission. Configured staff roles authorize staff to claim and manage tickets and use the voice-lock commands.

### 🎫 Ticket System

The `/ticketpanel` command posts a panel containing a **Create Ticket** button.

When a member creates a ticket, the bot creates a private text channel and grants access to the ticket owner and configured staff roles.

#### Ticket Buttons

| Button | Description |
|---|---|
| Create Ticket | Create a private support channel. |
| Claim Ticket | Allow a staff member to claim the ticket. |
| Lock Ticket | Prevent the ticket owner from sending messages. |
| Unlock Ticket | Restore the ticket owner's ability to send messages. |
| Transcript | Generate and privately deliver an HTML transcript. |

#### Additional Ticket Command

| Command | Description |
|---|---|
| `/close` | Delete the current ticket after a short delay. |

### 🔊 Voice Commands

| Command | Description |
|---|---|
| `/lockvc` | Prevent members from connecting to your current voice channel. |
| `/unlockvc` | Restore the default connection permission for your current voice channel. |

These commands require a configured staff role. The bot also needs the Manage Channels permission.

## 🛠️ Setup and Installation

### 1. Install Python

```bash
python3 --version
```

### 2. Install discord.py

```bash
python3 -m pip install -U discord.py
```

For Linux systems that block system-wide pip installations, use a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U discord.py
```

### 3. Create a Discord Bot

1. Open the [Discord Developer Portal](https://discord.com/developers/applications).
2. Create an application and add a bot.
3. Copy the bot token.
4. Open **OAuth2 → URL Generator**.
5. Select the `bot` and `applications.commands` scopes.
6. Grant the required permissions and invite the bot to your server.

### 4. Enable Intents

Under **Bot → Privileged Gateway Intents**, enable:

- **Server Members Intent**
- **Message Content Intent**

### 5. Configure the Token

At the bottom of your Python file, replace the placeholder:

```python
bot.run("YOUR_BOT_TOKEN")
```

Never publish your real bot token in a public repository. Reset it immediately if it is exposed.

### 6. Run the Bot

Save the script as `bot.py` and execute:

```bash
python3 bot.py
```

Wait for the bot to connect and synchronize its slash commands.

## 🚀 First-Time Configuration

1. Start the bot and ensure it is online.
2. Run `/setup` and select the staff roles.
3. Run `/ticketpanel` in the channel where members should open tickets.
4. Test ticket creation with a regular member account.
5. Test claiming, locking, unlocking, transcript generation, and closing.
6. Test moderation and voice commands with the appropriate permissions.

## 🔐 Required Permissions

Depending on the features being used, the bot needs:

- View Channels
- Send Messages
- Embed Links
- Attach Files
- Read Message History
- Manage Channels
- Manage Messages
- Kick Members
- Ban Members
- Moderate Members

The bot's highest role must be above any member or role it needs to moderate or assign.

## 📚 Resources

- [discord.py Documentation](https://discordpy.readthedocs.io/en/stable/)
- [discord.py API Reference](https://discordpy.readthedocs.io/en/stable/api.html)
- [Discord Developer Portal](https://discord.com/developers/applications)
- [Discord Developer Documentation](https://discord.com/developers/docs)

---

<div align="center">

**Made for moderation, community management, and support.**

⭐ Test in a private server before deploying to a larger community.

</div>
