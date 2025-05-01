import os
import sys
import discord
from discord import app_commands
from flask import Flask
from threading import Thread
import json

# --- Load and check TOKEN ---
TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    print("❌ TOKEN is missing from environment!", file=sys.stderr)
    print("Available env keys:", list(os.environ.keys()), file=sys.stderr)
    raise RuntimeError("Missing required environment variable: TOKEN")
else:
    print("✅ Loaded token:", repr(TOKEN[:8] + "..."))

# --- Flask keep-alive server ---
app = Flask(__name__)

@app.route('/')
def home():
    return "I'm alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

Thread(target=run).start()

# --- Discord bot setup ---
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# --- Storage files ---
WHITELIST_FILE = "skull_whitelist.json"
TRIGGERS_FILE = "skull_triggers.json"
BLOCKLIST_FILE = "skull_blocklist.json"

# --- Load data ---
def load_json(path):
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return {}

skull_whitelist = load_json(WHITELIST_FILE)
skull_triggers = load_json(TRIGGERS_FILE)
skull_blocklist = load_json(BLOCKLIST_FILE)

# --- Save data ---
def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f)

def save_whitelist(): save_json(WHITELIST_FILE, skull_whitelist)
def save_triggers(): save_json(TRIGGERS_FILE, skull_triggers)
def save_blocklist(): save_json(BLOCKLIST_FILE, skull_blocklist)

# --- Bot events ---
@client.event
async def on_ready():
    await tree.sync()
    print(f"💀 Logged in as {client.user} (ID: {client.user.id})")

@client.event
async def on_message(message):
    if message.author.bot:
        return

    gid = str(message.guild.id)
    uid = str(message.author.id)

    if gid not in skull_whitelist:
        return

    if uid in skull_blocklist.get(gid, []):
        return

    triggers = skull_triggers.get(gid, [])
    if any(word in message.content.lower() for word in triggers):
        await message.add_reaction("💀")

# --- Commands ---
@tree.command(name="skullsetup", description="Enable skull reactions in this server")
async def skullsetup_command(interaction: discord.Interaction):
    skull_whitelist[str(interaction.guild.id)] = True
    save_whitelist()
    await interaction.response.send_message("💀 Skull reactions are now active in this server!", ephemeral=True)

@tree.command(name="addskull", description="Add a new skull trigger word")
@app_commands.describe(trigger="The word that triggers skull reaction")
async def addskull_command(interaction: discord.Interaction, trigger: str):
    gid = str(interaction.guild.id)
    skull_triggers.setdefault(gid, []).append(trigger.lower())
    save_triggers()
    await interaction.response.send_message(f"💀 Trigger added: `{trigger}`", ephemeral=True)

@tree.command(name="skullwhitelist", description="Show all skull trigger words for this server")
async def skullwhitelist_command(interaction: discord.Interaction):
    gid = str(interaction.guild.id)
    triggers = skull_triggers.get(gid, [])
    if triggers:
        await interaction.response.send_message("Skull trigger words: " + ", ".join(triggers), ephemeral=True)
    else:
        await interaction.response.send_message("No skull trigger words set for this server.", ephemeral=True)

@tree.command(name="removeskulls", description="Clear all skull trigger words for this server")
async def removeskulls_command(interaction: discord.Interaction):
    skull_triggers[str(interaction.guild.id)] = []
    save_triggers()
    await interaction.response.send_message("All skull trigger words removed for this server.", ephemeral=True)

@tree.command(name="skullblock", description="Prevent the bot from skull-reacting to a user")
@app_commands.describe(user="The user to block from skull reactions")
async def skullblock_command(interaction: discord.Interaction, user: discord.User):
    gid = str(interaction.guild.id)
    uid = str(user.id)
    skull_blocklist.setdefault(gid, [])
    if uid not in skull_blocklist[gid]:
        skull_blocklist[gid].append(uid)
        save_blocklist()
        await interaction.response.send_message(f"{user.mention} is now blocked from skull reactions.", ephemeral=True)
    else:
        await interaction.response.send_message("User is already blocked.", ephemeral=True)

@tree.command(name="skullunblock", description="Unblock a user from skull reactions")
@app_commands.describe(user="The user to unblock")
async def skullunblock_command(interaction: discord.Interaction, user: discord.User):
    gid = str(interaction.guild.id)
    uid = str(user.id)
    if uid in skull_blocklist.get(gid, []):
        skull_blocklist[gid].remove(uid)
        save_blocklist()
        await interaction.response.send_message(f"{user.mention} has been unblocked.", ephemeral=True)
    else:
        await interaction.response.send_message("User was not blocked.", ephemeral=True)

@tree.command(name="skullblockedusers", description="List users blocked from skull reactions")
async def skullblockedusers_command(interaction: discord.Interaction):
    gid = str(interaction.guild.id)
    blocked = skull_blocklist.get(gid, [])
    if not blocked:
        await interaction.response.send_message("No users are currently blocked.", ephemeral=True)
    else:
        mentions = []
        for uid in blocked:
            user = await client.fetch_user(int(uid))
            mentions.append(user.mention)
        await interaction.response.send_message("Blocked users:\n" + "\n".join(mentions), ephemeral=True)

# --- Start bot ---
if __name__ == "__main__":
    client.run(TOKEN)
