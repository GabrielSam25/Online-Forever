import os
import sys
import json
import asyncio
import platform
import requests
import websockets
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

validate = requests.get("https://discord.com/api/v9/users/@me", headers=headers)
if validate.status_code != 200:
    print(f"{Fore.WHITE}[{Fore.RED}-{Fore.WHITE}] Your token might be invalid. Please check it again.")
    sys.exit()

userinfo = requests.get("https://discord.com/api/v9/users/@me", headers=headers).json()
username = userinfo["username"]
discriminator = userinfo["discriminator"]
userid = userinfo["id"]

async def onliner(token, status):
    try:
        async with websockets.connect("wss://gateway.discord.gg/?v=9&encoding=json") as ws:
            # Receber o hello message com heartbeat interval
            hello = json.loads(await ws.recv())
            heartbeat_interval = hello["d"]["heartbeat_interval"] / 1000

            # Autenticação
            auth = {
                "op": 2,
                "d": {
                    "token": token,
                    "properties": {
                        "$os": platform.system(),
                        "$browser": "Chrome",
                        "$device": "Desktop",
                    },
                    "presence": {
                        "status": status,
                        "afk": False,
                        "activities": [
                            {
                                "type": 4,
                                "state": custom_status,
                                "name": "Custom Status",
                                "id": "custom",
                            }
                        ]
                    },
                },
            }
            await ws.send(json.dumps(auth))

            # Receber resposta da autenticação
            response = json.loads(await ws.recv())
            if response.get("op") == 0 and response.get("t") == "READY":
                print(f"{Fore.WHITE}[{Fore.GREEN}+{Fore.WHITE}] Logged in as {username}#{discriminator} ({userid})!")

            # Task para heartbeat
            async def heartbeat():
                while True:
                    await asyncio.sleep(heartbeat_interval)
                    try:
                        await ws.send(json.dumps({"op": 1, "d": None}))
                    except:
                        break

            # Iniciar heartbeat
            heartbeat_task = asyncio.create_task(heartbeat())

            # Manter conexão aberta
            try:
                while True:
                    message = await ws.recv()
                    data = json.loads(message)
                    
                    # Responder a heartbeats solicitados
                    if data["op"] == 1:
                        await ws.send(json.dumps({"op": 1, "d": None}))
                    
                    # Reconectar se solicitado
                    if data["op"] == 7:
                        await ws.close()
                        break
                        
            except websockets.exceptions.ConnectionClosed:
                print(f"{Fore.WHITE}[{Fore.RED}-{Fore.WHITE}] Connection closed. Reconnecting...")
            finally:
                heartbeat_task.cancel()
                
    except Exception as e:
        print(f"{Fore.WHITE}[{Fore.RED}-{Fore.WHITE}] Error: {e}")
        print(f"{Fore.WHITE}[{Fore.YELLOW}*{Fore.WHITE}] Reconnecting in 5 seconds...")
        await asyncio.sleep(5)
        await onliner(token, status)  # Reconectar

async def run_onliner():
    if platform.system() == "Windows":
        os.system("cls")
    else:
        os.system("clear")
    
    print(f"{Fore.CYAN}Discord Online Status")
    print(f"{Fore.CYAN}=====================")
    
    await onliner(usertoken, status)

if __name__ == "__main__":
    keep_alive()
    try:
        asyncio.run(run_onliner())
    except KeyboardInterrupt:
        print(f"\n{Fore.WHITE}[{Fore.YELLOW}*{Fore.WHITE}] Stopping...")
    except Exception as e:
        print(f"{Fore.WHITE}[{Fore.RED}-{Fore.WHITE}] Fatal error: {e}")
