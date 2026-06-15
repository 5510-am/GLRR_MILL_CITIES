import streamlit as st
import pandas as pd
import numpy as np
import random
from optimizer import optimize_with_constraints

st.set_page_config(layout="wide")
st.title("🏃 GLRR Mill Cities Relay Optimizer")

# -----------------------------
# COURSE PROFILES
# -----------------------------
legs = {
    "Leg1": {"dist": 5.0, "elev": 120, "difficulty": 1.00},
    "Leg2": {"dist": 4.8, "elev": 180, "difficulty": 1.05},
    "Leg3": {"dist": 5.5, "elev": 260, "difficulty": 1.15},
    "Leg4": {"dist": 3.9, "elev": 90,  "difficulty": 0.95},
    "Leg5": {"dist": 5.7, "elev": 220, "difficulty": 1.10}
}

# -----------------------------
# CATEGORIES (5-person only)
# -----------------------------
categories = {
    "CO": {"min_age": 18, "min_female": 2},
    "FO": {"min_age": 18, "min_female": 5},
    "MO": {"min_age": 18, "min_female": 0},
    "CSM": {"min_age": 30, "min_female": 2},
    "FSM": {"min_age": 30, "min_female": 5},
    "MSM": {"min_age": 30, "min_female": 0},
    "CM": {"min_age": 40, "min_female": 2},
    "FM": {"min_age": 40, "min_female": 5},
    "MM": {"min_age": 40, "min_female": 0},
    "CS": {"min_age": 50, "min_female": 2},
    "FS": {"min_age": 50, "min_female": 5},
    "MS": {"min_age": 50, "min_female": 0},
    "CV": {"min_age": 60, "min_female": 2},
    "MV": {"min_age": 60, "min_female": 0}
}

team_names = [
    "Negative Splitters",
    "Miles & Smiles",
    "Relay Rebels",
    "Pace Cadets",
    "Draft Dodgers"
]

# -----------------------------
# HELPERS
# -----------------------------
def elevation_adjustment(elev_gain):
    return (elev_gain * 0.3) / 60

def calculate_leg_times(df):
    for leg, data in legs.items():
        base = df["pace"] * data["dist"] * data["difficulty"]
        elev = elevation_adjustment(data["elev"])
        df[leg+"_time"] = base + elev
    return df

# -----------------------------
# INPUT
# -----------------------------
uploaded = st.file_uploader("Upload CSV (name, pace, age, gender)", type="csv")

if not uploaded:
    st.info("Upload a CSV to begin")
    st.stop()

df = pd.read_csv(uploaded)

required = ["name","pace","age","gender"]
for col in required:
    if col not in df.columns:
        st.error(f"Missing column: {col}")
        st.stop()

df["gender"] = df["gender"].str.upper()

# -----------------------------
# SELECT CATEGORY
# -----------------------------
category_code = st.sidebar.selectbox("Team Category", list(categories.keys()))
category = categories[category_code]

# -----------------------------
# FILTER ELIGIBLE
# -----------------------------
eligible = df[df["age"] >= category["min_age"]].copy()
eligible["is_female"] = eligible["gender"] == "F"

if len(eligible) < 5:
    st.error("Not enough eligible runners")
    st.stop()

# -----------------------------
# DETERMINE MAX TEAMS
# -----------------------------
min_female = category["min_female"]

num_female = eligible["is_female"].sum()
total = len(eligible)

max_teams_by_size = total // 5
max_teams_by_gender = num_female // min_female if min_female > 0 else max_teams_by_size

max_teams = min(max_teams_by_size, max_teams_by_gender)

if max_teams == 0:
    st.error("Not enough runners to form valid teams")
    st.stop()

num_teams = st.sidebar.slider("Number of Teams", 1, max_teams, max_teams)

# -----------------------------
# SELECT ONLY VALID RUNNERS
# -----------------------------
required_total = num_teams * 5
required_female = num_teams * min_female

eligible = eligible.sort_values("pace")

selected_f = eligible[eligible["is_female"]].head(required_female)
remaining = eligible.drop(selected_f.index)
selected_other = remaining.head(required_total - required_female)

selected = pd.concat([selected_f, selected_other])
selected = calculate_leg_times(selected)

excluded = eligible.drop(selected.index)

# -----------------------------
# OPTIMIZE
# -----------------------------
if st.button("⚖️ Build Teams"):
    results = optimize_with_constraints(
        selected,
        legs,
        num_teams,
        min_female
    )
    st.session_state["results"] = results

# -----------------------------
# OUTPUT
# -----------------------------
if "results" in st.session_state:

    res = st.session_state["results"]

    st.header("🏃 Teams")

    for t in sorted(res["team"].unique()):
        team_df = res[res["team"] == t]

        st.markdown(f"### 🟦 {random.choice(team_names)} (Team {t})")

        total_time = team_df["leg_time"].sum()
        st.caption(f"⏱ Total: {round(total_time,1)} min")

        for _, r in team_df.iterrows():
            st.write(f"{r['leg']} → {r['name']} ({round(r['leg_time'],1)})")

    # -----------------------------
    # TEAM PERFORMANCE
    # -----------------------------
    st.header("📊 Team Performance")

    team_summary = res.groupby("team")["leg_time"].sum()
    st.bar_chart(team_summary)

    spread = team_summary.max() - team_summary.min()
    st.metric("Time Spread", f"{round(spread,1)} min")

    # -----------------------------
    # EXCLUDED RUNNERS
    # -----------------------------
    if len(excluded) > 0:
        st.header("🚫 Not Assigned to Teams")
        st.dataframe(excluded[["name","pace","age","gender"]])

    # -----------------------------
    # EXPORT
    # -----------------------------
    st.download_button(
        "Download CSV",
        res.to_csv(index=False),
        "relay_teams.csv"
    )
