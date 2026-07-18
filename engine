"""
Geothermal Economic Engine v2 — full cashflow per Excel model
Produces: EBITDA → EBIT → UFCF → LFCF → Discounted CF
"""
import numpy as np
from datetime import date

def safe(p, key, default=0.0):
    v = p.get(key, default)
    return float(v) if v is not None else float(default)

def npv_calc(rate, cashflows):
    return sum(cf / (1+rate)**t for t, cf in enumerate(cashflows))

def irr_calc(cashflows, guess=0.1):
    cf = np.array(cashflows, dtype=float)
    if not (any(cf>0) and any(cf<0)): return None
    rate = guess
    for _ in range(2000):
        f  = sum(c/(1+rate)**t for t,c in enumerate(cf))
        df = sum(-t*c/(1+rate)**(t+1) for t,c in enumerate(cf))
        if abs(df) < 1e-12: break
        rate_new = rate - f/df
        if abs(rate_new-rate) < 1e-8: return rate_new
        rate = max(rate_new, -0.9999)
    return rate

def payback(cashflows, disc=False, r=0.0):
    cum = 0.0
    for t, cf in enumerate(cashflows):
        cum += cf/(1+r)**t if disc else cf
        if cum >= 0: return t
    return None

def pi_calc(cashflows, r):
    pv_in  = sum(cf/(1+r)**t for t,cf in enumerate(cashflows) if cf>0)
    pv_out = sum(-cf/(1+r)**t for t,cf in enumerate(cashflows) if cf<0)
    return pv_in/pv_out if pv_out else None

