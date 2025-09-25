import os
import sys
import json
import asyncio
import platform
import requests
import websockets
import time
from colorama import init, Fore
from keep_alive import keep_alive

init(autoreset=True)

status = "idle"  # online/dnd/idle
custom_status = "A geometria é única e eterna; ela é um reflexo do pensamento de Deus"  # Custom Status
usertoken = os.getenv("TOKEN")

if not usertoken:
    print(f"{Fore.WHITE}[{Fore.RED}-{Fore.WHITE}] Please add a token inside Secrets.")
    sys.exit()

headers = {"Authorization": usertoken, "Content-Type": "application/json"}
validate = requests.get("https://canary.discordapp.com/api/v9/users/@me", headers=headers)

if validate.status_code != 200:
    print(f"{Fore.WHITE}[{Fore.RED}-{Fore.WHITE}] Your token might be invalid. Please check it again.")
    sys.exit()

userinfo = requests.get("https://canary.discordapp.com/api/v9/users/@me", headers=headers).json()
username = userinfo["username"]
discriminator = userinfo["discriminator"]
userid = userinfo["id"]

class RateLimiter:
    def __init__(self, max_attempts=5, window=60):
        self.max_attempts = max_attempts
        self.window = window
        self.attempts = []
    
    def should_allow(self):
        now = time.time()
        # Remove attempts outside the current window
        self.attempts = [attempt for attempt in self.attempts if now - attempt < self.window]
        
        if len(self.attempts) < self.max_attempts:
            self.attempts.append(now)
            return True
        return False

limiter = RateLimiter()

async def onliner(token, status):
    async with websockets.connect("wss://gateway.discord.gg/?v=9&encoding=json") as ws:
        start = json.loads(await ws.recv())
        heartbeat = start["d"]["heartbeat_interval"]
        
        # Optimized auth payload - combined presence and status
        auth = {
            "op": 2,
            "d": {
                "token": token,
                "properties": {
                    "$os": "Windows 10",
                    "$browser": "Google Chrome",
                    "$device": "Windows",
                },
                "presence": {
                    "status": status,
                    "afk": False,
                    "since": 0,
                    "activities": [{
                        "type": 4,
                        "state": custom_status,
                        "name": "Custom Status",
                        "id": "custom",
                        # Uncomment the below lines if you want an emoji in the status
                        #"emoji": {
                        #    "name": "emoji name",
                        #    "id": "emoji id",
                        #    "animated": False,
                        #},
                    }]
                },
            },
        }
        
        await ws.send(json.dumps(auth))
        
        # Simplified heartbeat payload
        online = {"op": 1, "d": None}  # Use None instead of "None"
        
        while True:
            try:
                # Receive any incoming messages to keep connection alive
                message = await asyncio.wait_for(ws.recv(), timeout=heartbeat / 1000)
                data = json.loads(message)
                
                if data.get('op') == 10:  # Hello message
                    heartbeat = data['d']['heartbeat_interval']
                
            except asyncio.TimeoutError:
                # Send heartbeat
                await ws.send(json.dumps(online))
            
            except websockets.exceptions.ConnectionClosed:
                break
            
            await asyncio.sleep(heartbeat / 1000)

async def run_onliner():
    if platform.system() == "Windows":
        os.system("cls")
    else:
        os.system("clear")
    print(f"{Fore.WHITE}[{Fore.LIGHTGREEN_EX}+{Fore.WHITE}] Logged in as {Fore.LIGHTBLUE_EX}{username} {Fore.WHITE}({userid})!")
    
    while True:
        if limiter.should_allow():
            try:
                await onliner(usertoken, status)
            except Exception as e:
                print(f"{Fore.WHITE}[{Fore.RED}-{Fore.WHITE}] Connection error: {e}")
                wait_time = 30
                print(f"{Fore.WHITE}[{Fore.YELLOW}*{Fore.WHITE}] Reconnecting in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
        else:
            print(f"{Fore.WHITE}[{Fore.RED}-{Fore.WHITE}] Rate limit exceeded. Waiting 60 seconds...")
            await asyncio.sleep(60)

# Keep the server alive
keep_alive()

# Run with error handling
try:
    asyncio.run(run_onliner())
except KeyboardInterrupt:
    print(f"\n{Fore.WHITE}[{Fore.YELLOW}*{Fore.WHITE}] Bot stopped by user")
except Exception as e:
    print(f"{Fore.WHITE}[{Fore.RED}-{Fore.WHITE}] Fatal error: {e}")
