import discord
from discord import app_commands
from tabulate import tabulate
from Assets.Methods import *
import asyncio
from datetime import datetime
import pytz
import Assets.EloSystem as EloSystem


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
# Sunday Midnight Reset
    while True:
        # Check for Monday at Midnight
        if isMondayatMidnight() and not monday_reset_done:
            await backup_and_wipe_parley_picks()
            monday_reset_done = True  # Set flag to prevent re-trigger

        # Reset Monday flag after the window has passed
        if isAfterMondayResetWindow():
            monday_reset_done = False  # Reset flag after Monday midnight window

        # Check for Wednesday at 5 PM
        if isWednesdayEvening() and not wednesday_reminder_done:
            await remind_missing_locks(client, Channel.guild.id, Channel)
            wednesday_reminder_done = True  # Set flag to prevent re-trigger

        # Reset Wednesday flag after the window has passed
        if isAfterWednesdayReminderWindow():
            wednesday_reminder_done = False  # Reset flag after Wednesday window

        print("Sleeping for 10 minutes")
        await asyncio.sleep(600)

#End of on_ready
#######################################################################################################################

#Slash Commands
# New slash command to lock a parley pick for another user
@tree.command(name="lockfor", description="Save a parley pick for another user without notifying them.")
async def lock_for_parley_pick(interaction: discord.Interaction, person: discord.Member, pick: str, odds: float):
    # Save the pick and odds for the specified user
    save_parley_pick(person.id, pick, odds)
    # Send an ephemeral response to the command invoker
    await interaction.response.send_message(
        f"{person.mention}'s parley pick has been locked as: \"{pick}\" with odds: {odds}", ephemeral=True)

# Slash command to lock a parley pick
@tree.command(name="mylock", description="Save your parley pick for the week.")
async def lock_parley_pick(interaction: discord.Interaction, pick: str, odds: float):
    # Save the pick and odds to the JSON file
    save_parley_pick(interaction.user.id, pick, odds)
    # Respond to the user
    await interaction.response.send_message(f"Your parley pick has been locked as: \"{pick}\" with odds: {odds}")

# Slash command to show all parley picks
@tree.command(name="show_picks", description="Displays everyones saved parley picks for the week.")
async def show_parley_picks(interaction: discord.Interaction):
    # Use await to call the async function and pass the client and guild ID
    table_str = await format_parley_picks(client, interaction.guild_id)
    #table_str = await format_parley_picks(client, interaction.guild_id, openai_client)
    # Send the formatted table as a response
    await interaction.response.send_message(f"```{table_str}```")

@tree.command(name="remind_missing", description="Remind users who have not submitted their parley picks.")
async def remind_missing_locks_command(interaction: discord.Interaction):
    # Fetch the channel where the command was invoked
    channel = interaction.channel
    # Call the async function to remind users who have not submitted their picks
    await remind_missing_locks(client, interaction.guild_id, channel)
    # Send a response to the command invoker
    await interaction.response.send_message("Reminder sent to users who have not submitted their parley picks.")

@tree.command(name="set_bozo", description="Assign a user the '🤡 - The Bozo' role.")
async def assign_bozo_role(interaction: discord.Interaction, person: discord.Member):
    await assign_bozo(client, interaction.guild, person)
    await interaction.response.send_message(f"{person.mention} has been assigned the '🤡 - The Bozo' role.")

#TODO: SHA-256 Hash the image and make sure that is not already in the database
@tree.command(name="submit_results", description="Upload an image with results for the bot to process.")
async def provide_results(interaction: discord.Interaction, attachment: discord.Attachment):
    await interaction.response.defer()

    if not attachment.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        await interaction.followup.send("Please upload a valid image file (PNG, JPG, JPEG).")
        return

    image_path = EloSystem.BASE_DIR / attachment.filename
    await attachment.save(image_path)

    #If the image is not in the SHA-256 database, process the image. If it is, return an error message

    if not EloSystem.is_duplicate_submission(image_path):
        print("Processing image...")
        
        try:
            extracted_results = EloSystem.extract_text_with_results(image_path)
            
            if extracted_results is None or not isinstance(extracted_results, dict) or not extracted_results:
                await interaction.followup.send("Failed to extract results from the image.")
                return
            
            updated_data = EloSystem.update_json_with_results(extracted_results)
            print(updated_data)

            # Create a summary of updated entries using cached usernames
            summary_lines = []
            for user_id, entry in updated_data.items():
                if 'result' in entry:
                    # Retrieve member from cache using the pre-cached member list
                    member = interaction.guild.get_member(int(user_id))
                    if member:
                        username = member.display_name
                    else:
                        username = f"Unknown User ({user_id})"  # Fallback to indicate user is missing

                    summary_lines.append(f"{username}: {entry['result']}")

            summary = "\n".join(summary_lines)

            await interaction.followup.send(
                f"Results have been successfully updated in the JSON file.\n\nSummary of updates:\n{summary}"
            )


        except Exception as e:
            await interaction.followup.send(f"Failed to process the image: {e}")
        finally:
            image_path.unlink(missing_ok=True)

    else:
        print("Duplicate file submission, processing halted.")
        await interaction.followup.send("Duplicate file submission, processing halted.")

# Show Power Ranking MatPlotLib
@tree.command(name="show_rankings", description="Show the current power ranking.")
async def show_power_ranking(interaction: discord.Interaction):
    guild = client.get_guild(interaction.guild_id)
    PlotPath = EloSystem.ELO_Plot_Generator(guild)
    await interaction.response.send_message(file=discord.File(PlotPath))
# Run the bot
client.run(TOKEN)
