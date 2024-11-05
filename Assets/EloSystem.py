import pandas as pd
import numpy as np
#from Assets.Methods import get_openai_key
from pathlib import Path
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
import openai
import json
import base64
from openai import OpenAI
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import hashlib
#from Main import guild


BASE_DIR = Path(__file__).resolve().parent
ONE_WEEK = BASE_DIR / "One_Weeks_Picks.json"
TWO_WEEK = BASE_DIR / "Two_Weeks_Picks.json"
HASH_FILE = BASE_DIR / "processed_files.json"
DATA_FILE = BASE_DIR / "parley_picks.json"

#openai.api_key = get_openai_key()
#client = OpenAI()
#Function to feed images of pick results to openAI. AI returns the results of the picks based on image content.

def compute_sha256(file_path):
    """Computes the SHA-256 hash of a file."""
    import hashlib
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

def is_duplicate_submission(file_path, hash_file=HASH_FILE):
    """
    Checks if the file has already been submitted by comparing its SHA-256 hash.

    Parameters:
    - file_path (Path): The path to the file to check.
    - hash_file (Path): The path to the JSON file where hashes are stored.

    Returns:
    - bool: True if the file is a duplicate, False otherwise.
    """
    # Compute the hash of the current file
    file_hash = compute_sha256(file_path)

    # Load existing hashes from JSON, handling empty or invalid JSON cases
    processed_hashes = []
    if hash_file.exists():
        try:
            with open(hash_file, 'r') as f:
                if f.read().strip():  # Check if file is non-empty
                    f.seek(0)  # Go back to the start of the file after reading
                    processed_hashes = json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: {hash_file} contains invalid JSON. Initializing as empty list.")

    # Check if the hash already exists
    if file_hash in processed_hashes:
        print(f"Duplicate submission detected for file: {file_path}")
        return True

    # If new, store the hash
    processed_hashes.append(file_hash)
    with open(hash_file, 'w') as f:
        json.dump(processed_hashes, f, indent=4)

    print(f"File {file_path} processed and hash stored.")
    return False

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def extract_text_with_results(image_path):
    """
    Sends a base64 encoded image to OpenAI for text extraction.
    """
    # Encode the image to base64 format
    base64_image = encode_image(image_path)

    # Send the encoded image to OpenAI with a prompt asking for content extraction
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "This image contains a list of bets with color indicators next to each title. "
                            "Please extract each bet title and indicate whether it has a green or red color next to it. "
                            "Return the results as structured valid syntax json data with no extra symbols, words, etc, mapping each bet title to 'win' if green and 'loss' if red."
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        },
                    },
                ],
            }
        ],
    )

 # Check and print response content for debugging
    response_content = response.choices[0].message.content

    # Clean up the response content
    cleaned_content = (
        response_content.replace("```json", "")  # Remove leading markdown syntax
        .replace("```", "")  # Remove trailing markdown syntax
        .strip()  # Remove any leading or trailing whitespace
    )

    # Try parsing the cleaned content as JSON
    try:
        extracted_results = json.loads(cleaned_content)
    except json.JSONDecodeError:
        print("DEBUG: Failed to parse cleaned content as JSON.")
        extracted_results = {}
    #print("DEBUG: Extracted results:", extracted_results)
    return extracted_results

def update_json_with_results(results, NoResults=DATA_FILE, ONE_WEEK_path=ONE_WEEK):
    """
    Updates JSON with win/loss results based on extracted data using fuzzy matching.
    Adds a "result" field with "win", "loss", or "miss" to each user entry.
    """
    # Load existing data
    with open(NoResults, "r") as file:
        data = json.load(file)

    # Threshold for minimum similarity ratio to consider a match
    fuzzy_threshold = 33

    # Create a list of tuples (user_id, parley_pick) for fuzzy matching
    parley_picks = [(user_id, value["parley_pick"]) for user_id, value in data.items()]

    # Initialize results as "miss" for all entries initially
    for user_id in data:
        data[user_id]["result"] = "miss"

    for bet_title, result in results.items():
        # Find the best match for the bet_title in parley_picks
        best_match = max(parley_picks, key=lambda x: fuzz.ratio(bet_title, x[1]))
        match_ratio = fuzz.ratio(bet_title, best_match[1])

        # Only update if match ratio meets or exceeds the threshold
        if match_ratio >= fuzzy_threshold:
            data[best_match[0]]["result"] = result  # Set "win" or "loss"

    # Write updated results to the output file
    with open(ONE_WEEK_path, "w") as ONE_WEEK:
        json.dump(data, ONE_WEEK, indent=4)

    return data  # Ensure updated data is returned

