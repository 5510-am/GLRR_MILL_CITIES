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
# MILL CITIES CATEGORIES (5-person ONLY)
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
# CATEGORY
# -----------------------------
category_code = st.sidebar.selectbox("Team Category", list(categories.keys()))
category = categories[category_code]

eligible = df[df["age"] >= category["min_age"]].copy()

if len(eligible) < 5:
    st.error("Not enough eligible runners")
    st.stop()

eligible["is_female"] = eligible["gender"] == "F"

eligible = calculate_leg_times(eligible)

num_teams = st.sidebar.slider("Number of Teams", 1, max(1,len(eligible)//5), len(eligible)//5)

# -----------------------------
# OPTIMIZE
# -----------------------------
if "results" not in st.session_state:
    st.session_state.results = None

if st.button("⚖️ Optimize Teams"):
    results = optimize_with_constraints(
        eligible,
        legs,
        num_teams,
        locked=[],
        min_female=category["min_female"]
    )
    st.session_state.results = results

# -----------------------------
# OUTPUT
# -----------------------------
if st.session_state.results is not None:

    res = st.session_state.results

    if res.empty:
        st.error("No valid teams found — check age/gender balance")
        st.stop()

    st.header("🏃 Teams")

    for t in sorted(res["team"].unique()):
        team_df = res[res["team"] == t]

        st.markdown(f"### 🟦 {random.choice(team_names)} (Team {t})")
        total = team_df["leg_time"].sum()

        st.caption(f"⏱ Total: {round(total,1)} min")

        for _, r in team_df.iterrows():
            st.write(f"{r['leg']} → {r['name']} ({round(r['leg_time'],1)})")

    # -----------------------------
    # EDIT MODE
    # -----------------------------
    st.header("✏️ Edit Assignments")
    edited = st.data_editor(res, use_container_width=True)

    # -----------------------------
    # SWAP TOOL
    # -----------------------------
    st.subheader("🔁 Quick Swap")
    r1 = st.selectbox("Runner 1", edited["name"])
    r2 = st.selectbox("Runner 2", edited["name"], key="swap")

    if st.button("Swap"):
        i1 = edited[edited["name"] == r1].index[0]
        i2 = edited[edited["name"] == r2].index[0]
        temp = edited.loc[i1, ["team","leg"]].copy()
        edited.loc[i1, ["team","leg"]] = edited.loc[i2, ["team","leg"]]
        edited.loc[i2, ["team","leg"]] = temp
        st.session_state.results = edited

    # -----------------------------
    # PERFORMANCE
    # -----------------------------
    st.header("📊 Team Performance")

    team_summary = edited.groupby("team")["leg_time"].sum().reset_index()
    team_summary.rename(columns={"leg_time":"total_time"}, inplace=True)
    team_summary["rank"] = team_summary["total_time"].rank()

    st.dataframe(team_summary.sort_values("total_time"))
    st.bar_chart(team_summary.set_index("team")["total_time"])

    spread = team_summary["total_time"].max() - team_summary["total_time"].min()
    st.metric("Time Spread", f"{round(spread,1)} min")

    # -----------------------------
    # EMAIL EXPORT
    # -----------------------------
    def format_email(df):
        txt = ""
        for t in sorted(df["team"].unique()):
            txt += f"\nTeam {t}\n"
            for _, r in df[df["team"]==t].iterrows():
                txt += f"{r['leg']}: {r['name']}\n"
        return txt

    st.text_area("📧 Copy for Email", format_email(edited))

    csv = edited.to_csv(index=False).encode()
    st.download_button("Download CSV", csv, "relay_teams.csv")
