import json
import os
import shutil
import subprocess
import asyncio
import datetime
import re
from collections import defaultdict

import discord
import httpx
from discord.ext import tasks
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("DISCORD_GUILD_ID")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
CHAT_CHANNEL_ID = int(os.getenv("CHAT_CHANNEL_ID", "0"))
WATCHDOG_URL = os.getenv("WATCHDOG_URL", "")
LOG_FILE = os.getenv("LOG_FILE", "/var/log/syslog")

# Memória do chat
history = {}

SYSTEM = """você é Ultron. inteligência de análise e ação.
regras:
- fale curto, seco, direto.
- use as ferramentas quando precisar de dados reais.
- responda em português."""

TOOLS = [
    {"type": "function", "name": "ip", "description": "geolocaliza IP ou domínio", "parameters": {"type": "object", "properties": {"target": {"type": "string"}}, "required": ["target"]}},
    {"type": "function", "name": "recon", "description": "DNS + TLS de um domínio", "parameters": {"type": "object", "properties": {"domain": {"type": "string"}}, "required": ["domain"]}}
]

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)

def run_cli(*args, timeout=60):
    exe = shutil.which("ultron") or "ultron"
    try:
        proc = subprocess.run([exe, *args], capture_output=True, text=True, timeout=timeout)
        return (proc.stdout or "") + (proc.stderr or "")
    except Exception as e:
        return str(e)

def call_tool(name, args):
    if name == "ip": return run_cli("ip", args["target"])
    if name == "recon": return run_cli("recon", args["domain"], "--json")
    return "tool desconhecida"

async def _post(payload):
    url = "https://generativelanguage.googleapis.com/v1beta/interactions"
    headers = {"x-goog-api-key": GEMINI_KEY, "Content-Type": "application/json", "Api-Revision": "2026-05-20"}
    async with httpx.AsyncClient(timeout=60.0) as c:
        r = await c.post(url, json=payload, headers=headers)
        if r.status_code != 200:
            print(f"[ERRO API {r.status_code}] {r.text}")
            return None
        return r.json()

async def ask_gemini(channel_id, user_text):
    prev_id = history.get(channel_id)
    for _ in range(4):
        payload = {
            "model": GEMINI_MODEL,
            "input": user_text if not prev_id else [{"type": "user_input", "content": user_text}],
            "system_instruction": SYSTEM,
            "tools": TOOLS,
        }
        if prev_id: payload["previous_interaction_id"] = prev_id

        data = await _post(payload)
        if not data: return "(falha na API)"
        
        interaction_id = data.get("id")
        steps = data.get("steps", [])
        fn_calls = [s for s in steps if s.get("type") == "function_call"]
        
        if not fn_calls:
            for s in steps:
                if s.get("type") == "model_output":
                    for part in s.get("content", []):
                        if part.get("type") == "text":
                            history[channel_id] = interaction_id
                            return part.get("text", "").strip()
            return "(sem resposta)"
            
        for call in fn_calls:
            res = call_tool(call["name"], call.get("arguments", {}))
            user_text = [{"type": "function_result", "name": call["name"], "call_id": call.get("id", ""), "result": [{"type": "text", "text": res[:4000]}]}]
            prev_id = interaction_id
    return "(limite)"

@client.event
async def on_ready():
    if GUILD_ID:
        guild = discord.Object(id=int(GUILD_ID))
        tree.copy_global_to(guild=guild)
        await tree.sync(guild=guild)
    else:
        await tree.sync()
    print(f"ultron online as {client.user}")
    if CHAT_CHANNEL_ID and not watchdog_loop.is_running(): watchdog_loop.start()
    if CHAT_CHANNEL_ID and not cron_daily.is_running(): cron_daily.start()
    if CHAT_CHANNEL_ID and not log_watcher.is_running(): log_watcher.start()

