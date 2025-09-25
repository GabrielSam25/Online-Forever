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

# Debug: Verificar se as variáveis de ambiente estão carregando
print(f"{Fore.WHITE}[{Fore.YELLOW}*{Fore.WHITE}] Carregando token...")
usertoken = os.getenv("TOKEN")

# Debug: Mostrar informações sobre o token (sem mostrar o token completo por segurança)
if usertoken:
    token_preview = usertoken[:10] + "..." if len(usertoken) > 10 else usertoken
    print(f"{Fore.WHITE}[{Fore.YELLOW}*{Fore.WHITE}] Token encontrado: {token_preview}")
    print(f"{Fore.WHITE}[{Fore.YELLOW}*{Fore.WHITE}] Comprimento do token: {len(usertoken)} caracteres")
else:
    print(f"{Fore.WHITE}[{Fore.RED}-{Fore.WHITE}] Token NÃO encontrado nas variáveis de ambiente")
    print(f"{Fore.WHITE}[{Fore.YELLOW}*{Fore.WHITE}] Variáveis de ambiente disponíveis: {list(os.environ.keys())}")

if not usertoken:
    print(f"{Fore.WHITE}[{Fore.RED}-{Fore.WHITE}] Please add a token inside Secrets.")
    sys.exit()

# Verificar formato do token
if not usertoken.startswith(('mfa.', 'ND', 'OT', 'MT')):
    print(f"{Fore.WHITE}[{Fore.RED}-{Fore.WHITE}] Formato do token parece inválido")
    print(f"{Fore.WHITE}[{Fore.YELLOW}*{Fore.WHITE}] Tokens geralmente começam com mfa., ND, OT ou MT")

headers = {
    "Authorization": usertoken, 
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

print(f"{Fore.WHITE}[{Fore.YELLOW}*{Fore.WHITE}] Validando token...")

try:
    validate = requests.get("https://discord.com/api/v9/users/@me", headers=headers, timeout=10)
    print(f"{Fore.WHITE}[{Fore.YELLOW}*{Fore.WHITE}] Status code da validação: {validate.status_code}")
    
    if validate.status_code != 200:
        print(f"{Fore.WHITE}[{Fore.RED}-{Fore.WHITE}] Token inválido. Status: {validate.status_code}")
        if validate.status_code == 401:
            print(f"{Fore.WHITE}[{Fore.RED}-{Fore.WHITE}] Erro 401: Não autorizado - Token inválido ou expirado")
        elif validate.status_code == 403:
            print(f"{Fore.WHITE}[{Fore.RED}-{Fore.WHITE}] Erro 403: Proibido - Token pode estar banido")
        elif validate.status_code == 429:
            print(f"{Fore.WHITE}[{Fore.RED}-{Fore.WHITE}] Erro 429: Rate limit - Muitas requisições")
        
        # Tentar obter mais informações do erro
        try:
            error_response = validate.json()
            print(f"{Fore.WHITE}[{Fore.RED}-{Fore.WHITE}] Resposta do Discord: {error_response}")
        except:
            print(f"{Fore.WHITE}[{Fore.RED}-{Fore.WHITE}] Resposta bruta: {validate.text[:100]}...")
        
        sys.exit()
    
    # Se chegou aqui, token é válido
    userinfo = validate.json()
    username = userinfo["username"]
    discriminator = userinfo.get("discriminator", "0")
    userid = userinfo["id"]
    
    print(f"{Fore.WHITE}[{Fore.GREEN}+{Fore.WHITE}] Token válido! Logado como: {username}#{discriminator} ({userid})")

except requests.exceptions.Timeout:
    print(f"{Fore.WHITE}[{Fore.RED}-{Fore.WHITE}] Timeout na validação do token")
    sys.exit()
except requests.exceptions.ConnectionError:
    print(f"{Fore.WHITE}[{Fore.RED}-{Fore.WHITE}] Erro de conexão na validação do token")
    sys.exit()
except Exception as e:
    print(f"{Fore.WHITE}[{Fore.RED}-{Fore.WHITE}] Erro inesperado na validação: {e}")
    sys.exit()

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
    print(f"{Fore.WHITE}[{Fore.YELLOW}*{Fore.WHITE}] Conectando ao Gateway do Discord...")
    
    try:
        async with websockets.connect(
            "wss://gateway.discord.gg/?v=9&encoding=json",
            timeout=30,
            max_size=2**20  # 1MB limit
        ) as ws:
            print(f"{Fore.WHITE}[{Fore.GREEN}+{Fore.WHITE}] Conectado ao Gateway!")
            
            start = json.loads(await ws.recv())
            heartbeat = start["d"]["heartbeat_interval"]
            print(f"{Fore.WHITE}[{Fore.YELLOW}*{Fore.WHITE}] Heartbeat interval: {heartbeat}ms")
            
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
                        }]
                    },
                },
            }
            
            await ws.send(json.dumps(auth))
            print(f"{Fore.WHITE}[{Fore.GREEN}+{Fore.WHITE}] Payload de autenticação enviado")
            
            # Simplified heartbeat payload
            online = {"op": 1, "d": None}
            
            heartbeat_count = 0
            while True:
                try:
                    # Receive any incoming messages to keep connection alive
                    message = await asyncio.wait_for(ws.recv(), timeout=heartbeat / 1000)
                    data = json.loads(message)
                    
                    if data.get('op') == 10:  # Hello message
                        heartbeat = data['d']['heartbeat_interval']
                    elif data.get('t') == 'READY':
                        print(f"{Fore.WHITE}[{Fore.GREEN}+{Fore.WHITE}] Bot está online e funcionando!")
                    
                except asyncio.TimeoutError:
                    # Send heartbeat
                    await ws.send(json.dumps(online))
                    heartbeat_count += 1
                    if heartbeat_count % 10 == 0:  # Log a cada 10 heartbeats
                        print(f"{Fore.WHITE}[{Fore.BLUE}*{Fore.WHITE}] Heartbeat #{heartbeat_count} enviado")
                
                except websockets.exceptions.ConnectionClosed as e:
                    print(f"{Fore.WHITE}[{Fore.RED}-{Fore.WHITE}] Conexão fechada: {e}")
                    break
                
                await asyncio.sleep(heartbeat / 1000)
                
    except Exception as e:
        print(f"{Fore.WHITE}[{Fore.RED}-{Fore.WHITE}] Erro na conexão WebSocket: {e}")
        raise

