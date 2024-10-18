import discord
from discord import app_commands
from tabulate import tabulate
from Assets.Methods import *
from Assets.SundayMidnightReset import *
import asyncio


# Intents setup
intents = discord.Intents.all()
client = discord.Client(command_prefix='/',intents=intents)
tree = app_commands.CommandTree(client) 
CHANNEL_ID = get_channel_id()
BotTestChannel = client.get_channel(CHANNEL_ID)
TOKEN = get_token()


# Event to trigger once the bot is ready and sync the commands with Discord
@client.event
async def on_ready():
    try:
        synced = await tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(e)
    print(f'Logged in as {client.user}!')
        
    # Sunday Midnight Reset
    while True:
        if isSundayatMidnight == True:
            #Reset the Parley Picks
            pass
        else:
            #Do nothing
            pass
        await asyncio.sleep(500)

# Slash command to lock a parley pick
@tree.command(name="lock", description="Save your parley pick.")
async def lock_parley_pick(interaction: discord.Interaction, pick: str):
    # Save the pick to the JSON file
    save_parley_pick(interaction.user.id, pick)
    # Respond to the user
    await interaction.response.send_message(f"Your parley pick has been locked as: \"{pick}\"")

# Slash command to show all parley picks
@tree.command(name="show_picks", description="Displays all saved parley picks.")
async def show_parley_picks(interaction: discord.Interaction):
    # Use await to call the async function and pass the client and guild ID
    table_str = await format_parley_picks(client, interaction.guild_id)
    
    # Send the formatted table as a response
    await interaction.response.send_message(f"```{table_str}```")



# Run the bot
client.run(TOKEN)
