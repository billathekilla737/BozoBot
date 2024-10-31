import discord
from discord import app_commands
from tabulate import tabulate
from Assets.Methods import *
import asyncio
from openai import OpenAI


# Intents setup
#client = OpenAI(api_key=get_openai_key())
intents = discord.Intents.all()
client = discord.Client(command_prefix='/',intents=intents)
tree = app_commands.CommandTree(client) 
TOKEN = get_token()
#openai_client = OpenAI(api_key=get_openai_key())
CHANNEL_ID = get_channel_id()# locks channel
#BotTestChannelID = get_test_channel_id() # test channel

# Event to trigger once the bot is ready and sync the commands with Discord
@client.event
async def on_ready():
    #Startup Initialization
    #############################################################################
    initialize_data_file()                                                      #
    LocksChannel = client.get_channel(CHANNEL_ID)                               #
    #BotTestChannel = client.get_channel(BotTestChannelID)                      #
    Channel = LocksChannel                                                      #
    # Cache all guild members                                                   #
    for guild in client.guilds:                                                 #
        # Collect all members by iterating over the async generator             #
        async for member in guild.fetch_members(limit=None):                    #
            pass  # This will cache all the members                             #
    print("successfully finished startup") # Bisect Hosting Needs this          #
    print(f'Logged in as {client.user}!')                                       #
    #############################################################################

    # Sync the commands with Discord
    try:
        synced = await tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(e)
    
    # Sunday Midnight Reset
    while True:
        if isMondayatMidnight == True:
           await wipe_parley_picks()
        if isWednesdayEvening == True:
            await remind_missing_locks(client, Channel.guild.id, Channel)
        print("Sleeping for 10 minutes")
        await asyncio.sleep(600)
#End of on_ready
#######################################################################################################################

#Slash Commands
# New slash command to lock a parley pick for another user
@tree.command(name="lockfor", description="Save a parley pick for another user without notifying them.")
async def lock_for_parley_pick(interaction: discord.Interaction, person: discord.Member, pick: str):
    # Save the pick for the specified user
    save_parley_pick(person.id, pick)
    # Send an ephemeral response to the command invoker
    await interaction.response.send_message(
        f"{person.mention}'s parley pick has been locked as: \"{pick}\"", ephemeral=True)

# Slash command to lock a parley pick
@tree.command(name="mylock", description="Save your parley pick for the week.")
async def lock_parley_pick(interaction: discord.Interaction, pick: str):
    # Save the pick to the JSON file
    save_parley_pick(interaction.user.id, pick)
    # Respond to the user
    await interaction.response.send_message(f"Your parley pick has been locked as: \"{pick}\"")

# Slash command to show all parley picks
@tree.command(name="show_picks", description="Displays everyones saved parley picks for the week.")
async def show_parley_picks(interaction: discord.Interaction):
    # Use await to call the async function and pass the client and guild ID
    table_str = await format_parley_picks(client, interaction.guild_id)
    #table_str = await format_parley_picks(client, interaction.guild_id, openai_client)
    # Send the formatted table as a response
    await interaction.response.send_message(f"```{table_str}```")

@tree.command(name="remind_missing_locks", description="Remind users who have not submitted their parley picks.")
async def remind_missing_locks_command(interaction: discord.Interaction):
    # Fetch the channel where the command was invoked
    channel = interaction.channel
    # Call the async function to remind users who have not submitted their picks
    await remind_missing_locks(client, interaction.guild_id, channel)
    # Send a response to the command invoker
    await interaction.response.send_message("Reminder sent to users who have not submitted their parley picks.")

@tree.command(name="assign_bozo", description="Assign a user the '🤡 - The Bozo' role.")
async def assign_bozo_role(interaction: discord.Interaction, person: discord.Member):
    await assign_bozo(client, interaction.guild, person)
    await interaction.response.send_message(f"{person.mention} has been assigned the '🤡 - The Bozo' role.")

# Run the bot
client.run(TOKEN)
