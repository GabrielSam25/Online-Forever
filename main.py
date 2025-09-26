import discord
import os
from discord.ext import commands

# Configurando os intents
intents = discord.Intents.default()
intents.message_content = True  # necessário para ler mensagens no Discord

client = commands.Bot(command_prefix=':', self_bot=True, help_command=None, intents=intents)

@client.event
async def on_ready():
    await client.change_presence(status=discord.Status.online)
    os.system('clear')
    print(f'Logged in as {client.user} (ID: {client.user.id})')

client.run(os.getenv("TOKEN"), bot=False)
