from dotenv import load_dotenv
import json
from pathlib import Path
from tabulate import tabulate
import json
from pathlib import Path
import datetime
import pytz
import discord
import os

# Determine the base directory (the root where the script is running)
BASE_DIR = Path(__file__).parent.parent  # Adjust to two levels up to account for 'Assets/Methods.py'

# Define data paths relative to the base directory
DATA_FILE = BASE_DIR / "Assets/parley_picks.json"
ENV_FILE = BASE_DIR / "Assets/Key.env"
SEASON_FILE = BASE_DIR / "Assets/season_parley_picks.json"
ONE_WEEK = BASE_DIR / "Assets/One_Weeks_Picks.json"
TWO_WEEK = BASE_DIR / "Assets/Two_Weeks_Picks.json"


# Load environment variables from the correct path
load_dotenv(dotenv_path=ENV_FILE)

# Create the json file if it doesn't exist
def initialize_data_file():
    if not Path(DATA_FILE).is_file() or Path(DATA_FILE).stat().st_size == 0:
        with open(DATA_FILE, "w") as file:
            json.dump({}, file)

#Get the OpenAI key from the .env file
def get_openai_key():
    # Load the .env file
    # Retrieve the OpenAI key
    openai_key = os.getenv("OPENAI_API_KEY")
    return openai_key

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
        # Skip users without a populated "parley_pick" field
        if not isinstance(pick, dict) or "parley_pick" not in pick:
            continue

        # Convert user ID to Discord member nickname
        try:
            member = guild.get_member(int(user_id))
            display_name = member.display_name if member else "Unknown Member"
            print("Member found:", display_name)  # Debug
        except Exception as e:
            display_name = "Unknown Member"
            print(f"Error fetching member for {user_id}: {e}")  # Debug

        # Get odds if available
        odds = pick.get("odds", "N/A")

        # Append to table with pick extracted as needed
        table_data.append([display_name, pick["parley_pick"], odds])

    print("Table data populated:", table_data)  # Debug
    return tabulate(table_data, headers=["Names", "Parley Pick", "Odds"], tablefmt="github")

# Function to save parley picks to a JSON file
def save_parley_pick(user_id, parley_pick, odds):
    data = import_parley_picks()  # Ensure it loads correctly from the correct path

    # Get the current date in MM:DD:YYYY format
    current_date = datetime.datetime.now().strftime("%m:%d:%Y")

    # Convert odds to string and remove '+' sign if present
    odds = str(odds)  # Convert to string
    if odds.startswith('+'):
        odds = odds[1:]

    # Store the parley pick, odds, and current date associated with the user's ID
    if str(user_id) in data:
        data[str(user_id)].update({
            "parley_pick": parley_pick,
            "date": current_date,
            "odds": odds
        })
    else:
        data[str(user_id)] = {
            "parley_pick": parley_pick,
            "date": current_date,
            "odds": odds
        }

    # Save the updated data back to the JSON file
    with open(DATA_FILE, "w") as file:
        json.dump(data, file, indent=4)
        print(f"{user_id} parley pick saved with date: {current_date}, pick: {parley_pick}, odds: {odds}")

