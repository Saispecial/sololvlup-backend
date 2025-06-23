from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import json
import random
import requests
import os
from datetime import datetime

app = FastAPI()

# Allow Netlify frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with your Netlify domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----- RPG ENGINE STATE -----
rpg_state = {
    "Level": 1,
    "Rank": "E",
    "XP": 0,
    "Stats": {
        "IQ": 10,
        "EQ": 10,
        "Strength": 10,
        "Technical Attribute": 10,
        "Aptitude": 10,
        "Problem Solving": 10
    },
    "ActiveQuests": {
        "Daily": [],
        "Main": None  # Made dynamic
    },
    "QuestHistory": [],
    "XPLog": {}
}

# ----- CONSTANTS -----
QUEST_POOL = [
    ("Solve 1 DSA Problem", 50, ["IQ", "Problem Solving"]),
    ("Write Journal Reflection", 10, ["EQ"]),
    ("Deep Coding (Java – 1 Hour)", 25, ["Technical Attribute", "Aptitude"]),
    ("Drink 2L Water", 5, ["Strength"]),
    ("Study AI Concepts", 15, ["Technical Attribute", "IQ"]),
    ("1 Hour Creative Writing", 20, ["EQ", "Problem Solving"])
]

RANKS = ["E", "D", "C", "B", "A", "S", "S+"]

# ----- HELPER FUNCTIONS -----
def level_up():
    level = rpg_state["Level"]
    xp = rpg_state["XP"]
    while xp >= level * 100:
        rpg_state["Level"] += 1
        level = rpg_state["Level"]
        for stat in rpg_state["Stats"]:
            rpg_state["Stats"][stat] += 1
        if level in [10, 20, 35, 50]:
            current_rank_index = RANKS.index(rpg_state["Rank"])
            if current_rank_index + 1 < len(RANKS):
                rpg_state["Rank"] = RANKS[current_rank_index + 1]

def log_xp():
    today = datetime.now().strftime("%Y-%m-%d")
    rpg_state["XPLog"][today] = rpg_state["XP"]


# ----- API ROUTES -----

@app.get("/arise")
def get_profile():
    return rpg_state


@app.post("/forge")
def forge():
    selected = random.sample(QUEST_POOL, 3)
    rpg_state["ActiveQuests"]["Daily"] = [q[0] for q in selected]
    if not rpg_state["ActiveQuests"]["Main"]:
        rpg_state["ActiveQuests"]["Main"] = "Path to Global Recognition"
    return {"DailyQuests": rpg_state["ActiveQuests"]["Daily"], "MainQuest": rpg_state["ActiveQuests"]["Main"]}


@app.post("/complete/{quest_name}")
def complete_quest(quest_name: str):
    match = next((q for q in QUEST_POOL if quest_name.lower() in q[0].lower()), None)
    if not match:
        return {"error": "❌ Quest not found"}

    quest_title, xp_reward, affected_stats = match
    if quest_title not in rpg_state["ActiveQuests"]["Daily"]:
        return {"error": "⚠️ Quest not active today"}

    rpg_state["XP"] += xp_reward
    for stat in affected_stats:
        rpg_state["Stats"][stat] += 1

    rpg_state["ActiveQuests"]["Daily"].remove(quest_title)
    rpg_state["QuestHistory"].append({"quest": quest_title, "xp": xp_reward, "date": datetime.now().isoformat()})
    level_up()
    log_xp()
    return {"message": f"✅ {quest_title} completed. Gained {xp_reward} XP.", "currentXP": rpg_state["XP"]}


# ---- AI Assistant with HuggingFace phi-2 ----

@app.post("/ask")
async def ask(request: Request):
    data = await request.json()
    prompt = data.get("query", "")
    if not prompt:
        return {"error": "No query provided."}

    headers = {
        "Authorization": f"Bearer {os.environ.get('HUGGINGFACE_TOKEN')}"
    }
    payload = {
        "inputs": f"You are an RPG assistant. Interpret this command: '{prompt}' and provide a helpful response.",
        "parameters": {
            "max_new_tokens": 60,
            "temperature": 0.7
        }
    }

    response = requests.post(
        "https://api-inference.huggingface.co/models/microsoft/phi-2",
        headers=headers,
        json=payload
    )

    if response.status_code == 200:
        result = response.json()
        return {"response": result[0].get("generated_text", "")}
    else:
        return {"error": "HuggingFace API call failed."}