#update_json_with_results(results={'DEN NUGGETS': 'loss', 'TEXAS A&M': 'win','OVER 64.5': 'loss','VANDERBILT +18.5': 'win','A.J. BROWN': 'loss'},ONE_WEEK_path=ONE_WEEK)

def calculate_implied_probability(odds):
        if odds > 0:
            return 100 / (odds + 100)
        else:
            return abs(odds) / (abs(odds) + 100)






def convert_american_to_decimal(american_odds):
    if american_odds < 0:
        return (100 / abs(american_odds)) + 1
    else:
        return (american_odds / 100) + 1

def parlay_impact_analysis(player_bets_file, bet_amount=50, cap_adjustment=20):
    # Load JSON data from the file
    with open(player_bets_file, 'r') as file:
        player_bets_data = json.load(file)

    # Initialize ELO for each player if not already present
    for user_id, bet_info in player_bets_data.items():
        if "ELO" not in bet_info:
            player_bets_data[user_id]["ELO"] = 1000  # Starting ELO value

    # Restructure the JSON data into a list of dictionaries for processing
    formatted_bets = []
    for user_id, bet_info in player_bets_data.items():
        odds = float(bet_info.get("odds", 0))
        
        # Convert American odds to decimal odds
        decimal_odds = convert_american_to_decimal(odds)
        
        result = bet_info.get("result", "miss").lower()
        
        if decimal_odds == 1:  # After conversion, 1 implies zero odds in American terms
            print(f"WARNING: Missing or zero odds for user_id {user_id}. Skipping this entry.")
            continue  # Skip entries with missing or zero odds

        # Only add bets that are "win" or "loss" for ELO calculation
        if result in ["win", "loss"]:
            formatted_bets.append({
                "Player": user_id,
                "Parlay Pick": bet_info.get("parley_pick"),
                "Odds": decimal_odds,
                "Result": "Win" if result == "win" else "Loss",
                "Date": bet_info.get("date"),
                "ELO": player_bets_data[user_id]["ELO"]
            })

    # Convert to DataFrame for calculation
    df_bets = pd.DataFrame(formatted_bets)
    print("DEBUG: DataFrame structure:", df_bets.head())

    # Adjust ELO for each player based on their odds and result
    for index, row in df_bets.iterrows():
        # Calculate points based on odds difficulty
        difficulty_factor = (2.5 - row["Odds"])  # Lower odds get more points if won
        if row["Result"] == "Win":
            points = min(difficulty_factor * 10, cap_adjustment)
        else:  # Loss
            points = -min(difficulty_factor * 5, cap_adjustment)  # Lesser penalty for losing hard bets

        # Update ELO based on points
        player_bets_data[row["Player"]]["ELO"] += round(points, 1)
        print(f"DEBUG: Player {row['Player']} new ELO: {player_bets_data[row['Player']]['ELO']} with points: {points}")

    # Save the updated JSON data back to the file
    with open(player_bets_file, 'w') as file:
        json.dump(player_bets_data, file, indent=4)
    
    print("ELO scores have been updated in the JSON file.")





def get_nickname(user_id, guild):
    member = guild.get_member(int(user_id))
    return member.display_name if member else f"User {user_id}"

