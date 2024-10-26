from dotenv import load_dotenv
import os
import json
from pathlib import Path
from tabulate import tabulate
import requests
from bs4 import BeautifulSoup
import json
from pathlib import Path
import datetime
import pytz

# Determine the base directory (the root where the script is running)
BASE_DIR = Path(__file__).parent.parent  # Adjust to two levels up to account for 'Assets/Methods.py'

# Define data paths relative to the base directory
DATA_FILE = BASE_DIR / "Assets/parley_picks.json"
ENV_FILE = BASE_DIR / "Assets/Key.env"
SEASON_DATA_FILE = BASE_DIR / "Assets/season_parley_picks.json"


# Load environment variables from the correct path
load_dotenv(dotenv_path=ENV_FILE)

# Create the json file if it doesn't exist
def initialize_data_file():
    if not Path(DATA_FILE).is_file() or Path(DATA_FILE).stat().st_size == 0:
        with open(DATA_FILE, "w") as file:
            json.dump({}, file)

#Get the Discord token
def get_token():
    # Load the .env file
    # Retrieve the token
    token = os.getenv("TOKEN")
    return token

#Get the channel ID from the .env file
def get_channel_id():
    # Set a default channel ID or raise an error if not set
    channel_id = os.getenv("CHANNEL_ID")
    if channel_id is None:
        raise ValueError("CHANNEL_ID environment variable not set")
    return int(channel_id)

#Get the TESTchannel ID from the .env file
def get_test_channel_id():
    # Load the .env file
    # Retrieve the channel ID
    channel_id = int(os.getenv("TEST_CHANNEL_ID"))
    return channel_id

#Get the OpenAI key from the .env file
def get_openai_key():
    # Load the .env file
    # Retrieve the OpenAI key
    openai_key = os.getenv("OPENAI_API_KEY")
    return openai_key

# Function to import parley picks from a JSON file
def import_parley_picks():
    # Check if the file exists; if not, create an empty JSON object
    if not Path(DATA_FILE).is_file():
        return {}

    # Check if the file is empty, and return an empty dictionary if it is
    if Path(DATA_FILE).stat().st_size == 0:
        return {}

    # Attempt to load the JSON data
    with open(DATA_FILE, "r") as file:
        try:
            return json.load(file)
        except json.JSONDecodeError:
            # If the JSON is invalid, return an empty dictionary and log a warning
            print("Warning: Invalid JSON detected. Returning an empty dictionary.")
            return {}

# Make output table message
async def format_parley_picks(client, guild_id):
    data = import_parley_picks()
    table_data = []

    # Fetch the guild object
    guild = client.get_guild(guild_id)

    for user_id, pick in data.items():
        # Convert user ID to Discord member nickname
        try:
            member = guild.get_member(int(user_id))
            if member:
                # Use the member's nickname or username
                display_name = member.display_name
            else:
                display_name = "Unknown Member"
        except Exception:
            display_name = "Unknown Member"  # Fallback in case member can't be fetched

        #Feed the pick data into openAI so that it can return the team name and the game start time
        # openai_client = openai.ChatCompletion.create(
        #     model="gpt-4o-mini",
        #     messages=[
        #         {"role": "system", "content": "You will be give a list of parley picks I will need to know the team name if it isn't given and the game start time of each pick."},
        #         {"role": "user", "content": pick},
        #     ],
        # )


        table_data.append([display_name, pick])

    # Create headers and use tabulate to format the data
    return tabulate(table_data, headers=["Names", "Parley Pick"], tablefmt="github")

# Function to save parley picks to a JSON file
def save_parley_pick(user_id, parley_pick):
    data = import_parley_picks()  # Ensure it loads correctly from the correct path

    # Store the parley pick associated with the user's ID
    data[str(user_id)] = parley_pick

    # Save the updated data back to the JSON file
    with open(DATA_FILE, "w") as file:
        json.dump(data, file, indent=4)
        print(f"{user_id} saved Parley pick saved as: {parley_pick}")

#Save the picks to JSON and Wipe the week picks
async def wipe_parley_picks():
    # Wipe all parley picks from the JSON file
    with open(DATA_FILE, "w") as file:
        SeasonPickSaver()
        json.dump({}, file)
        print("Parley picks have been wiped.")

    with open(DATA_FILE, "r") as file:
        return json.load(file)

