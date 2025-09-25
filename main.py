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
custom_status = "A geometria é única e eterna; ela é um reflexo do pensamento de Deus"

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

class DiscordOnline:
    def __init__(self, token, status):
        self.token = token
        self.status = status
        self.running = True

    async def connect(self):
        while self.running:
            try:
                async with websockets.connect("wss://gateway.discord.gg/?v=9&encoding=json") as ws:
                    print(f"{Fore.WHITE}[{Fore.GREEN}+{Fore.WHITE}] Connecting to Discord Gateway...")
                    
                    # Receber hello message
                    hello = json.loads(await ws.recv())
                    heartbeat_interval = hello["d"]["heartbeat_interval"] / 1000

                    # Payload de autenticação
                    auth_payload = {
                        "op": 2,
                        "d": {
                            "token": self.token,
                            "properties": {
                                "$os": platform.system(),
                                "$browser": "Chrome",
                                "$device": "Desktop",
                            },
                            "presence": {
                                "status": self.status,
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
                    
                    await ws.send(json.dumps(auth_payload))
                    
                    # Aguardar resposta READY
                    ready_received = False
                    while not ready_received:
                        message = await ws.recv()
                        data = json.loads(message)
                        
                        if data.get("op") == 0 and data.get("t") == "READY":
                            print(f"{Fore.WHITE}[{Fore.GREEN}+{Fore.WHITE}] Logged in as {username}#{discriminator} ({userid})!")
                            ready_received = True
                            break
                    
                    # Loop principal para manter conexão
                    last_heartbeat = asyncio.get_event_loop().time()
                    heartbeat_ack = True
                    
                    while self.running:
                        try:
                            # Verificar se precisa enviar heartbeat
                            current_time = asyncio.get_event_loop().time()
                            if current_time - last_heartbeat >= heartbeat_interval:
                                if heartbeat_ack:
                                    await ws.send(json.dumps({"op": 1, "d": None}))
                                    last_heartbeat = current_time
                                    heartbeat_ack = False
                                else:
                                    # Heartbeat não foi respondido, reconectar
                                    break
                            
                            # Ler mensagens com timeout
                            try:
                                message = await asyncio.wait_for(ws.recv(), timeout=1.0)
                                data = json.loads(message)
                                
                                # Processar opcode 11 (heartbeat ack)
                                if data["op"] == 11:
                                    heartbeat_ack = True
                                
                                # Processar opcode 7 (reconnect)
                                elif data["op"] == 7:
                                    print(f"{Fore.WHITE}[{Fore.YELLOW}*{Fore.WHITE}] Reconnect requested by Discord")
                                    break
                                
                                # Processar opcode 9 (invalid session)
                                elif data["op"] == 9:
                                    print(f"{Fore.WHITE}[{Fore.YELLOW}*{Fore.WHITE}] Invalid session, reconnecting...")
                                    break
                                    
                            except asyncio.TimeoutError:
                                continue
                                
                        except websockets.exceptions.ConnectionClosed:
                            print(f"{Fore.WHITE}[{Fore.RED}-{Fore.WHITE}] Connection closed")
                            break
                            
            except Exception as e:
                print(f"{Fore.WHITE}[{Fore.RED}-{Fore.WHITE}] Connection error: {e}")
                print(f"{Fore.WHITE}[{Fore.YELLOW}*{Fore.WHITE}] Reconnecting in 10 seconds...")
                await asyncio.sleep(10)
                
    def stop(self):
        self.running = False

async def run_onliner():
    if platform.system() == "Windows":
        os.system("cls")
    else:
        os.system("clear")
    
    print(f"{Fore.CYAN}Discord Online Status")
    print(f"{Fore.CYAN}=====================")
    
    online = DiscordOnline(usertoken, status)
    await online.connect()

def main():
    keep_alive()
    try:
        asyncio.run(run_onliner())
    except KeyboardInterrupt:
        print(f"\n{Fore.WHITE}[{Fore.YELLOW}*{Fore.WHITE}] Stopping...")
    except Exception as e:
        print(f"{Fore.WHITE}[{Fore.RED}-{Fore.WHITE}] Fatal error: {e}")

if __name__ == "__main__":
    main()
