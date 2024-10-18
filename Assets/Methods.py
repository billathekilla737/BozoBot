from dotenv import load_dotenv
import os
import json
from pathlib import Path
from tabulate import tabulate

load_dotenv("Assets/Key.env")
DATA_FILE = "Assets/Parley_Picks.json"

def get_token():
    # Load the .env file
    # Retrieve the token
    token = os.getenv("TOKEN")
    return token

def get_channel_id():
    # Load the .env file
    # Retrieve the channel ID
    channel_id = int(os.getenv("CHANNEL_ID"))
    return channel_id

def import_parley_picks():
    # Load the json file with the parley picks of the week
    with open("Assets/ParleyPicks.json", "r") as file:
        parley_picks = json.load(file)


# Make output table message
async def format_parley_picks(client, guild_id):
    data = load_parley_picks()
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
        
        table_data.append([display_name, pick])
    
    # Create headers and use tabulate to format the data
    return tabulate(table_data, headers=["Names", "Parley Pick"], tablefmt="github")



# Function to save parley picks to a JSON file
def save_parley_pick(user_id, parley_pick):
    data = load_parley_picks()
    
    # Store the parley pick associated with the user's ID
    data[str(user_id)] = parley_pick
    
    # Save the updated data back to the JSON file
    with open(DATA_FILE, "w") as file:
        json.dump(data, file, indent=4)
        print(f"{user_id} saved Parley pick saved as: {parley_pick}")

# Function to load existing parley picks from the JSON file
def load_parley_picks():
    # Check if the file exists; if not, create an empty JSON object
    if not Path(DATA_FILE).is_file():
        return {}
    
    with open(DATA_FILE, "r") as file:
        return json.load(file)
