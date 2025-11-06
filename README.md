# MultiplatformGamingMonitor 🎮 Multi-Platform Gaming Monitor

Real-time gaming activity monitor for PlayStation Network, Xbox Live, and Steam with Discord and Uptime Kuma notifications.

---

## 📋 Quick Start

1. Create `config.json` with your settings
2. Run: `docker-compose up -d`
3. View logs: `docker-compose logs -f`

---

## 🎛️ Configuration

All settings go in `config.json`.

### Global Settings

{
"check_interval": 30,
"notifications": {
"discord_webhook": "https://discord.com/api/webhooks/YOUR_WEBHOOK",
"uptime_kuma_push_url": "https://uptime.wakxi.com/api/push/YOUR_KEY"
},
"monitors": []
}

text

| Setting | Type | Required | Description |
|---------|------|----------|-------------|
| `check_interval` | number | ✅ | Seconds between each check (30-60 recommended) |
| `discord_webhook` | string | ❌ | Discord webhook URL for gaming alerts (empty to disable) |
| `uptime_kuma_push_url` | string | ❌ | Uptime Kuma push URL for status monitoring (empty to disable) |

---

## 📱 Monitor Settings

Each monitor tracks one user on one platform.

### Basic Monitor Structure

{
"monitors": [
{
"name": "Display Name",
"enabled": true,
"platform": "psn",
"username": "username_here",
"auth": {
"npsso_token": "token_here"
},
"track_mode": "specific_games",
"games": ["Game 1", "Game 2"],
"ignore_mobile": true
}
]
}

text

### Monitor Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | ✅ | Display name (used in notifications) |
| `enabled` | boolean | ✅ | `true` to monitor, `false` to skip |
| `platform` | string | ✅ | `psn`, `xbox`, or `steam` |
| `username` | string | ✅ | Platform username/ID |
| `auth` | object | ✅ | Authentication credentials (platform-specific) |
| `track_mode` | string | ✅ | `specific_games`, `any_game`, or `online_status` |
| `games` | array | ❌ | Games to track (required for `specific_games` mode) |
| `ignore_mobile` | boolean | ❌ | Ignore mobile/phone activity (PSN only) |
| `notifications` | object | ❌ | Override global notifications for this monitor |

---

## 🎯 Track Modes

### `specific_games`
Track only when playing specific games.

{
"track_mode": "specific_games",
"games": ["Battlefield 6", "Call of Duty", "Fortnite"]
}

text

**What it does:**
- Sends alerts ONLY when user plays games in your list
- Ignores all other games
- Case-insensitive matching

---

### `any_game`
Track whenever any game is being played.

{
"track_mode": "any_game"
}

text

**What it does:**
- Sends alerts for ANY game activity
- No game list needed
- Ignores online-but-not-gaming status

---

### `online_status`
Track only online/offline status, not specific games.

{
"track_mode": "online_status"
}

text

**What it does:**
- Sends alerts when user goes online/offline
- Ignores which game they're playing
- Useful for simple presence monitoring

---

## 🔐 Platform Authentication

### PlayStation Network (PSN)

{
"platform": "psn",
"username": "your_psn_id",
"auth": {
"npsso_token": "64_character_token_here"
}
}

text

**How to get NPSSO token:**
1. Go to https://www.playstation.com/
2. Sign in
3. Visit: https://ca.account.sony.com/api/v1/ssocookie
4. Copy the `npsso` value
5. Tokens expire after ~2 months

**Note:** `ignore_mobile: true` will ignore PS App/mobile logins

---

### Xbox Live

{
"platform": "xbox",
"username": "YourGamertag",
"auth": {
"api_key": "openxbl_api_key_here"
}
}

text

**How to get API key:**
1. Go to https://xbl.io/
2. Create free account
3. Get API key from Profile
4. Free tier: 120 requests/hour

---

### Steam

{
"platform": "steam",
"username": "76561198XXXXXXXXX",
"auth": {
"api_key": "steam_api_key_here"
}
}

text

**How to get Steam ID:**
1. Visit https://steamid.io/
2. Enter your Steam profile URL
3. Copy the **Steam64 ID** (looks like `76561198...`)

**How to get API key:**
1. Go to https://steamcommunity.com/dev/apikey
2. Sign in with Steam
3. Register API key (domain: `localhost`)

**Important:** Steam profile must be **PUBLIC**

---

## 🔔 Notifications

### Global Notifications

Set default Discord and Uptime Kuma for all monitors:

{
"notifications": {
"discord_webhook": "https://discord.com/api/webhooks/GLOBAL_CHANNEL",
"uptime_kuma_push_url": "https://uptime.example.com/api/push/KEY"
}
}

text

### Per-Monitor Notifications (Override)

Use different notifications for specific monitors:

{
"name": "Child's PlayStation",
"enabled": true,
"platform": "psn",
"username": "child_psn",
"auth": { "npsso_token": "..." },
"track_mode": "specific_games",
"games": ["Fortnite"],
"notifications": {
"discord_webhook": "https://discord.com/api/webhooks/PARENTS_PRIVATE_CHANNEL",
"uptime_kuma_push_url": "https://uptime.example.com/api/push/CUSTOM_KEY"
}
}

