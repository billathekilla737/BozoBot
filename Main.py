import discord
from discord import app_commands
from tabulate import tabulate

# Your bot token
TOKEN = 'YOUR_DISCORD_BOT_TOKEN'

# Intents setup
intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# League members and their results (initially all weeks are grey ⬜)
league_data = {
    "Aaren": ["⬜"] * 18,
    "Ben": ["⬜"] * 18,
    "Christian": ["⬜"] * 18,
    "Isaiah": ["⬜"] * 18,
    "Jake": ["⬜"] * 18,
    "Max": ["⬜"] * 18,
    "Nathan": ["⬜"] * 18,
    "Noah": ["⬜"] * 18,
    "Patton": ["⬜"] * 18,
    "Preston": ["⬜"] * 18,
    "Zack": ["⬜"] * 18,
}

# Function to create the table
def create_table():
    headers = ["Name"] + [f"Week {i+1}" for i in range(18)]
    table = [[name] + weeks for name, weeks in league_data.items()]
    return tabulate(table, headers, tablefmt="github")

# Command to show the league table
@tree.command(name="show_league", description="Displays the league table with all members and their current results.")
async def show_league(interaction: discord.Interaction):
    table_str = create_table()
    await interaction.response.send_message(f"```{table_str}```")

# Command to update a player's result
@tree.command(name="update_result", description="Update a player's result for a specific week.")
async def update_result(interaction: discord.Interaction, name: str, week: int, result: str):
    if name in league_data and 1 <= week <= 18 and result in ["⬜", "🟩", "🟥"]:
        league_data[name][week - 1] = result
        await interaction.response.send_message(f"Updated {name}'s result for Week {week} to {result}.")
    else:
        await interaction.response.send_message("Invalid input! Make sure the name, week, and result are correct.")

# Event to trigger once the bot is ready and sync the commands with Discord
@client.event
async def on_ready():
    await tree.sync()
    print(f'Logged in as {client.user}!')

# Run the bot
client.run(TOKEN)
