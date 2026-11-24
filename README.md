# PetroPulse: Oil Shock Lag-Time Model & Bio-BCP Simulator

 Econometric time-series lag analyzer and Business Continuity Plan (**Bio-BCP**) policy simulator developed for **OIL SHOCK Hack! — Thailand Earth Day 2026 (Track A)** *(UTCC School of Economics & School of Engineering × CreativeLab × Nakhonratchasima Chamber of Commerce — Team Thinktanker)*.

* **Competition Pitch Deck:** [`Thinktanker_A-.pdf`](./Thinktanker_A-.pdf)
* **Live Interactive Simulator:** `https://benjarong-dev.github.io/petropulse-oil-shock-bcp-simulator/`

## Problem Statement & Core Hypothesis

Global crude oil shocks do not hit Thailand's downstream logistics, agricultural inputs, and household CPI instantaneously. Structural shipping, refinery, and price-stabilization mechanisms create a measurable **transmission lag** between global benchmarks (**EIA Brent/WTI**) and domestic ex-refinery/retail diesel prices (**DOEB / EPPO**).

Identifying this **10-day shockwave lag window** enables policymakers and industrial fleet operators to execute a staged **Lead-Time Protocol** rather than costly blanket subsidies:

| Protocol Window | Operational & Fiscal Trigger | Economic Objective |
| :--- | :--- | :--- |
| **T-Minus 1–3 Days** | Dynamic Oil Fund buffer + temporary Excise Tax shock absorber | Suppress retail panic buying and smooth daily price volatility |
| **T-Minus 7–14 Days** | Strategic reserve release (`DOEB`) + **Bio-Fuel surge (`E20` / `B10` UCO)** | Offset imported crude volume using domestic cassava, sugarcane & used cooking oil |
| **Targeted vs. Blanket** | Reallocate subsidy strictly to **SME freight & agricultural supply chains** | Prevent SME freight margin squeeze and fertilizer cost pass-through while cutting fiscal leakage |

## Repository Structure

```text
petropulse-oil-shock-bcp-simulator/
├── LICENSE                         # MIT License
├── README.md                       # Econometric methodology & Lead-Time Protocol
├── Thinktanker_A-.pdf              # Original OIL SHOCK Hack! 2026 Track A slide deck
├── index.html                      # Interactive Shockwave & Bio-BCP Web Simulator
├── styles.css                      # Dashboard & time-series chart styling
├── app.js                          # Client-side shockwave lag curve & subsidy engine
├── src/
│   ├── __init__.py
│   └── shockwave_model.py          # Cross-correlation lag detector, ARX Granger F-test & Bio-BCP model
└── tests/
    └── test_shockwave_model.py     # Unit tests for 10-day lag detection & fiscal leakage savings
```

## Statistical & Simulation Methodology

1. **First-Difference Cross-Correlation (`r`):** Computes Pearson correlation across candidate lags $k \in [0, 20]$ days between $\Delta \text{Crude}_{t-k}$ (`USD/bbl`) and $\Delta \text{Diesel}_{t}$ (`THB/L`) to isolate peak transmission delay.
2. **Predictive Granger F-Statistic:** Evaluates restricted autoregressive model $AR(p)$ against unrestricted $ARX(p)$ incorporating lagged global crude shocks via Ordinary Least Squares (`OLS`) residual sum of squares:
   $$F = \frac{(RSS_R - RSS_U) / p}{RSS_U / (T - 2p - 1)}$$
3. **Bio-BCP & Targeted Subsidy Accounting:** Quantifies crude import displacement from domestic **Ethanol (`E20`)** and **Biodiesel (`B10` / Used Cooking Oil)** blending alongside fiscal savings from targeted SME logistics/agriculture support versus universal price caps.

## Local Verification (Zero External Packages Required)

```bash
git clone https://github.com/benjarong-dev/petropulse-oil-shock-bcp-simulator.git
cd petropulse-oil-shock-bcp-simulator

# 1. Run unit tests (verifies 10-day lag recovery, Granger F-stat, and Bio-BCP math)
python3 -m unittest discover -s tests -v

# 2. Execute full shockwave lag analysis & policy comparison CLI report
python3 -m src.shockwave_model --crude-spike 115 --bio-blend-pct 18 --output-dir ./outputs
```

## License

Distributed under the MIT License. See `LICENSE` for details.
