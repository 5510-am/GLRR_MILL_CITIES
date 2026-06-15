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

team_names = [
    "Negative Splitters",
    "Miles & Smiles",
    "Relay Rebels",
    "Pace Cadets",
    "Draft Dodgers"
]

# -----------------------------
# HELPER FUNCTIONS
# -----------------------------
def elevation_adjustment(elev_gain):
    return (elev_gain * 0.3) / 60  # minutes penalty

def calculate_leg_times(df):
    for leg, data in legs.items():
        base = df["pace"] * data["dist"] * data["difficulty"]
        elev = elevation_adjustment(data["elev"])
        df[leg+"_time"] = base + elev
    return df

# -----------------------------
# INPUT
# -----------------------------
uploaded = st.file_uploader("Upload CSV (name, pace)", type="csv")

if not uploaded:
    st.info("Upload a CSV to begin")
    st.stop()

df = pd.read_csv(uploaded)

if "name" not in df.columns or "pace" not in df.columns:
    st.error("CSV must have columns: name, pace")
    st.stop()

df = calculate_leg_times(df)

num_teams = st.sidebar.slider("Number of Teams", 1, max(1, len(df)//5), len(df)//5)

if "results" not in st.session_state:
    st.session_state.results = None

# -----------------------------
# OPTIMIZE
# -----------------------------
if st.button("⚖️ Optimize Teams"):
    results = optimize_with_constraints(df, legs, num_teams, [])
    st.session_state.results = results

# -----------------------------
# OUTPUT
# -----------------------------
if st.session_state.results is not None:

    res = st.session_state.results

    st.header("🏃 Teams")

    for t in sorted(res["team"].unique()):
        team_df = res[res["team"] == t]

        st.markdown(f"### 🟦 {random.choice(team_names)} (Team {t})")

        total = team_df["leg_time"].sum()
        st.caption(f"⏱ Total: {round(total,1)} min")

        for _, r in team_df.iterrows():
            st.write(f"{r['leg']} → {r['name']} ({round(r['leg_time'],1)} min)")

    # -----------------------------
    # EDIT MODE
    # -----------------------------
    st.header("✏️ Edit Assignments")

    edited = st.data_editor(res, use_container_width=True)

    # -----------------------------
    # QUICK SWAP
    # -----------------------------
    st.subheader("🔁 Quick Swap")

    r1 = st.selectbox("Runner 1", edited["name"])
    r2 = st.selectbox("Runner 2", edited["name"], key="swap")

    if st.button("Swap"):
        i1 = edited[edited["name"] == r1].index[0]