# Function to backup and wipe parley picks and transfer data around
async def backup_and_wipe_parley_picks():
    print("Backing up and wiping parley picks...")

    # Step 1: Load the current data from DATA_FILE and store it in a temporary variable
    if DATA_FILE.exists():
        with open(DATA_FILE, "r") as file:
            original_data = json.load(file)
    else:
        original_data = {}

    # Save last week into Season file
    SeasonSaver()

    # Step 2: Transfer data from One_Weeks_Picks.json to Two_Weeks_Picks.json
    if ONE_WEEK.exists():
        with open(ONE_WEEK, "r") as file:
            last_week_data = json.load(file)
        with open(TWO_WEEK, "w") as file:
            json.dump(last_week_data, file, indent=4)
        print("Transferred last week's picks to Two_Weeks_Picks.json.")
    else:
        print("One_Weeks_Picks.json is empty or missing; nothing to transfer to Two_Weeks_Picks.json.")

    # Step 3: Create a cleaned version of DATA_FILE with only user IDs and ELO values
    cleaned_data = {}
    for user_id, data in original_data.items():
        if "ELO" in data:
            cleaned_data[user_id] = {"ELO": data["ELO"]}

    # Step 4: Update cleaned_data with ELO values from ONE_WEEK if available
    if ONE_WEEK.exists():
        with open(ONE_WEEK, "r") as file:
            one_week_data = json.load(file)
        
        # Overwrite with ELO values from ONE_WEEK
        for user_id, data in one_week_data.items():
            if "ELO" in data:
                cleaned_data[user_id] = {"ELO": data["ELO"]}

    # Save the cleaned data back to DATA_FILE
    with open(DATA_FILE, "w") as file:
        json.dump(cleaned_data, file, indent=4)
    print("DATA_FILE has been updated with only user ID and ELO values.")

    # Step 5: Save the original data to ONE_WEEK
    with open(ONE_WEEK, "w") as file:
        json.dump(original_data, file, indent=4)
    print("Original contents of DATA_FILE have been saved to One_Weeks_Picks.json.")

    # Return the cleaned data for verification if needed
    return cleaned_data


# Function to save parley picks to Season Tracker File
def SeasonSaver():
    """
    Appends the weekly parley picks from ONE_WEEK to the season-long record in SEASON_FILE.
    If a user already exists in SEASON_FILE, it adds new entries to their record.
    """
    # Load current week's data from ONE_WEEK
    if ONE_WEEK.exists():
        with open(ONE_WEEK, "r") as file:
            one_week_data = json.load(file)
    else:
        print("One_Weeks_Picks.json is empty or missing; nothing to save to season.")
        return

    # Load season data, handling cases where the file is empty or has invalid JSON
    season_data = {}
    if SEASON_FILE.exists():
        try:
            with open(SEASON_FILE, "r") as file:
                if file.read().strip():  # Check if file is non-empty
                    file.seek(0)  # Reset pointer to start of file for loading
                    season_data = json.load(file)
                else:
                    print("SEASON_FILE is empty, initializing new data.")
        except json.JSONDecodeError:
            print("SEASON_FILE contains invalid JSON, initializing new data.")

    # Append each user's weekly data to their season data
    for user_id, weekly_info in one_week_data.items():
        if user_id not in season_data:
            # Initialize user data if not already in season file
            season_data[user_id] = {key: [value] for key, value in weekly_info.items()}
        else:
            # Append new weekly data for existing user
            for key, value in weekly_info.items():
                season_data[user_id].setdefault(key, []).append(value)

    # Save updated season data back to SEASON_FILE
    with open(SEASON_FILE, "w") as file:
        json.dump(season_data, file, indent=4)
    print("Season parley picks have been updated in season_parley_picks.json.")

# Function to check if it is Monday at midnight
def isMondayatMidnight() -> bool:
    # Create a timezone object for Chicago/Central
    chi_tz = pytz.timezone('America/Chicago')

    # Get the current time in Chicago/Central timezone
    correctednow = datetime.datetime.now(chi_tz)

    # Check if it is Monday and between 12am-1am
    if correctednow.weekday() == 0 and correctednow.hour == 0 and correctednow.minute < 50:
        return True
    else:
        return False

# Function to check if it is Tuesday at 8:00 AM
def isTuesdayat8AM() -> bool:
    # Create a timezone object for Chicago/Central
    chi_tz = pytz.timezone('America/Chicago')

    # Get the current time in Chicago/Central timezone
    correctednow = datetime.datetime.now(chi_tz)

    # Check if it is Tuesday and between 8:00 AM and 8:50 AM
    if correctednow.weekday() == 1 and correctednow.hour == 8 and correctednow.minute < 50:
        return True
    else:
        return False


