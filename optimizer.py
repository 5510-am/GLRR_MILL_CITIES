from ortools.linear_solver import pywraplp
import pandas as pd

def optimize_with_constraints(df, legs, num_teams, min_female):

    solver = pywraplp.Solver.CreateSolver('SCIP')

    if solver is None:
        return pd.DataFrame()

    runners = df.index.tolist()
    leg_list = list(legs.keys())

    # -----------------------------
    # DECISION VARIABLES
    # -----------------------------
    x = {}
    for r in runners:
        for t in range(num_teams):
            for l in leg_list:
                x[(r,t,l)] = solver.BoolVar(f'x_{r}_{t}_{l}')

    # -----------------------------
    # CONSTRAINTS
    # -----------------------------

    # Each runner assigned exactly once
    for r in runners:
        solver.Add(
            sum(x[(r,t,l)] for t in range(num_teams) for l in leg_list) == 1
        )

    # Each team gets exactly one runner per leg
    for t in range(num_teams):
        for l in leg_list:
            solver.Add(
                sum(x[(r,t,l)] for r in runners) == 1
            )

    # Gender constraint (Mill Cities rule)
    for t in range(num_teams):
        solver.Add(
            sum(
                x[(r,t,l)] * int(df.loc[r,"is_female"])
                for r in runners for l in leg_list
            ) >= min_female
        )

    # -----------------------------
    # OBJECTIVE (FIXED - LINEAR)
    # -----------------------------

    # Total time for each team
    team_times = []
    for t in range(num_teams):
        team_time = solver.Sum(
            x[(r,t,l)] * df.loc[r, l + "_time"]
            for r in runners for l in leg_list
        )
        team_times.append(team_time)

    # Create variable for worst team
    max_time = solver.NumVar(0, solver.infinity(), "max_time")

    # Constrain all teams <= max_time
    for t in range(num_teams):
        solver.Add(team_times[t] <= max_time)

    # Minimize worst team (best balance)
    solver.Minimize(max_time)

    # -----------------------------
    # SOLVE
    # -----------------------------
    status = solver.Solve()

    if status != pywraplp.Solver.OPTIMAL:
        return pd.DataFrame()

    # -----------------------------
    # OUTPUT RESULTS
    # -----------------------------
    results = []

    for r in runners:
        for t in range(num_teams):
            for l in leg_list:
                if x[(r,t,l)].solution_value() > 0.5:
                    results.append({
                        "name": df.loc[r, "name"],
                        "team": t + 1,
                        "leg": l,
                        "leg_time": df.loc[r, l + "_time"]
                    })

    return pd.DataFrame(results)