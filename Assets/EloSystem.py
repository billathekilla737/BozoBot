import pandas as pd
import numpy as np
from Assets.Methods import get_openai_key
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

openai.api_key = get_openai_key()
client = OpenAI()
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

#def update_json_with_results(results, NoResults=DATA_FILE, OutputFile=ONE_WEEK):

def update_json_with_results(results, InputFile=DATA_FILE, OutputFile=DATA_FILE):
    """
    Updates JSON with win/loss results based on extracted data using fuzzy matching.
    Adds a "result" field with "win", "loss", or "miss" to each user entry, unless it already has "win" or "loss".
    """
    # Load existing data
    try:
        with open(InputFile, "r") as file:
            data = json.load(file)
        print("Loaded data from DATA_FILE successfully.")
    except Exception as e:
        print(f"Error loading DATA_FILE: {e}")
        return None

    # Increase threshold for better matches
    fuzzy_threshold = 30

    # Extract parley picks for fuzzy matching
    try:
        parley_picks = [(user_id, value["parley_pick"]) for user_id, value in data.items()]
        print(f"Parley picks extracted for fuzzy matching: {parley_picks}")
    except KeyError as e:
        print(f"Error accessing parley_pick in data: {e}")
        return None

    # Initialize "miss" only for entries that do not already have "win" or "loss"
    for user_id, details in data.items():
        if details.get("result") not in ["win", "loss"]:
            details["result"] = "miss"
    print("Initialized 'miss' only for entries without 'win' or 'loss'.")

    # Perform fuzzy matching and update results
    for bet_title, result in results.items():
        print(f"\nProcessing bet title: '{bet_title}' with expected result: '{result}'")

        # Attempt to find the best match for each bet title
        best_match = None
        best_ratio = 0
        for user_id, parley_pick in parley_picks:
            match_ratio = fuzz.token_set_ratio(bet_title, parley_pick)
            print(f"Comparing '{bet_title}' with '{parley_pick}' - Match Ratio: {match_ratio}")

            # Track the best match
            if match_ratio > best_ratio:
                best_match = (user_id, parley_pick)
                best_ratio = match_ratio

        # Check if the best match meets the threshold and update if it's currently "miss"
        if best_match and best_ratio >= fuzzy_threshold:
            if data[best_match[0]].get("result") == "miss":  # Only update if currently set to "miss"
                print(f"Match found: '{best_match[1]}' with ratio {best_ratio}. Updating result to '{result}'.")
                data[best_match[0]]["result"] = result
            else:
                print(f"Entry for '{best_match[1]}' already set to '{data[best_match[0]]['result']}', skipping update.")
        else:
            print(f"No suitable match for '{bet_title}' (best match ratio: {best_ratio}). Skipping update.")

    # Write updated results to ONE_WEEK
    try:
        with open(OutputFile, "w") as ONE_WEEK:
            json.dump(data, ONE_WEEK, indent=4)
        print("Results updated in ONE_WEEK file successfully.")
    except Exception as e:
        print(f"Error writing to ONE_WEEK file: {e}")

    return data  # Return updated data for verification if needed
#update_json_with_results(results={'DEN NUGGETS': 'loss', 'TEXAS A&M': 'win','OVER 64.5': 'loss','VANDERBILT +18.5': 'win','A.J. BROWN': 'loss'},OutputFile=ONE_WEEK)

def calculate_implied_probability(odds):
        if odds > 0:
            return 100 / (odds + 100)
        else:
            return abs(odds) / (abs(odds) + 100)

def parlay_impact_analysis(player_bets_file = ONE_WEEK, base_elo=1000, k_factor=20, high_risk_scaling_factor=1.5, high_risk_threshold=3.0):
    # Load JSON data from the file
    with open(player_bets_file, 'r') as file:
        player_bets_data = json.load(file)

    # Initialize ELO for each player if not already present
    for user_id, bet_info in player_bets_data.items():
        if "ELO" not in bet_info:
            player_bets_data[user_id]["ELO"] = base_elo  # Starting ELO value

    # Restructure the JSON data into a list of dictionaries for processing
    formatted_bets = []
    for user_id, bet_info in player_bets_data.items():
        odds = float(bet_info.get("odds", 0))
        
        # Convert American odds to decimal odds
        if odds >= 100:
            decimal_odds = (odds / 100) + 1
        elif odds <= -100:
            decimal_odds = (100 / abs(odds)) + 1
        else:
            print(f"Invalid odds for user_id {user_id}: {odds}")
            continue

        result = bet_info.get("result", "miss").lower()
        
        if decimal_odds <= 1:
            print(f"WARNING: Invalid decimal odds for user_id {user_id}. Skipping this entry.")
            continue

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
        current_elo = player_bets_data[row["Player"]]["ELO"]
        
        # Calculate win probability based on decimal odds
        win_prob = 1 / row["Odds"]

        # Determine if the bet is considered high risk
        is_high_risk = row["Odds"] >= high_risk_threshold
        
        # Adjust ELO change based on high-risk and low-risk adjustments
        if row["Result"] == "Win":
            # Apply high-risk scaling factor if applicable
            elo_change = k_factor * (1 / win_prob) * (high_risk_scaling_factor if is_high_risk else 1)
        else:  # Loss
            # Apply high-risk scaling factor if applicable
            elo_change = -k_factor * (1 / win_prob) * (high_risk_scaling_factor if is_high_risk else 1)

        # Update player's ELO
        new_elo = current_elo + elo_change
        player_bets_data[row["Player"]]["ELO"] = round(new_elo, 1)
        
        print(f"DEBUG: Player {row['Player']} new ELO: {new_elo} with ELO change: {elo_change}")

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
