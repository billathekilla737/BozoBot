BozoBot - Discord Parley Picks Bot
Description
BozoBot is a Discord bot designed to manage and display parley picks from server members. It allows users to lock in their parley picks using a simple slash command, and retrieves them later in a nicely formatted table. The bot saves these picks externally to a JSON file to ensure persistence and easy access even if the bot restarts.

Features
Slash Commands:
/lock "Place your pick here" - Allows users to save their parley picks. The response is visible to everyone in the channel.
/show_picks - Displays a nicely formatted table of all saved picks, showing server nicknames for users.
Data Persistence:
Picks are saved to a JSON file (parley_picks.json) for persistence.
If the bot restarts or crashes, the saved data will remain intact.
User-Friendly Output:
Uses tabulate to present picks in a readable table format.
Fetches and displays users' server nicknames for more personalized output.
Requirements
Python 3.8+
The following Python packages:
discord.py
python-dotenv
tabulate
schedule (if any scheduled tasks are used)
Installing Dependencies
bash
Copy code
pip install discord.py python-dotenv tabulate
Getting Started
Clone the Repository and Navigate to Project Directory:

bash
Copy code
git clone <your-repository-url>
cd BozoBot
Create a Virtual Environment (Recommended):

bash
Copy code
python -m venv BozoVenv
BozoVenv\Scripts\activate  # Windows
source BozoVenv/bin/activate  # macOS/Linux
Set Up Your .env File:

In the Assets directory, create a file named Key.env with the following content:
makefile
Copy code
TOKEN=your_discord_bot_token_here
CHANNEL_ID=your_channel_id_here
Replace your_discord_bot_token_here and your_channel_id_here with the actual token and ID.
Invite the Bot to Your Server:

Make sure the bot has applications.commands and administrator permissions.
Enable SERVER MEMBERS INTENT in the Discord Developer Portal.
Run the Bot:

bash
Copy code
python Main.py
Commands
1. /lock "Place your pick here"
Description: Allows users to save their parley pick. The response will be visible to everyone in the channel.
Example:
bash
Copy code
/lock "Team A wins with 10 points!"
Response:
ZackTheGreat has locked in their parley pick: "Team A wins with 10 points!"
2. /show_picks
Description: Displays all saved parley picks in a formatted table.
Example:
bash
Copy code
/show_picks
Response:
sql
Copy code
| Nickname      | Parley Pick                     |
|---------------|---------------------------------|
| BobDylan      | Team A wins with 10 points!     |
| JohnDoe       | Team B scores over 20           |
Code Overview
Main Functionality:
lock_parley_pick(): Saves the parley pick to parley_picks.json using user ID as the key, and announces the pick publicly in the channel.
show_parley_picks(): Fetches data from the JSON file and displays it in a readable format using tabulate.
format_parley_picks(client, guild_id): Fetches user nicknames based on IDs to provide more personalized output.
JSON Storage Functions:
save_parley_pick(user_id, parley_pick): Saves data to parley_picks.json.
load_parley_picks(): Loads saved data from parley_picks.json.
Troubleshooting
Bot Commands Not Appearing?

Ensure that the bot has applications.commands permissions.
Make sure the correct intents are enabled (presence, members, message content) in the Discord Developer Portal.
Bot Not Fetching Usernames Properly?

Check if the bot has permissions to view members.
Make sure SERVER MEMBERS INTENT is enabled in the Developer Portal.
JSON File Issues:

Ensure the parley_picks.json file exists and is accessible by the bot. If the file is missing, the bot will create a new one.