def run_model(p):
    """Full model including EBITDA/EBIT/UFCF/LFCF/Discounted"""
    sy   = int(safe(p,"start_year",2026))
    mh   = int(safe(p,"model_horizon",40))
    years = list(range(sy, sy+mh))
    n    = len(years)

    cod_year  = int(safe(p,"cod_year",sy+5))
    cod_month = int(safe(p,"cod_month",1))
    lifetime  = int(safe(p,"lifetime",30))
    end_year  = cod_year + lifetime

    # Rates
    wacc      = safe(p,"hurdle_rate",0.076)
    cost_esc  = safe(p,"cost_esc_rate",0.02355)
    tariff_esc= safe(p,"tariff_esc_rate",0.02355)
    corp_tax  = safe(p,"corp_tax_rate",0.22)
    prod_fee  = safe(p,"production_fee_pct",0.025)
    prod_bonus= safe(p,"production_bonus_pct",0.005)
    dep_yrs_wf= int(safe(p,"dep_years_wells",20))
    dep_yrs_pp= int(safe(p,"dep_years_pp",25))
    vat_rate  = safe(p,"vat",0.11)
    base_idr  = safe(p,"base_idr_usd",16500)

    def ce(yr): return (1+cost_esc)**(yr-sy)
    def te(yr):
        if yr<cod_year: return 1.0
        return (1+tariff_esc)**(yr-cod_year)

    # ── Production profile (from well schedule if provided) ──────────────────
    cap   = safe(p,"install_capacity",50)
    cf_pct= safe(p,"capacity_factor",0.9)
    dec   = safe(p,"production_decline",0.03)
    q0    = safe(p,"initial_steam_supply", cap*0.7)
    scheme= p.get("scheme","PJBL")

    # Well schedule: list of {year, type, mw_output}
    well_schedule = p.get("well_schedule", [])

    net_gen = {}
    steam_q = {}
    for yr in years:
        if yr < cod_year or yr >= end_year:
            net_gen[yr] = 0.0; steam_q[yr] = 0.0; continue
        t = yr - cod_year
        op_days = 365
        if yr == cod_year:
            op_days = int((12-cod_month+1)/12*365)
        # Base decline
        q_yr = q0 * (1-dec)**t
        # Add makeup wells from schedule
        for ws in well_schedule:
            ws_yr = ws.get("year",9999)
            ws_type = ws.get("type","")
            if "makeup" in ws_type.lower() and ws_yr <= yr:
                dt = yr - ws_yr
                q_yr += ws.get("mw_output",0) * (1-dec)**dt
        steam_q[yr] = max(q_yr, 0)
        net_gen[yr] = min(cap, steam_q[yr]) * cf_pct * op_days * 24

    # ── Revenue ───────────────────────────────────────────────────────────────
    revenue = {}
    for yr in years:
        if net_gen.get(yr,0) == 0: revenue[yr]=0.0; continue
        t10 = yr - cod_year + 1
        if scheme=="PJBU":
            tariff = safe(p,"steam_price_1_10",6.875) if t10<=10 else safe(p,"steam_price_11_30",5.31)
        elif scheme=="CA":
            tariff = safe(p,"conv_fee_1_10",3.475) if t10<=10 else safe(p,"conv_fee_11_30",2.69)
        else:  # PJBL
            tariff = safe(p,"elec_fee_1_10",10.35) if t10<=10 else safe(p,"elec_fee_11_30",8.0)
        revenue[yr] = net_gen[yr] * tariff * te(yr) / 100_000  # kUSD

    # ── CAPEX from spending schedule ──────────────────────────────────────────
    capex = {yr:0.0 for yr in years}
    # Spending schedule: dict {yr: {cost_item: amount}}
    spend_sched = p.get("spending_schedule", {})
    if spend_sched:
        for yr_str, items in spend_sched.items():
            yr = int(yr_str)
            if yr in capex:
                capex[yr] += sum(float(v or 0) for v in items.values())
    else:
        # Fallback: auto-schedule from lump sum inputs
        # Exploration (year 1)
        exp_total = (safe(p,"ga_exploration")+safe(p,"survey_4g")+
                     safe(p,"land_infra_exploration")+
                     safe(p,"exploration_well_cost")*safe(p,"n_exploration_wells",2))
        if sy in capex: capex[sy] += exp_total * ce(sy)

        # Development spread over dev_years
        dev_yrs = int(safe(p,"dev_years",5))
        dev_total = (safe(p,"ga_exploitation")*safe(p,"dev_years_ga",5)+
                     safe(p,"land_infra_exploitation")+safe(p,"feed_cost")+
                     safe(p,"fcrs_cost")+safe(p,"power_plant_cost")+
                     safe(p,"transmission_cost")+
                     safe(p,"prod_well_cost")*safe(p,"n_prod_wells",3)+
                     safe(p,"inj_well_cost")*safe(p,"n_inj_wells",4)+
                     safe(p,"idc"))
        wts = [0.05,0.15,0.35,0.30,0.15][:dev_yrs]
        s = sum(wts); wts = [w/s for w in wts]
        for i,w in enumerate(wts):
            yr = sy+1+i
            if yr in capex: capex[yr] += dev_total*w*ce(yr)

        # Makeup wells from well schedule
        for ws in well_schedule:
            ws_yr = ws.get("year",9999)
            if "makeup" in str(ws.get("type","")).lower() and ws_yr in capex:
                capex[ws_yr] += (safe(p,"makeup_well_cost")+
                                 safe(p,"infra_makeup")/max(safe(p,"n_makeup_wells",1),1))*ce(ws_yr)

    # ── OPEX ─────────────────────────────────────────────────────────────────
    opex = {yr:0.0 for yr in years}
    om_steam = safe(p,"om_steam_annual")
    om_plant = safe(p,"om_plant_annual")
    maj_oh   = safe(p,"major_overhaul_cost")
    maj_int  = int(safe(p,"major_overhaul_interval",5))
    min_oh   = safe(p,"minor_overhaul_cost")
    min_int  = int(safe(p,"minor_overhaul_interval",2))
    chem     = safe(p,"chemical_treatment")
    trans    = safe(p,"opex_transmission")
    pbb      = safe(p,"pbb_annual")

    for yr in years:
        if yr<cod_year or yr>=end_year: continue
        t10 = yr-cod_year+1
        base = (om_steam+om_plant+chem+trans+pbb)*ce(yr)
        if t10>0 and t10%maj_int==0: base += maj_oh*ce(yr)
        elif t10>0 and t10%min_int==0: base += min_oh*ce(yr)
        opex[yr] = base

    # ── EBITDA ────────────────────────────────────────────────────────────────
    ebitda = {yr: revenue.get(yr,0)-opex.get(yr,0) for yr in years}

    # ── Depreciation ─────────────────────────────────────────────────────────
    # Wells & infra: straight line dep_yrs_wf years from COD
    # Power plant: dep_yrs_pp years from COD
    total_wells_capex = (safe(p,"prod_well_cost")*safe(p,"n_prod_wells",3)+
                         safe(p,"inj_well_cost")*safe(p,"n_inj_wells",4)+
                         safe(p,"infra_makeup"))
    total_pp_capex    = safe(p,"power_plant_cost")+safe(p,"fcrs_cost")
    dep_wells_annual  = total_wells_capex/dep_yrs_wf if dep_yrs_wf>0 else 0
    dep_pp_annual     = total_pp_capex/dep_yrs_pp    if dep_yrs_pp>0 else 0

    depreciation = {}
    for yr in years:
        d = 0.0
        if cod_year<=yr<cod_year+dep_yrs_wf: d += dep_wells_annual
        if cod_year<=yr<cod_year+dep_yrs_pp: d += dep_pp_annual
        depreciation[yr] = d

    # ── EBIT & Tax ────────────────────────────────────────────────────────────
    ebit      = {yr: ebitda[yr]-depreciation.get(yr,0) for yr in years}
    tax_loss_cf = 0.0
    prod_fee_amt  = {}
    prod_bonus_amt= {}
    income_tax    = {}
    ebt           = {}
    for yr in years:
        rev = revenue.get(yr,0)
        pf  = rev*prod_fee
        pb  = rev*prod_bonus
        prod_fee_amt[yr]   = pf
        prod_bonus_amt[yr] = pb
        _ebt = ebit[yr] - pf - pb
        # Tax loss carryforward
        _ebt -= tax_loss_cf
        if _ebt < 0:
            tax_loss_cf = -_ebt
            _ebt = 0
        else:
            tax_loss_cf = 0
        ebt[yr] = _ebt
        income_tax[yr] = max(_ebt*corp_tax, 0)

    # ── UFCF (Unlevered Free Cash Flow) ──────────────────────────────────────
    ufcf = {}
    for yr in years:
        ufcf[yr] = (ebitda[yr]
                    - income_tax.get(yr,0)
                    - capex.get(yr,0)
                    + depreciation.get(yr,0)
                    - prod_fee_amt.get(yr,0)
                    - prod_bonus_amt.get(yr,0))

    # ── Debt service (3 loans) ────────────────────────────────────────────────
    def loan_schedule(principal, start_yr, repay_yrs, grace_yrs, interest_rate,
                      front_end_fee, commitment_fee):
        """Returns dict yr→{drawdown, interest, principal_repay, total_service}"""
        sched = {yr:{"drawdown":0,"interest":0,"principal_repay":0,"service":0}
                 for yr in years}
        if principal<=0 or start_yr not in years: return sched
        # Drawdown at start year
        sched[start_yr]["drawdown"] = principal
        outstanding = principal
        repay_start = start_yr + grace_yrs + 1
        annual_repay = principal/repay_yrs if repay_yrs>0 else 0
        for yr in years:
            if yr < start_yr: continue
            interest = outstanding * interest_rate
            sched[yr]["interest"] = interest
            if yr >= repay_start and outstanding > 0:
                rep = min(annual_repay, outstanding)
                sched[yr]["principal_repay"] = rep
                outstanding = max(outstanding-rep, 0)
            sched[yr]["service"] = interest + sched[yr]["principal_repay"]
        return sched

    # Exploration loan
    exp_loan_p  = safe(p,"exp_loan_principal")
    exp_loan_yr = int(safe(p,"exp_loan_start_year",sy))
    exp_sched   = loan_schedule(exp_loan_p, exp_loan_yr,
                                int(safe(p,"exp_loan_repay_years",0)),
                                int(safe(p,"exp_loan_grace_period",0)),
                                safe(p,"exp_loan_interest_rate"),
                                safe(p,"exp_loan_front_end_fee"),
                                safe(p,"exp_loan_commitment_fee"))

    # Dev Upstream loan
    dev_up_p   = safe(p,"dev_upstream_loan_principal")
    dev_up_yr  = int(safe(p,"dev_upstream_loan_start_year",sy+1))
    dev_up_sch = loan_schedule(dev_up_p, dev_up_yr,
                               int(safe(p,"dev_upstream_repay_years",10)),
                               int(safe(p,"dev_upstream_grace_period",2)),
                               safe(p,"dev_upstream_interest_rate",0.0472),
                               safe(p,"dev_upstream_front_end_fee",0.0025),
                               safe(p,"dev_upstream_commitment_fee",0.0025))

    # Dev Downstream (Corp) loan
    dev_dn_p   = safe(p,"dev_downstream_loan_principal")
    dev_dn_yr  = int(safe(p,"dev_downstream_loan_start_year",sy+2))
    dev_dn_sch = loan_schedule(dev_dn_p, dev_dn_yr,
                               int(safe(p,"dev_downstream_repay_years",25)),
                               int(safe(p,"dev_downstream_grace_period",5)),
                               safe(p,"dev_downstream_interest_rate",0.0492),
                               safe(p,"dev_downstream_front_end_fee",0.0025),
                               safe(p,"dev_downstream_commitment_fee",0.0035))

    # Total debt service per year
    interest_total = {}
    debt_repay     = {}
    for yr in years:
        interest_total[yr] = (exp_sched[yr]["interest"] +
                              dev_up_sch[yr]["interest"] +
                              dev_dn_sch[yr]["interest"])
        debt_repay[yr]     = (exp_sched[yr]["principal_repay"] +
                              dev_up_sch[yr]["principal_repay"] +
                              dev_dn_sch[yr]["principal_repay"])

    # ── LFCF (Levered Free Cash Flow) ────────────────────────────────────────
    lfcf = {}
    for yr in years:
        lfcf[yr] = ufcf[yr] - interest_total.get(yr,0) - debt_repay.get(yr,0)

    # ── Discounted CFs ────────────────────────────────────────────────────────
    disc_factor     = {yr: 1/(1+wacc)**(yr-sy) for yr in years}
    disc_ufcf       = {yr: ufcf[yr]*disc_factor[yr] for yr in years}
    disc_lfcf       = {yr: lfcf[yr]*disc_factor[yr] for yr in years}
    cum_ufcf        = {}; run=0.0
    for yr in years: run+=ufcf[yr]; cum_ufcf[yr]=run
    cum_lfcf        = {}; run=0.0
    for yr in years: run+=lfcf[yr]; cum_lfcf[yr]=run
    cum_disc_ufcf   = {}; run=0.0
    for yr in years: run+=disc_ufcf[yr]; cum_disc_ufcf[yr]=run
    cum_disc_lfcf   = {}; run=0.0
    for yr in years: run+=disc_lfcf[yr]; cum_disc_lfcf[yr]=run

    # ── KPIs ─────────────────────────────────────────────────────────────────
    ufcf_list = [ufcf[yr] for yr in years]
    lfcf_list = [lfcf[yr] for yr in years]
    npv_ufcf  = npv_calc(wacc, ufcf_list)
    npv_lfcf  = npv_calc(wacc, lfcf_list)
    irr_ufcf  = irr_calc(ufcf_list)
    irr_lfcf  = irr_calc(lfcf_list)
    pb_ufcf   = payback(ufcf_list)
    pb_lfcf   = payback(lfcf_list)
    pb_disc   = payback(ufcf_list, disc=True, r=wacc)
    pi        = pi_calc(ufcf_list, wacc)
    tot_gen   = sum(net_gen.values())/1e3  # GWh
    lcoe      = ((sum(capex.values())+sum(opex.values())) /
                 sum(net_gen.values())*1e5) if sum(net_gen.values())>0 else 0

    return {
        "years":years, "net_gen":net_gen, "steam_q":steam_q,
        "revenue":revenue, "capex":capex, "opex":opex,
        "ebitda":ebitda, "depreciation":depreciation, "ebit":ebit,
        "prod_fee":prod_fee_amt, "prod_bonus":prod_bonus_amt,
        "ebt":ebt, "income_tax":income_tax,
        "ufcf":ufcf, "lfcf":lfcf,
        "disc_factor":disc_factor,
        "disc_ufcf":disc_ufcf, "disc_lfcf":disc_lfcf,
        "cum_ufcf":cum_ufcf, "cum_lfcf":cum_lfcf,
        "cum_disc_ufcf":cum_disc_ufcf, "cum_disc_lfcf":cum_disc_lfcf,
        "interest":interest_total, "debt_repay":debt_repay,
        "exp_loan_sched":exp_sched, "dev_up_loan_sched":dev_up_sch,
        "dev_dn_loan_sched":dev_dn_sch,
        # KPIs
        "npv":npv_ufcf, "npv_ufcf":npv_ufcf, "npv_lfcf":npv_lfcf,
        "irr":irr_ufcf, "irr_ufcf":irr_ufcf, "irr_lfcf":irr_lfcf,
        "payback":pb_ufcf, "disc_payback":pb_disc,
        "payback_lfcf":pb_lfcf,
        "pi":pi, "lcoe":lcoe,
        "total_capex":sum(capex.values()),
        "total_opex":sum(opex.values()),
        "total_rev":sum(revenue.values()),
        "total_gen_gwh":tot_gen,
    }

def run_sensitivity(base_params, variable, multipliers, metric="npv_ufcf"):
    results = []
    for m in multipliers:
        p2 = base_params.copy()
        base_val = base_params.get(variable, 0) or 0
        p2[variable] = base_val * m
        try:
            res = run_model(p2)
            results.append(res.get(metric, res.get("npv", 0)))
        except:
            results.append(0)
    return results
