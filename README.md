<div align="center">

# 🔴 TEAM GG BOT ⚫

### A powerful, red-and-black themed Discord bot for community management.

<p>
  <a href="https://discord.com/developers/applications"><img src="https://img.shields.io/badge/Discord-Developer%20Portal-5865F2?style=for-the-badge&logo=discord&logoColor=white" alt="Discord Developer Portal"></a>
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Library-discord.py-5865F2?style=for-the-badge&logo=discord&logoColor=white" alt="discord.py">
  <img src="https://img.shields.io/badge/Theme-Red%20%26%20Black-B51224?style=for-the-badge" alt="Red and black theme">
</p>

<p>
  <b>🎫 Interactive Tickets</b> · <b>🛡️ Moderation</b> · <b>👋 Welcome Cards</b> · <b>🔊 Voice Controls</b>
</p>

<p>
  <a href="#-features">Features</a> •
  <a href="#-requirements">Requirements</a> •
  <a href="#-installation">Installation</a> •
  <a href="#-configuration">Configuration</a> •
  <a href="#-commands">Commands</a> •
  <a href="#-troubleshooting">Troubleshooting</a>
</p>

</div>

---

## ⚡ Overview

**Team GG Bot** is a custom Discord server bot built with `discord.py`. It combines interactive support tickets, moderation slash commands, personalized welcome cards, staff-role configuration, and voice-channel locking in one bot.

