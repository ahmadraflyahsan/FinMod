"""
Decline Curve Analysis Engine – Arps (Exponential, Hyperbolic, Harmonic)
+ Makeup Well Scheduler (manual & auto target)
"""
import numpy as np
from datetime import date
import pandas as pd

# ── Arps decline functions ────────────────────────────────────────────────────
def exp_decline(q0, Di, t):
    return q0 * np.exp(-Di * np.array(t))

def hyp_decline(q0, Di, b, t):
    t = np.array(t)
    return q0 / (1 + b * Di * t) ** (1/b)

def harm_decline(q0, Di, t):
    return q0 / (1 + Di * np.array(t))

def arps_decline(q0, Di, b, t_years):
    """Unified Arps: b=0 exponential, b=1 harmonic, 0<b<1 hyperbolic"""
    t = np.array(t_years, dtype=float)
    if b == 0:
        return exp_decline(q0, Di, t)
    elif b == 1:
        return harm_decline(q0, Di, t)
    else:
        return hyp_decline(q0, Di, b, t)

def cumulative_arps(q0, Di, b, t_years):
    t = np.array(t_years, dtype=float)
    if b == 0:
        return (q0 / Di) * (1 - np.exp(-Di * t))
    elif b == 1:
        return (q0 / Di) * np.log(1 + Di * t)
    else:
        return (q0 / ((1-b)*Di)) * (1 - (1 + b*Di*t)**((b-1)/b))

# ── Makeup well scheduler ─────────────────────────────────────────────────────
def run_dca(params):
    q0          = float(params["q0"])
    Di          = float(params["Di_annual"])
    b           = float(params.get("b", 0.0))
    cod         = params["cod_date"]
    max_yrs     = int(params["max_years"])
    cap         = float(params["install_cap"])
    thresh_pct  = float(params.get("threshold_pct", 90.0))
    mu_out      = float(params.get("mu_output") or 10.0)
    mu_succ     = float(params.get("mu_success", 80.0)) / 100
    mu_Di_raw   = params.get("mu_decline_rate")
    mu_Di       = float(mu_Di_raw) if mu_Di_raw else Di
    mode        = params.get("mu_schedule_mode", "auto")
    mu_manual   = [int(x) for x in params.get("mu_manual_years", [])]
    mu_max      = int(params.get("mu_max_wells", 20))

    years       = [cod.year + i for i in range(max_yrs)]
    t_from_cod  = list(range(max_yrs))
    threshold_q = cap * (thresh_pct / 100)

    # Base decline (no makeup)
    q_base = arps_decline(q0, Di, b, t_from_cod)

    # Makeup contributions: each entry = {start_t, q0, Di, b}
    makeup_contributions = []
    mu_schedule    = []
    total_mu_wells = 0
    q_with_mu      = np.zeros(max_yrs, dtype=float)

    for ti in range(max_yrs):
        yr    = years[ti]
        t_yr  = t_from_cod[ti]

        # Sum base + all makeup contributions at this timestep
        q_now = float(q_base[ti])
        for mc in makeup_contributions:
            dt = t_yr - mc["start_t"]
            if dt >= 0:
                # FIX: pass b correctly for each makeup contribution
                q_now += float(arps_decline(mc["q0"], mc["Di"], mc["b"], [dt])[0])

        q_with_mu[ti] = min(q_now, cap * 1.05)

        # Decide whether to add makeup well this year
        add_mu = False
        if mode == "auto":
            if q_now < threshold_q and total_mu_wells < mu_max:
                add_mu = True
        else:
            yr_from_cod = yr - cod.year
            if yr_from_cod in mu_manual and total_mu_wells < mu_max:
                add_mu = True

        if add_mu:
            effective_output = mu_out * mu_succ
            makeup_contributions.append({
                "start_t": t_yr,
                "q0":      effective_output,
                "Di":      mu_Di,
                "b":       b,   # FIX: store b with each contribution
            })
            total_mu_wells += 1
            # Recalc this timestep with new well added
            q_with_mu[ti] = min(q_now + effective_output, cap * 1.05)
            mu_schedule.append({
                "Year":            yr,
                "Yr from COD":     t_yr,
                "Wells Added":     1,
                "MW Added":        round(effective_output, 2),
                "Cumulative Wells":total_mu_wells,
                "Production After (MW)": round(float(q_with_mu[ti]), 2),
            })

    # Annual MWh (treat q as avg MW over year × 8760 hrs)
    mwh_annual = [float(q_with_mu[i]) * 8760 for i in range(max_yrs)]

    return {
        "years":          years,
        "t_from_cod":     t_from_cod,
        "q_base":         q_base.tolist(),
        "q_with_mu":      q_with_mu.tolist(),
        "mwh_annual":     mwh_annual,
        "mu_schedule":    mu_schedule,
        "install_cap":    cap,
        "threshold_q":    threshold_q,
        "total_mu_wells": total_mu_wells,
        "max_years":      max_yrs,
    }
