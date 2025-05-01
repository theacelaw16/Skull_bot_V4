import os
import discord
from discord import app_commands
from flask import Flask
from threading import Thread
import json

# --- Get token directly from Railway shared variable ---
TOKEN = os.environ["TOKEN"]
print("Loaded token:", repr(TOKEN))  # Debug print

# --- Flask server setup (keep-alive for Replit etc.) ---
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

# --- Persistent storage files ---
WHITELIST_FILE = "skull_whitelist.json"
TRIGGERS_FILE = "skull_triggers.json"
BLOCKLIST_FILE = "skull_blocklist.json"

# --- Load whitelist ---
if os.path.exists(WHITELIST_FILE):
    with open(WHITELIST_FILE, 'r') as f:
        skull_whitelist = json.load(f)
else:
    skull_whitelist = {}

# --- Load triggers ---
if os.path.exists(TRIGGERS_FILE):
    with open(TRIGGERS_FILE, 'r') as f:
        skull_triggers = json.load(f)
else:
    skull_triggers = {}

# --- Load blocklist ---
if os.path.exists(BLOCKLIST_FILE):
    with open(BLOCKLIST_FILE, 'r') as f:
        skull_blocklist = json.load(f)
else:
    skull_blocklist = {}

# --- Save whitelist ---
def save_whitelist():
    with open(WHITELIST_FILE, 'w') as f:
        json.dump(skull_whitelist, f)

# --- Save triggers ---
def save_triggers():
    with open(TRIGGERS_FILE, 'w') as f:
        json.dump(skull_triggers, f)

# --- Save blocklist ---
def save_blocklist():
    with open(BLOCKLIST_FILE, 'w') as f:
        json.dump(skull_blocklist, f)

# --- Discord Events ---
@client.event
async def on_ready():
    await tree.sync()
    print(f'Logged in as {client.user} (ID: {client.user.id})')
    print('------')

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
        await message.add_reaction("\U0001F480")

# --- Slash Commands ---
@tree.command(name="skullsetup", description="Enable skull reactions in this server")
async def skullsetup_command(interaction: discord.Interaction):
    gid = str(interaction.guild.id)
    skull_whitelist[gid] = True
    save_whitelist()
    await interaction.response.send_message("💀 Skull reactions are now active in this server!", ephemeral=True)

@tree.command(name="addskull", description="Add a new skull trigger word")
@app_commands.describe(trigger="The word that triggers skull reaction")
async def addskull_command(interaction: discord.Interaction, trigger: str):
    gid = str(interaction.guild.id)
    if gid not in skull_triggers:
        skull_triggers[gid] = []
    skull_triggers[gid].append(trigger.lower())
    save_triggers()
    await interaction.response.send_message(f"💀 Trigger added: `{trigger}`", ephemeral=True)

@tree.command(name="skullwhitelist", description="Show all skull trigger words for this server")
async def skullwhitelist_command(interaction: discord.Interaction):
    gid = str(interaction.guild.id)
    triggers = skull_triggers.get(gid, [])
    if not triggers:
        await interaction.response.send_message("No skull trigger words set for this server.", ephemeral=True)
    else:
        await interaction.response.send_message("Skull trigger words: " + ", ".join(triggers), ephemeral=True)

@tree.command(name="removeskulls", description="Clear all skull trigger words for this server")
async def removeskulls_command(interaction: discord.Interaction):
    gid = str(interaction.guild.id)
    if gid in skull_triggers:
        skull_triggers[gid] = []
        save_triggers()
    await interaction.response.send_message("All skull trigger words removed for this server.", ephemeral=True)

@tree.command(name="skullblock", description="Prevent the bot from skull-reacting to a user in this server")
@app_commands.describe(user="The user to ignore for skull reactions")
async def skullblock_command(interaction: discord.Interaction, user: discord.User):
    gid = str(interaction.guild.id)
    uid = str(user.id)
    if gid not in skull_blocklist:
        skull_blocklist[gid] = []
    if uid not in skull_blocklist[gid]:
        skull_blocklist[gid].append(uid)
        save_blocklist()
        await interaction.response.send_message(f"User {user.mention} will now be ignored for skull reactions.", ephemeral=True)
    else:
        await interaction.response.send_message("User is already blocked.", ephemeral=True)

@tree.command(name="skullunblock", description="Remove a user from the skull blocklist")
@app_commands.describe(user="The user to unblock from skull reactions")
async def skullunblock_command(interaction: discord.Interaction, user: discord.User):
    gid = str(interaction.guild.id)
    uid = str(user.id)
    if gid in skull_blocklist and uid in skull_blocklist[gid]:
        skull_blocklist[gid].remove(uid)
        save_blocklist()
        await interaction.response.send_message(f"User {user.mention} has been unblocked.", ephemeral=True)
    else:
        await interaction.response.send_message("User is not currently blocked.", ephemeral=True)

@tree.command(name="skullblockedusers", description="List users blocked from skull reactions")
async def skullblockedusers_command(interaction: discord.Interaction):
    gid = str(interaction.guild.id)
    blocked_ids = skull_blocklist.get(gid, [])
    if not blocked_ids:
        await interaction.response.send_message("No users are currently blocked from skull reactions in this server.", ephemeral=True)
    else:
        mentions = []
        for uid in blocked_ids:
            user = await client.fetch_user(int(uid))
            mentions.append(user.mention)
        await interaction.response.send_message("Blocked users:\n" + "\n".join(mentions), ephemeral=True)

# --- Run the bot ---
if __name__ == "__main__":
    client.run(TOKEN)