async def run_onliner():
    if platform.system() == "Windows":
        os.system("cls")
    else:
        os.system("clear")
    
    print(f"{Fore.WHITE}[{Fore.GREEN}+{Fore.WHITE}] Bot iniciado!")
    print(f"{Fore.WHITE}[{Fore.GREEN}+{Fore.WHITE}] Logado como {Fore.CYAN}{username}{Fore.WHITE} ({userid})!")
    print(f"{Fore.WHITE}[{Fore.YELLOW}*{Fore.WHITE}] Status: {status}")
    print(f"{Fore.WHITE}[{Fore.YELLOW}*{Fore.WHITE}] Custom Status: {custom_status}")
    print(f"{Fore.WHITE}[{Fore.YELLOW}*{Fore.WHITE}] Pressione Ctrl+C para parar o bot\n")
    
    while True:
        if limiter.should_allow():
            try:
                await onliner(usertoken, status)
            except Exception as e:
                print(f"{Fore.WHITE}[{Fore.RED}-{Fore.WHITE}] Erro: {e}")
                wait_time = 30
                print(f"{Fore.WHITE}[{Fore.YELLOW}*{Fore.WHITE}] Reconectando em {wait_time} segundos...")
                await asyncio.sleep(wait_time)
        else:
            print(f"{Fore.WHITE}[{Fore.RED}-{Fore.WHITE}] Rate limit excedido. Aguardando 60 segundos...")
            await asyncio.sleep(60)

# Keep the server alive
keep_alive()
print(f"{Fore.WHITE}[{Fore.GREEN}+{Fore.WHITE}] Servidor keep-alive iniciado!")

# Run with error handling
try:
    asyncio.run(run_onliner())
except KeyboardInterrupt:
    print(f"\n{Fore.WHITE}[{Fore.YELLOW}*{Fore.WHITE}] Bot parado pelo usuário")
except Exception as e:
    print(f"{Fore.WHITE}[{Fore.RED}-{Fore.WHITE}] Erro fatal: {e}")