text

**What this does:**
- This monitor sends alerts to `PARENTS_PRIVATE_CHANNEL`
- Uses custom Uptime Kuma endpoint
- Other monitors use global settings

### Discord Webhook Setup

1. Open Discord Server
2. Server Settings → Integrations → Webhooks
3. Create New Webhook
4. Copy URL

---

## 📊 Uptime Kuma Setup

### Create Monitor

1. In Uptime Kuma, create **Push** monitor
2. Copy the push URL
3. Add to `config.json`

### Recommended Settings

| Setting | Value | Why |
|---------|-------|-----|
| Heartbeat Interval | 180 seconds | Prevents false alerts (3x check_interval) |
| Retries | 0 | Immediate status changes |
| Upside Down Mode | OFF | `down` = not playing, `up` = playing |

### Status Meaning

- **🟢 Green (Up)**: User is playing tracked game
- **🔴 Red (Down)**: User is NOT playing or offline

---

## 📝 Complete Example Configs

### Example 1: Parent Monitoring Child

{
"check_interval": 30,
"notifications": {
"discord_webhook": "",
"uptime_kuma_push_url": ""
},
"monitors": [
{
"name": "Child's PlayStation",
"enabled": true,
"platform": "psn",
"username": "child_gamer123",
"auth": {
"npsso_token": "YOUR_NPSSO_TOKEN"
},
"track_mode": "specific_games",
"games": ["Fortnite", "Minecraft", "Roblox"],
"ignore_mobile": true,
"notifications": {
"discord_webhook": "https://discord.com/api/webhooks/PARENTS_CHANNEL",
"uptime_kuma_push_url": "https://uptime.example.com/api/push/CHILD_KEY"
}
}
]
}

text

---

### Example 2: Friend Group Activity Tracker

{
"check_interval": 60,
"notifications": {
"discord_webhook": "https://discord.com/api/webhooks/GAMING_GROUP",
"uptime_kuma_push_url": "https://uptime.example.com/api/push/GROUP_KEY"
},
"monitors": [
{
"name": "John - Steam",
"enabled": true,
"platform": "steam",
"username": "76561198012345678",
"auth": {
"api_key": "STEAM_API_KEY"
},
"track_mode": "any_game"
},
{
"name": "Sarah - PlayStation",
"enabled": true,
"platform": "psn",
"username": "sarah_gaming",
"auth": {
"npsso_token": "NPSSO_TOKEN"
},
"track_mode": "any_game",
"ignore_mobile": true
},
{
"name": "Mike - Xbox",
"enabled": true,
"platform": "xbox",
"username": "MikeGamer123",
"auth": {
"api_key": "OPENXBL_API_KEY"
},
"track_mode": "specific_games",
"games": ["Call of Duty", "Halo", "Fortnite"]
}
]
}

text

---

### Example 3: Separate Channels Per Platform

{
"check_interval": 45,
"notifications": {
"discord_webhook": "",
"uptime_kuma_push_url": ""
},
"monitors": [
{
"name": "PlayStation Users",
"enabled": true,
"platform": "psn",
"username": "player_psn",
"auth": {
"npsso_token": "TOKEN"
},
"track_mode": "any_game",
"notifications": {
"discord_webhook": "https://discord.com/api/webhooks/PSN_CHANNEL"
}
},
{
"name": "Xbox Players",
"enabled": true,
"platform": "xbox",
"username": "XboxGamer",
"auth": {
"api_key": "KEY"
},
"track_mode": "any_game",
"notifications": {
"discord_webhook": "https://discord.com/api/webhooks/XBOX_CHANNEL"
}
}
]
}

text

---

## 🚀 Deployment

### Docker Compose

docker-compose up -d

text

### View Logs

docker-compose logs -f

text

### Restart

docker-compose restart

text

### Rebuild

docker-compose build --no-cache
docker-compose up -d

text

---

## ⚠️ Important Notes

- **JSON Syntax**: Use double quotes `"`, not single quotes `'`
- **No Comments**: JSON doesn't support `//` or `#` comments
- **Token Security**: Keep tokens private; use `.gitignore`
- **API Limits**: 
  - Steam: 100,000 calls/day (shared)
  - Xbox: 120 requests/hour (free tier)
  - PSN: No official limits
- **Check Interval**: Recommended 30-60 seconds (balances updates vs. API usage)

---

## 🔍 Troubleshooting

### Monitor not detecting games
- Verify username is correct
- Check track_mode and games list
- View detailed logs: `docker-compose logs -f`

### Notifications not sending
- Verify webhook URLs are complete
- Check Discord/Uptime Kuma server settings
- Ensure monitor is `enabled: true`

### Authentication errors
- Refresh tokens (NPSSO expires ~2 months)
- Verify API keys are correct
- Check Steam profile is public

---

## 📄 License

MIT License - Free to use and modify

---

**Version**: 1.0  
**Last Updated**: November 2025
