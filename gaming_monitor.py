#!/usr/bin/env python3
import os
import time
import requests
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Setup logging
log_dir = Path("/app/logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "gaming_monitor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# PLATFORM HANDLERS
# ============================================================================

class PlatformHandler:
    """Base class for platform handlers"""
    def __init__(self, config: dict, monitor_name: str):
        self.config = config
        self.monitor_name = monitor_name
        self.username = config.get('username')
        self.track_mode = config.get('track_mode', 'any_game')
        self.games_to_track = [g.lower() for g in config.get('games', [])]
        self.ignore_mobile = config.get('ignore_mobile', True)
        self.currently_playing = False
        self.current_game = None
        self.session_start = None
        self.logger = logging.getLogger(f"{self.__class__.__name__}:{monitor_name}")
    
    def check_status(self) -> Dict:
        """Check gaming status - to be implemented by subclasses"""
        raise NotImplementedError
    
    def should_track_game(self, game_title: str) -> bool:
        """Determine if we should track this game"""
        if not game_title:
            return False
        
        game_lower = game_title.lower()
        
        if self.track_mode == "any_game":
            self.logger.debug(f"Track mode: any_game - accepting '{game_title}'")
            return True
        elif self.track_mode == "specific_games":
            matches = any(tracked in game_lower for tracked in self.games_to_track)
            self.logger.debug(f"Track mode: specific_games - '{game_title}' matches: {matches}")
            return matches
        elif self.track_mode == "online_status":
            self.logger.debug(f"Track mode: online_status - ignoring game '{game_title}'")
            return False
        
        return False

class PSNHandler(PlatformHandler):
    """PlayStation Network handler"""
    def __init__(self, config: dict, monitor_name: str):
        super().__init__(config, monitor_name)
        self.npsso_token = config['auth'].get('npsso_token')
        if not self.npsso_token:
            raise ValueError(f"PSN monitor '{monitor_name}' missing npsso_token")
        
        try:
            from psnawp_api import PSNAWP
            self.psnawp = PSNAWP(self.npsso_token)
            self.logger.info(f"✅ PSN initialized for {self.username}")
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize PSN: {e}")
            raise
    
    def check_status(self) -> Dict:
        """Check PSN gaming status"""
        try:
            self.logger.debug(f"Fetching presence for {self.username}...")
            user = self.psnawp.user(online_id=self.username)
            presence = user.get_presence()
            
            basic_presence = presence.get('basicPresence', {})
            primary_platform = basic_presence.get('primaryPlatformInfo', {})
            
            online_status = primary_platform.get('onlineStatus', 'offline')
            platform = primary_platform.get('platform', 'Unknown')
            
            self.logger.info(f"📊 PSN Status: {online_status} on {platform}")
            
            # Check if mobile (ignore if configured)
            if self.ignore_mobile and platform in ['PS App', 'Mobile']:
                self.logger.info(f"🚫 Ignoring mobile presence for {self.username}")
                return {
                    'online': False,
                    'playing': False,
                    'game': None,
                    'platform': platform
                }
            
            result = {
                'online': online_status == 'online',
                'playing': False,
                'game': None,
                'platform': platform
            }
            
            if online_status == 'online':
                game_status = basic_presence.get('gameTitleInfoList', [])
                self.logger.debug(f"Game list: {game_status}")
                
                if game_status:
                    game_title = game_status[0].get('titleName', '')
                    self.logger.info(f"🎮 Currently playing: {game_title}")
                    
                    if self.track_mode == "online_status":
                        result['playing'] = True
                        result['game'] = "Online"
                        self.logger.info(f"✅ Online status mode - tracking as 'Online'")
                    elif self.should_track_game(game_title):
                        result['playing'] = True
                        result['game'] = game_title
                        self.logger.info(f"✅ Game matched tracking rules!")
                    else:
                        self.logger.info(f"❌ Game not in tracking list")
                else:
                    self.logger.info(f"ℹ️ Online but not playing any game")
            else:
                self.logger.info(f"⚫ User is offline")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error checking PSN status: {e}", exc_info=True)
            return {'online': False, 'playing': False, 'game': None, 'platform': 'Error'}

class XboxHandler(PlatformHandler):
    """Xbox Live handler using OpenXBL API"""
    def __init__(self, config: dict, monitor_name: str):
        super().__init__(config, monitor_name)
        self.api_key = config['auth'].get('api_key')
        if not self.api_key:
            raise ValueError(f"Xbox monitor '{monitor_name}' missing api_key")
        
        self.base_url = "https://xbl.io/api/v2"
        self.headers = {
            "X-Authorization": self.api_key,
            "Accept": "application/json"
        }
        self.logger.info(f"✅ Xbox initialized for {self.username}")
    
    def check_status(self) -> Dict:
        """Check Xbox Live gaming status"""
        try:
            self.logger.debug(f"Fetching Xbox presence for {self.username}...")
            response = requests.get(
                f"{self.base_url}/friends/search?gt={self.username}",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code != 200:
                self.logger.warning(f"Xbox API returned {response.status_code}")
                return {'online': False, 'playing': False, 'game': None, 'platform': 'Xbox'}
            
            data = response.json()
            
            if not data.get('people'):
                self.logger.info(f"⚫ Xbox user not found or offline")
                return {'online': False, 'playing': False, 'game': None, 'platform': 'Xbox'}
            
            user_data = data['people'][0]
            presence_state = user_data.get('presenceState', 'Offline')
            
            self.logger.info(f"📊 Xbox Status: {presence_state}")
            
            result = {
                'online': presence_state == 'Online',
                'playing': False,
                'game': None,
                'platform': 'Xbox'
            }
            
            if presence_state == 'Online':
                presence_text = user_data.get('presenceText', '')
                self.logger.info(f"🎮 Xbox presence: {presence_text}")
                
                if self.track_mode == "online_status":
                    result['playing'] = True
                    result['game'] = "Online"
                    self.logger.info(f"✅ Online status mode - tracking as 'Online'")
                elif presence_text and self.should_track_game(presence_text):
                    result['playing'] = True
                    result['game'] = presence_text
                    self.logger.info(f"✅ Game matched tracking rules!")
                else:
                    self.logger.info(f"❌ Game not in tracking list")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error checking Xbox status: {e}", exc_info=True)
            return {'online': False, 'playing': False, 'game': None, 'platform': 'Xbox'}

class SteamHandler(PlatformHandler):
    """Steam handler using Steam Web API"""
    def __init__(self, config: dict, monitor_name: str):
        super().__init__(config, monitor_name)
        self.api_key = config['auth'].get('api_key')
        if not self.api_key:
            raise ValueError(f"Steam monitor '{monitor_name}' missing api_key")
        
        self.steam_id = self.username  # Should be Steam64 ID
        self.base_url = "https://api.steampowered.com"
        self.logger.info(f"✅ Steam initialized for {self.steam_id}")
    
    def check_status(self) -> Dict:
        """Check Steam gaming status"""
        try:
            self.logger.debug(f"Fetching Steam presence for {self.steam_id}...")
            response = requests.get(
                f"{self.base_url}/ISteamUser/GetPlayerSummaries/v0002/",
                params={
                    'key': self.api_key,
                    'steamids': self.steam_id
                },
                timeout=10
            )
            
            if response.status_code != 200:
                self.logger.warning(f"Steam API returned {response.status_code}")
                return {'online': False, 'playing': False, 'game': None, 'platform': 'Steam'}
            
            data = response.json()
            players = data.get('response', {}).get('players', [])
            
            if not players:
                self.logger.info(f"⚫ Steam user not found or private profile")
                return {'online': False, 'playing': False, 'game': None, 'platform': 'Steam'}
            
            player = players[0]
            persona_state = player.get('personastate', 0)  # 0=Offline, 1=Online, etc.
            persona_name = player.get('personaname', 'Unknown')
            
            state_names = {0: 'Offline', 1: 'Online', 2: 'Busy', 3: 'Away', 4: 'Snooze', 5: 'Looking to trade', 6: 'Looking to play'}
            state_text = state_names.get(persona_state, 'Unknown')
            
            self.logger.info(f"📊 Steam Status: {persona_name} - {state_text}")
            
            result = {
                'online': persona_state > 0,
                'playing': False,
                'game': None,
                'platform': 'Steam'
            }
            
            if persona_state > 0:
                game_name = player.get('gameextrainfo')
                
                if game_name:
                    self.logger.info(f"🎮 Currently playing: {game_name}")
                else:
                    self.logger.info(f"ℹ️ Online but not playing any game")
                
                if self.track_mode == "online_status":
                    result['playing'] = True
                    result['game'] = "Online"
                    self.logger.info(f"✅ Online status mode - tracking as 'Online'")
                elif game_name and self.should_track_game(game_name):
                    result['playing'] = True
                    result['game'] = game_name
                    self.logger.info(f"✅ Game matched tracking rules!")
                else:
                    if game_name:
                        self.logger.info(f"❌ Game not in tracking list")
            else:
                self.logger.info(f"⚫ User is offline")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error checking Steam status: {e}", exc_info=True)
            return {'online': False, 'playing': False, 'game': None, 'platform': 'Steam'}

# ============================================================================
# NOTIFICATION SYSTEM
# ============================================================================

class NotificationManager:
    """Handle all notifications with per-monitor override support"""
    def __init__(self, global_config: dict, monitor_config: dict = None, monitor_name: str = ""):
        """
        Initialize with global config and optional per-monitor override
        
        Args:
            global_config: Global notification settings
            monitor_config: Monitor-specific notification settings (overrides global)
            monitor_name: Name of the monitor for logging
        """
        self.monitor_name = monitor_name
        
        # Check for monitor-specific overrides
        if monitor_config and monitor_config.get('notifications'):
            monitor_notif = monitor_config['notifications']
            self.discord_webhook = monitor_notif.get('discord_webhook', '').strip()
            self.uptime_kuma_url = monitor_notif.get('uptime_kuma_push_url', '').strip()
            logger.info(f"🔧 {monitor_name}: Using custom notification settings")
        else:
            # Use global settings
            self.discord_webhook = global_config.get('discord_webhook', '').strip()
            self.uptime_kuma_url = global_config.get('uptime_kuma_push_url', '').strip()
            logger.info(f"🌐 {monitor_name}: Using global notification settings")
        
        # Validate URLs
        if self.discord_webhook and not self.discord_webhook.startswith('http'):
            logger.warning(f"{monitor_name}: Invalid Discord webhook, disabling")
            self.discord_webhook = None
        
        if self.uptime_kuma_url and not self.uptime_kuma_url.startswith('http'):
            logger.warning(f"{monitor_name}: Invalid Uptime Kuma URL, disabling")
            self.uptime_kuma_url = None
        
        logger.info(f"   Discord: {'✅' if self.discord_webhook else '❌'} | Uptime Kuma: {'✅' if self.uptime_kuma_url else '❌'}")
    
    def send_alert(self, message: str, color: int = 3447003):
        """Send Discord alert"""
        if not self.discord_webhook:
            return
        
        try:
            payload = {
                "embeds": [{
                    "title": f"🎮 {self.monitor_name}",
                    "description": message,
                    "color": color,
                    "timestamp": datetime.utcnow().isoformat(),
                    "footer": {"text": "Gaming Monitor"}
                }]
            }
            response = requests.post(self.discord_webhook, json=payload, timeout=10)
            if response.status_code == 204:
                logger.info(f"✅ Discord alert sent for {self.monitor_name}")
        except Exception as e:
            logger.error(f"❌ Discord error for {self.monitor_name}: {e}")
    
    def send_heartbeat(self, is_playing: bool):
        """Send Uptime Kuma heartbeat"""
        if not self.uptime_kuma_url:
            return
        
        try:
            status = "up" if is_playing else "down"
            msg = "Playing" if is_playing else "Not Playing"
            
            base_url = self.uptime_kuma_url.split('?')[0]
            url = f"{base_url}?status={status}&msg={msg}"
            
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                logger.info(f"{'💚' if is_playing else '🔴'} Heartbeat: {self.monitor_name} - {msg}")
        except Exception as e:
            logger.error(f"❌ Uptime Kuma error for {self.monitor_name}: {e}")

# ============================================================================
# MAIN MONITOR
# ============================================================================

class GamingMonitor:
    """Main gaming monitor coordinating all platforms"""
    def __init__(self, config_path: str = "/app/config.json"):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        self.check_interval = self.config.get('check_interval', 30)
        self.global_notifications = self.config.get('notifications', {})
        self.handlers: List[tuple] = []  # List of (handler, notifier) tuples
        
        # Initialize platform handlers with their notification managers
        for monitor_config in self.config.get('monitors', []):
            if not monitor_config.get('enabled', False):
                logger.info(f"⏭️ Skipping disabled monitor: {monitor_config.get('name', 'Unknown')}")
                continue
            
            platform = monitor_config.get('platform', '').lower()
            name = monitor_config.get('name', 'Unknown')
            
            try:
                # Create platform handler
                if platform == 'psn':
                    handler = PSNHandler(monitor_config, name)
                elif platform == 'xbox':
                    handler = XboxHandler(monitor_config, name)
                elif platform == 'steam':
                    handler = SteamHandler(monitor_config, name)
                else:
                    logger.warning(f"Unknown platform: {platform}")
                    continue
                
                # Create notification manager for this monitor
                notifier = NotificationManager(
                    self.global_notifications,
                    monitor_config,
                    name
                )
                
                self.handlers.append((handler, notifier))
                logger.info(f"✅ Loaded monitor: {name} ({platform})")
                
            except Exception as e:
                logger.error(f"❌ Failed to load {name}: {e}")
        
        if not self.handlers:
            raise ValueError("No valid monitors configured!")
        
        logger.info(f"📊 Total monitors: {len(self.handlers)}")
    
    def check_all(self):
        """Check all monitors"""
        for handler, notifier in self.handlers:
            try:
                logger.info(f"🔍 Checking {handler.monitor_name}...")
                status = handler.check_status()
                
                # Check for state changes
                was_playing = handler.currently_playing
                is_playing = status['playing']
                
                logger.info(f"   Was playing: {was_playing} | Is playing: {is_playing}")
                
                # Send heartbeat using monitor-specific notifier
                notifier.send_heartbeat(is_playing)
                
                # Send alerts on state changes
                if is_playing and not was_playing:
                    # Started playing
                    game = status['game']
                    platform = status['platform']
                    message = f"🎮 {handler.username} started playing **{game}** on {platform}!"
                    notifier.send_alert(message, color=5763719)
                    handler.session_start = datetime.now()
                    logger.info(f"🚀 {handler.monitor_name}: Started playing {game}")
                    
                elif not is_playing and was_playing:
                    # Stopped playing
                    duration = datetime.now() - handler.session_start if handler.session_start else None
                    minutes = duration.seconds // 60 if duration else 0
                    message = f"🛑 {handler.username} stopped playing **{handler.current_game}**"
                    if minutes > 0:
                        message += f"\nSession duration: {minutes} minutes"
                    notifier.send_alert(message, color=15844367)
                    logger.info(f"🛑 {handler.monitor_name}: Stopped playing (Duration: {minutes}min)")
                
                # Update state
                handler.currently_playing = is_playing
                handler.current_game = status['game']
                
            except Exception as e:
                logger.error(f"❌ Error checking {handler.monitor_name}: {e}", exc_info=True)
    
    def run(self):
        """Main monitoring loop"""
        logger.info("=" * 60)
        logger.info("🚀 MULTI-PLATFORM GAMING MONITOR STARTING")
        logger.info("=" * 60)
        logger.info(f"⏱️ Check interval: {self.check_interval}s")
        logger.info(f"🎮 Active monitors: {len(self.handlers)}")
        logger.info("=" * 60)
        
        check_count = 0
        
        while True:
            try:
                check_count += 1
                logger.info(f"━━━ Check #{check_count} ━━━")
                self.check_all()
                logger.info(f"💤 Sleeping for {self.check_interval} seconds...")
                time.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                logger.info("⚠️ Shutting down...")
                break
            except Exception as e:
                logger.error(f"❌ Main loop error: {e}", exc_info=True)
                time.sleep(self.check_interval * 2)

# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    try:
        monitor = GamingMonitor()
        monitor.run()
    except Exception as e:
        logger.critical(f"🚨 Fatal error: {e}", exc_info=True)
        exit(1)