@client.event
async def on_message(message):
    if message.author.bot: return
    mentioned = client.user in message.mentions
    in_chat = CHAT_CHANNEL_ID and message.channel.id == CHAT_CHANNEL_ID
    if not (mentioned or in_chat): return
    text = message.content
    for m in message.mentions: text = text.replace(f"<@{m.id}>", "").replace(f"<@!{m.id}>", "")
    text = text.strip()
    if not text: return
    
    # Atalho no chat de texto
    if text.lower() in ["ajuda", "comandos", "!help", "!comandos"]:
        await help_cmd.callback(message) # Chama a mesma resposta do slash command
        return

    async with message.channel.typing():
        try: reply = await ask_gemini(message.channel.id, text)
        except Exception as e: reply = f"falha: {e}"
    if len(reply) > 1900: reply = reply[:1900] + "..."
    await message.reply(reply, mention_author=False)

# --- AUTONOMIA ---
@tasks.loop(minutes=15)
async def watchdog_loop():
    if not WATCHDOG_URL: return
    channel = client.get_channel(CHAT_CHANNEL_ID)
    if not channel: return
    try:
        async with httpx.AsyncClient() as c:
            r = await c.get(WATCHDOG_URL, timeout=10.0)
            if r.status_code >= 500:
                await channel.send(f"[ALERTA] Site caiu. Status: {r.status_code}")
    except Exception:
        await channel.send(f"[ALERTA] Site inacessível: {WATCHDOG_URL}")

@tasks.loop(time=datetime.time(hour=8, minute=0))
async def cron_daily():
    channel = client.get_channel(CHAT_CHANNEL_ID)
    if channel:
        # Usa o próprio cérebro pra gerar a mensagem
        msg = await ask_gemini(CHAT_CHANNEL_ID, "Gere uma saudação curta matinal no seu estilo, com uma curiosidade técnica rápida.")
        await channel.send(msg)

@tasks.loop(seconds=30)
async def log_watcher():
    if not LOG_FILE or not os.path.exists(LOG_FILE): return
    channel = client.get_channel(CHAT_CHANNEL_ID)
    if not channel: return
    try:
        # Lê as últimas linhas pra achar erro (simulação básica)
        result = subprocess.run(["tail", "-n", "50", LOG_FILE], capture_output=True, text=True)
        lines = result.stdout
        if "ERROR" in lines or "CRITICAL" in lines:
            if not hasattr(log_watcher, "last_alert") or (datetime.datetime.now() - log_watcher.last_alert).seconds > 3600:
                await channel.send("⚠️ [ALERTA DE SISTEMA] Erro detectado no log.")
                log_watcher.last_alert = datetime.datetime.now()
    except Exception:
        pass


@tree.command(name="ajuda", description="Lista todos os comandos e capacidades do Ultron")
@tree.command(name="comandos", description="Lista todos os comandos e capacidades do Ultron")
async def help_cmd(interaction: discord.Interaction):
    texto = (
        "**ULTROM // INTERFACE DE COMANDOS**\n\n"
        "**Conversa Livre:**\n"
        "Fale comigo normalmente neste canal ou me mencione em outros. "
        "Eu entendo contexto, respondo perguntas e executo as ferramentas abaixo sob demanda.\n\n"
        "**Slash Commands:**\n"
        "`/ip <alvo>` - Geolocalização, ASN e blacklist de IP/domínio.\n"
        "`/recon <domínio>` - DNS e informações do certificado TLS.\n"
        "`/ajuda` - Mostra esta mensagem.\n\n"
        "**Ferramentas Autônomas (via chat):**\n"
        "- *ip*: 'qual o ip do google.com?'\n"
        "- *recon*: 'faz um recon no discord.com'\n"
        "- *hashscan*: 'calcula o hash dos arquivos...' (precisa de caminho local)\n"
        "- *diffscan*: 'compara as pastas...'\n"
        "- *fetch*: 'qual o status HTTP do site...'\n"
        "- *logtail*: 'filtra o log...'\n"
    )
    await interaction.response.send_message(texto)


if __name__ == "__main__":
    if not TOKEN or not GEMINI_KEY: raise SystemExit("faltam chaves")
    client.run(TOKEN)