def ELO_Plot_Generator(guild, last_week_file = ONE_WEEK, two_weeks_ago=TWO_WEEK, output_path= BASE_DIR / "ELO_Rankings.png"):
    """
    Plots the ELO rank comparison between two weeks, using Discord nicknames.

    Parameters:
    - guild (discord.Guild): The guild object to fetch member nicknames.
    - last_week_file (str): Path to the JSON file containing ELO data for the current week.
    - two_weeks_ago (str): Path to the JSON file containing ELO data for the last week.
    - output_path (Path): Path where the plot image will be saved.
    """
    
    # Load JSON data from both files
    with open(two_weeks_ago, 'r') as f:
        last_week_data = json.load(f)

    with open(last_week_file, 'r') as f:
        current_week_data = json.load(f)

    # Prepare data for each player's ranks based on ELO in the two weeks
    players = []
    last_week_elo = {}
    current_week_elo = {}

    # Extract players and their ELOs from the previous week
    for player_id, info in last_week_data.items():
        player_name = get_nickname(player_id, guild)
        players.append(player_name)
        last_week_elo[player_name] = info.get("ELO", 1000)  # Default to 1000 if ELO missing

    # Extract players and their ELOs from the current week
    for player_id, info in current_week_data.items():
        player_name = get_nickname(player_id, guild)
        current_week_elo[player_name] = info.get("ELO", 1000)

    # Sort players by ELO for ranking
    sorted_last_week = sorted(last_week_elo.items(), key=lambda x: -x[1])
    sorted_current_week = sorted(current_week_elo.items(), key=lambda x: -x[1])

    # Get ranks for each player in both weeks
    last_week_ranks = {player: rank + 1 for rank, (player, _) in enumerate(sorted_last_week)}
    current_week_ranks = {player: rank + 1 for rank, (player, _) in enumerate(sorted_current_week)}

    # Plot rank changes
    plt.figure(figsize=(12, 8), facecolor='black')
    ax = plt.gca()
    ax.set_facecolor('black')

    for i, player in enumerate(players):
        initial_rank = last_week_ranks.get(player, len(players))  # Default to last if missing
        current_rank = current_week_ranks.get(player, len(players))

        # Plot initial rank (red for last week)
        plt.plot(initial_rank, i, 'o', color='red', markersize=12)
        plt.text(initial_rank, i, str(initial_rank), color='white', ha='center', va='center', fontweight='bold')
        
        # Plot current rank (green for this week)
        plt.plot(current_rank, i, 'o', color='green', markersize=12)
        plt.text(current_rank, i, str(current_rank), color='white', ha='center', va='center', fontweight='bold')
        
        # Draw arrow from previous to current rank
        plt.arrow(initial_rank, i, current_rank - initial_rank, 0,
                  head_width=0.2, head_length=0.2, 
                  fc='green' if current_rank < initial_rank else 'red',
                  ec='green' if current_rank < initial_rank else 'red',
                  linewidth=2, length_includes_head=True)

    # Add a legend
    red_patch = mpatches.Patch(color='red', label='Last Week')
    green_patch = mpatches.Patch(color='green', label='This Week')
    legend = plt.legend(handles=[red_patch, green_patch], loc='upper right', fontsize=12, facecolor='black', framealpha=0.7, edgecolor='white')
    for text in legend.get_texts():
        text.set_color("white")

    # Customize the plot appearance
    plt.yticks(range(len(players)), players, color='white')
    plt.xticks(range(1, len(players) + 1), color='white')
    plt.xlabel("Place", color='white', fontsize=14)
    plt.title("Power Rankings Comparison: Last Week vs. This Week", color='white', fontsize=16)
    plt.gca().invert_xaxis()  # Flip x-axis so rank 1 is on the right

    # Add gridlines for readability
    plt.grid(True, which='major', axis='x', color='gray', linestyle='--', alpha=0.5)

    # Save the plot to file
    plt.savefig(output_path, facecolor='black', bbox_inches='tight')
    #plt.show()

    return output_path

parlay_impact_analysis(ONE_WEEK)