# Function to check if it is Wednesday at 5:00 PM
def isWednesdayEvening() -> bool:
    # Create a timezone object for Chicago/Central
    chi_tz = pytz.timezone('America/Chicago')

    # Get the current time in Chicago/Central timezone
    correctednow = datetime.datetime.now(chi_tz)

    # Check if it is Wednesday and exactly 5:00 PM
    if correctednow.weekday() == 2 and correctednow.hour == 17 and correctednow.minute <= 15:
        return True
    else:
        return False

# Function to remind users who have not submitted their parley picks
async def remind_missing_locks(client, guild_id, channel):
    print("Checking for missing locks...")
    # Import parley picks and determine submitted user IDs
    parley_picks = import_parley_picks()
    submitted_user_ids = {user_id for user_id, pick in parley_picks.items() if isinstance(pick, dict) and "parley_pick" in pick}

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


# Helper function to assign the "Bozo" role, ensuring only one member has it at a time
async def assign_bozo(client, guild, new_bozo):
    print("Assigning Bozo role...")
    # Get roles by name
    bozo_role = discord.utils.get(guild.roles, name="🤡 - The Bozo")
    brains_role = discord.utils.get(guild.roles, name="🧠 - The Brains")
    
    # Remove the Bozo role from any current holder
    for member in guild.members:
        if bozo_role in member.roles:
            await member.remove_roles(bozo_role)
            if brains_role:
                await member.add_roles(brains_role)
            break  # Stop after finding the first bozo (there should only be one)
    
    # Assign Bozo role to the new user and remove the Brains role if they have it
    await new_bozo.add_roles(bozo_role)
    if brains_role in new_bozo.roles:
        print("Removing Brains role from Bozo...")
        await new_bozo.remove_roles(brains_role)

# Function to check if it’s after the Monday reset window (past 1 AM on Monday)
def isAfterMondayResetWindow() -> bool:
    chi_tz = pytz.timezone('America/Chicago')  # Define timezone in the function scope
    correctednow = datetime.datetime.now(chi_tz)
    return correctednow.weekday() != 0 or correctednow.hour > 1

# Function to check if it’s after the Tuesday reminder window (past 10 AM on Tuesday)
def isAfterTuesdayResetWindow() -> bool:
    chi_tz = pytz.timezone('America/Chicago')  # Define timezone in the function scope
    correctednow = datetime.datetime.now(chi_tz)
    return correctednow.weekday() != 1 or correctednow.hour > 10

# Function to check if it’s after the Wednesday reminder window (past 6 PM on Wednesday)
def isAfterWednesdayReminderWindow() -> bool:
    chi_tz = pytz.timezone('America/Chicago') 
    correctednow = datetime.datetime.now(chi_tz)
    return correctednow.weekday() != 2 or correctednow.hour > 18

# Function to check if it’s between Tuesday at 8:05 AM to Saturday at 10:30 am
def isBetweenTuesdayAndSaturday() -> bool:
    chi_tz = pytz.timezone('America/Chicago')
    correctednow = datetime.datetime.now(chi_tz)

    # Define start and end times for the desired range
    today = correctednow.date()
    start_time = chi_tz.localize(datetime.datetime.combine(today, datetime.time(8, 5)))
    end_time = chi_tz.localize(datetime.datetime.combine(today, datetime.time(10, 30)))

    # Move the start_time to the most recent Tuesday if it's not already a Tuesday or later
    while start_time.weekday() != 1:  # Weekday 1 corresponds to Tuesday
        start_time -= datetime.timedelta(days=1)

    # Move the end_time to the next Saturday if it's not already a Saturday
    while end_time.weekday() != 5:  # Weekday 5 corresponds to Saturday
        end_time += datetime.timedelta(days=1)

    return start_time <= correctednow <= end_time


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