#Save the picks to season long JSON
def SeasonPickSaver():
    #TODO: If for somereason this gets called twice in a week it will make duplicate entries
    # Load the weekly picks from parley_picks.json
    if not DATA_FILE.is_file():
        print("No weekly picks file found.")
        return

    with open(DATA_FILE, "r") as file:
        try:
            weekly_picks = json.load(file)
        except json.JSONDecodeError:
            print("Warning: Invalid JSON detected in weekly picks file.")
            return

    # Ensure the season data file exists
    if not SEASON_DATA_FILE.is_file():
        with open(SEASON_DATA_FILE, "w") as file:
            json.dump({}, file)
    
    # Load existing season data
    with open(SEASON_DATA_FILE, "r") as file:
        try:
            season_data = json.load(file)
        except json.JSONDecodeError:
            print("Warning: Invalid JSON detected in season picks file. Starting fresh.")
            season_data = {}

    # Update season data with this week's picks
    for user_id, pick in weekly_picks.items():
        if str(user_id) in season_data:
            season_data[str(user_id)].append(pick)
        else:
            season_data[str(user_id)] = [pick]

    # Save the updated season data back to the JSON file
    with open(SEASON_DATA_FILE, "w") as file:
        json.dump(season_data, file, indent=4)
        print("Season picks have been updated.")

# Function to check if it is Monday at midnight
def isMondayatMidnight():
    # Create a timezone object for Chicago/Central
    chi_tz = pytz.timezone('America/Chicago')

    # Get the current time in Chicago/Central timezone
    correctednow = datetime.datetime.now(chi_tz)

    # Check if it is Monday and between 12am-1am
    if correctednow.weekday() == 0 and correctednow.hour == 0 and correctednow.minute < 50:
        return True
    else:
        return False

# Function to check if it is Wednesday at 5:00 PM
def isWednesdayEvening():
    # Create a timezone object for Chicago/Central
    chi_tz = pytz.timezone('America/Chicago')

    # Get the current time in Chicago/Central timezone
    correctednow = datetime.datetime.now(chi_tz)

    # Check if it is Wednesday and exactly 5:00 PM
    if correctednow.weekday() == 2 and correctednow.hour == 17 and correctednow.minute == 0:
        return True
    else:
        return False

# Function to remind users who have not submitted their parley picks
async def remind_missing_locks(client, guild_id, channel):
    print("Checking for missing locks...")
    # Import parley picks and determine submitted user IDs
    parley_picks = import_parley_picks()
    submitted_user_ids = set(parley_picks.keys())

    # Fetch the guild object using the guild ID
    guild = client.get_guild(guild_id)
    if not guild:
        print(f"Guild with ID {guild_id} not found.")
        return

    # Ensure all members are fetched and cached
    all_user_ids = set()
    try:
        async for member in guild.fetch_members(limit=None):
            # Ignore members who have the "Bots" role
            if any(role.name == "Bots" for role in member.roles):
                continue
            all_user_ids.add(str(member.id))
    except Exception as e:
        print(f"Error fetching members for guild {guild_id}: {e}")
        return

    # Determine which users are missing their parley picks
    missing_user_ids = all_user_ids - submitted_user_ids

    # Send a reminder message to users who have not submitted their picks
    if missing_user_ids:
        mentions = " ".join([f"<@{user_id}>" for user_id in missing_user_ids])
        reminder_message = f"Hey {mentions}\n Please turn in your bet ASAP using **/mylock**"
        # Send the reminder message to the specified channel
        if channel:
            try:
                await channel.send(reminder_message)
                print("Reminder sent successfully.")
            except Exception as e:
                print(f"Error sending reminder: {e}")
        else:
            print(f"Channel issue: {channel}")
    else:
        print("All users have submitted their locks.")


#Testing OpenAI
##########################################################
# from openai import OpenAI

# client = OpenAI()
# #Read the json file and just grab the picks and save to a list
# parley_picks = import_parley_picks()

# combined_picks = "\n".join([f"- {pick}" for pick in parley_picks.values()])
# print(combined_picks)

# response = openai_client = client.chat.completions.create(model="gpt-4o-mini",
# messages=[
#     {"role": "system", "content": """
#      You will be give a list of parley picks I will need to know the team name if it isn't given and the game start time of each pick. 
#      You will get these game start times from the ESPN website.
#      Use the following format: Team Name, Pick Made - Game Start Date and Time. For example: Lakers, Moneyline - Monday @ 7:00 PM CST.
#      """},
#     {"role": "user", "content": combined_picks},
#     #print the response
    
# ])
# #print the response
# print(response.choices[0].message.content)
