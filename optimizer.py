from ortools.linear_solver import pywraplp
import pandas as pd

def optimize_with_constraints(df, legs, num_teams, min_female):

    solver = pywraplp.Solver.CreateSolver('SCIP')

    runners = df.index.tolist()
    leg_list = list(legs.keys())

    x = {}
    for r in runners:
        for t in range(num_teams):
            for l in leg_list:
                x[(r,t,l)] = solver.BoolVar(f'x_{r}_{t}_{l}')

    # each runner once
    for r in runners:
        solver.Add(sum(x[(r,t,l)] for t in range(num_teams) for l in leg_list) == 1)

    # each team gets one per leg
    for t in range(num_teams):
        for l in leg_list:
            solver.Add(sum(x[(r,t,l)] for r in runners) == 1)

    # gender constraint
    for t in range(num_teams):
        solver.Add(
            sum(
                x[(r,t,l)] * int(df.loc[r,"is_female"])
                for r in runners for l in leg_list
            ) >= min_female
        )

    # objective: balance teams
    team_times = []
    for t in range(num_teams):
        time = solver.Sum(
            x[(r,t,l)] * df.loc[r, l+"_time"]
            for r in runners for l in leg_list
        )
        team_times.append(time)

    avg = solver.Sum(team_times) / num_teams

    solver.Minimize(
        solver.Sum((team_times[t] - avg)*(team_times[t] - avg)
        for t in range(num_teams))
    )

    status = solver.Solve()

    if status != pywraplp.Solver.OPTIMAL:
        return pd.DataFrame()

    results = []
    for r in runners:
        for t in range(num_teams):
            for l in leg_list:
                if x[(r,t,l)].solution_value() > 0.5:
                    results.append({
                        "name": df.loc[r,"name"],
                        "team": t+1,
                        "leg": l,
                        "leg_time": df.loc[r,l+"_time"]
                    })

    return pd.DataFrame(results)