> 🔐 **Security first:** Never publish your bot token. If a token has been shared publicly, reset it in the [Discord Developer Portal](https://discord.com/developers/applications) immediately.

## ✨ Features

<table>
  <tr>
    <td width="50%">
      <h3>🎫 Interactive Ticket System</h3>
      <ul>
        <li>Dropdown menu for <b>General Query</b> and <b>Server Job</b></li>
        <li>Modal forms collect the details before a ticket is created</li>
        <li>Private ticket channels with owner/staff access</li>
        <li>Claim, lock, unlock, transcript, and close controls</li>
        <li>HTML transcript export</li>
        <li>Prevents a member from opening another ticket while one is recorded</li>
      </ul>
    </td>
    <td width="50%">
      <h3>🛡️ Moderation Tools</h3>
      <ul>
        <li>Kick and ban members</li>
        <li>Timeout and remove timeouts</li>
        <li>Purge recent messages</li>
        <li>Configure channel slowmode</li>
        <li>Send warnings by DM</li>
      </ul>
    </td>
  </tr>
  <tr>
    <td width="50%">
      <h3>👋 Welcome Cards</h3>
      <ul>
        <li>Creates a personalized welcome image</li>
        <li>Displays the member's avatar, name, and member count</li>
        <li>Uses an optional custom background image</li>
        <li>Includes links to server information channels</li>
      </ul>
    </td>
    <td width="50%">
      <h3>🔊 Voice & Staff Controls</h3>
      <ul>
        <li>Lock and unlock voice-channel access</li>
        <li>Configure up to three staff roles</li>
        <li>Persist ticket and lock state in a local JSON file</li>
        <li>Admin-only bot username and avatar commands</li>
        <li>Server, user, and avatar information commands</li>
      </ul>
    </td>
  </tr>
</table>

## 🧰 Requirements

- Python **3.10+** recommended
- A Discord application and bot account
- `discord.py` 2.x with application-command and UI support
- `Pillow` for generated welcome images
- The bot's required Discord permissions and gateway intents

## 🚀 Installation

### 1. Clone or download the project

If the code is in a Git repository:

```bash
git clone https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
cd YOUR-REPOSITORY
```

Or download the source code and open a terminal in its folder.

### 2. Create a virtual environment

**Linux / Kali Linux / macOS**
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

**Windows (PowerShell)**
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

### 3. Install dependencies

```bash
python -m pip install -U discord.py Pillow
```

`Pillow` is used for welcome-card image generation. If you do not want welcome images, the code will need to be adjusted to make that dependency optional at runtime.

### 4. Configure the bot token

**Do not hard-code the token in your source file.** Replace the token constant with an environment variable:

```python
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError("Set the DISCORD_TOKEN environment variable first")
```

Then set it before running the bot.

**Linux / Kali Linux / macOS**
```bash
export DISCORD_TOKEN="YOUR_NEW_BOT_TOKEN"
python bot.py
```

**Windows PowerShell**
```powershell
$env:DISCORD_TOKEN = "YOUR_NEW_BOT_TOKEN"
python bot.py
```

> If your current source file contains a real token, reset it in the Discord Developer Portal before using the bot again. Do not commit `.env` files or tokens to Git.

## ⚙️ Configuration

### Discord Developer Portal

Open the [Discord Developer Portal](https://discord.com/developers/applications), select your application, and configure:

1. **Bot:** Reset/copy the bot token securely.
2. **Bot → Privileged Gateway Intents:** Enable **Server Members Intent** and **Message Content Intent** if your bot needs them.
3. **OAuth2 → URL Generator:** Select the `bot` and `applications.commands` scopes.
4. Grant only the permissions the bot needs. Ticket creation and channel/voice controls require **Manage Channels**; moderation actions require their corresponding permissions.

### Invite permissions checklist

Depending on which features you use, the bot may need:

- View Channels
- Send Messages
- Read Message History
- Embed Links
- Attach Files
- Manage Channels
- Manage Messages
- Kick Members
- Ban Members
- Moderate Members
- Connect (only if additional voice features need it)

The bot's role must be high enough in the server role hierarchy to moderate the intended members. Avoid granting Administrator unless you deliberately accept that risk.

### Set staff roles

1. Invite the bot and make sure it can see the channels where you will configure it.
2. Run `/setup` as a server administrator.
3. Choose the required staff roles in `role1`, with optional `role2` and `role3`.
4. Use `/staffroles` to verify the configured roles.

The configuration is stored in `bot_data.json` beside the Python script. Keep this file if you want to preserve saved bot state across restarts.

### Post the ticket panel

1. Go to the channel where members should open tickets.
2. Run `/ticketpanel` as an administrator.
3. Members select **General Query** or **Server Job** and complete the form.
4. Staff use the buttons in the ticket channel to manage it.

### Welcome image background (optional)

Place an image named `background.png` in the same folder as the Python script. The bot uses it as the welcome-card background. If the file is absent, the code generates a red-and-black fallback background.

## 📚 Commands

| Command | Access / Requirement | Description |
|---|---|---|
| `/help` | Everyone | Show the help menu |
| `/ping` | Everyone | Check bot latency |
| `/serverinfo` | Server | Show server statistics |
| `/userinfo` | Everyone | Show information about a member |
| `/avatar` | Everyone | Display a member's avatar |
| `/renamebot name:` | Administrator | Change the bot username |
| `/setpfp image:` | Administrator | Change the bot profile picture |
| `/setup role1: [role2:] [role3:]` | Administrator | Configure staff roles |
| `/staffroles` | Administrator | Show configured staff roles |
| `/ticketpanel` | Administrator | Post the ticket dropdown panel |
| `/close` | Ticket owner or staff | Close and delete the current ticket |
| `/kick member: [reason:]` | Requires Kick Members | Kick a member |
| `/ban member: [reason:]` | Requires Ban Members | Ban a member |
| `/timeout member: minutes: [reason:]` | Requires Moderate Members | Timeout a member |
| `/untimeout member:` | Requires Moderate Members | Remove a timeout |
| `/purge amount:` | Requires Manage Messages | Delete up to 100 recent messages |
| `/slowmode seconds:` | Requires Manage Channels | Set channel slowmode (0–21600 seconds) |
| `/warn member: [reason:]` | Requires Manage Messages | Attempt to DM a warning |
| `/lockvc` | Configured staff role or Administrator | Prevent members from connecting to your current voice channel |
| `/unlockvc` | Configured staff role or Administrator | Restore the default role's voice-channel connect permission |

### 🎛️ Ticket buttons

| Button | Purpose |
|---|---|
| **Claim Ticket** | Assigns the ticket to a staff member |
| **Lock Ticket** | Restricts configured staff-role visibility after a ticket is claimed |
| **Unlock Ticket** | Restores configured staff-role access |
| **Transcript** | Creates an HTML transcript file |
| **Close Ticket** | Deletes the ticket after a short delay |

### 🧾 Ticket form types

- **💬 General Query** — asks for a written description of the issue.
- **🛠️ Server Job** — asks for a server name and the job requirements.

## 💾 Saved data

The bot stores state in `bot_data.json`, including configured staff roles, ticket ownership and claims, ticket locks, voice locks, and ticket counters.

- Keep `bot_data.json` alongside the bot script.
- Back it up before changing deployments.
- Do not edit it while the bot is running unless you know how the state is managed.
- If a ticket channel is deleted while the bot is offline, the bot attempts to clean up stale ticket records when it starts.

## ▶️ Run the bot

Save your Python script as `bot.py` (or adjust the command to match your filename), activate the virtual environment, set `DISCORD_TOKEN`, and run:

```bash
python bot.py
```

On startup, the bot logs in, registers persistent ticket views, attempts to recover ticket ownership from channel topics, and syncs slash commands.

## 🧯 Troubleshooting

<details>
  <summary><b>Slash commands do not appear</b></summary>

  - Confirm the bot was invited with the `applications.commands` scope.
  - Check the terminal for command-sync errors.
  - Restart the bot and allow Discord a little time to refresh the command list.
</details>

<details>
  <summary><b>Ticket creation fails</b></summary>

  - Check the bot has Manage Channels, View Channels, Send Messages, Embed Links, and Read Message History permissions.
  - Make sure the configured staff roles still exist.
  - Check the terminal for `discord.Forbidden` or HTTP errors.
</details>

<details>
  <summary><b>Welcome card fails</b></summary>

  - Install Pillow: `python -m pip install Pillow`.
  - Verify the bot can access the welcome channel and attach files.
  - Optionally add `background.png` beside the script.
</details>

<details>
  <summary><b>Bot is stuck on “thinking”</b></summary>

  - For deferred slash commands, ensure the code eventually sends a follow-up or edits the original response.
  - Check the terminal for exceptions and Discord API errors.
</details>

<details>
  <summary><b>Profile update or rename fails</b></summary>

  - Check for Discord HTTP errors and rate limits.
  - Username changes may be rate-limited by Discord.
  - Keep the token private and reset it immediately if exposed.
</details>

## 🔒 Security notes

- Store your bot token in an environment variable or a secrets manager.
- Never upload `bot_data.json` if it contains sensitive server information.
- Grant only the permissions needed by the features you enable.
- Keep dependencies updated and review permissions before deploying publicly.

## 🤝 Contributing

Issues and pull requests are welcome if this project is hosted in a public repository. Before opening a pull request, describe the change and test the relevant command or interaction in a private test server.

## 📄 License

No license is specified in the supplied source. Add a `LICENSE` file before presenting the project as open source.

---

<div align="center">

**Built for Team GG 🔴⚫**

<sub>If this bot helps your server, consider starring the repository ⭐</sub>

</div>
