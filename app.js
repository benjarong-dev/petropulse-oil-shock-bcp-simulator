const BASE_CRUDE = 74.0;
const BASE_DIESEL = 30.5;
const DAILY_DEMAND_ML = 98.0;
const TARGETED_SHARE = 0.42;
const CAP_THB = 32.0;
const LITERS_PER_BBL = 158.987;

let latestSeries = [];

function computeSimulation() {
  const crudePeak = Number(document.getElementById("crudeSlider").value);
  const lagDays = Number(document.getElementById("lagSlider").value);
  const bioBlend = Number(document.getElementById("bioSlider").value);
  const exciseBuf = Number(document.getElementById("exciseSlider").value);

  document.getElementById("crudeVal").textContent = `${crudePeak} USD/bbl`;
  document.getElementById("lagVal").textContent = `${lagDays} Days`;
  document.getElementById("bioVal").textContent = `${bioBlend}%`;
  document.getElementById("exciseVal").textContent = `${exciseBuf.toFixed(2)} THB/L`;

  const deltaCrude = Math.max(0, crudePeak - BASE_CRUDE);
  const unmitigatedPeak = BASE_DIESEL + deltaCrude * 0.22;
  const bioDamp = deltaCrude * 0.22 * (0.32 * (bioBlend / 20.0));
  const bcpPeak = Math.max(BASE_DIESEL, unmitigatedPeak - bioDamp - exciseBuf);

  const blanketBurn = DAILY_DEMAND_ML * Math.max(0, unmitigatedPeak - CAP_THB);
  const targetedBurn = (DAILY_DEMAND_ML * TARGETED_SHARE) * Math.max(0, bcpPeak - CAP_THB);
  const savings = blanketBurn - targetedBurn;
  const savingsPct = blanketBurn > 0 ? (savings / blanketBurn) * 100 : 0;
  const importOffsetKbd = ((DAILY_DEMAND_ML * (bioBlend / 100.0) * 1e6) / LITERS_PER_BBL) / 1000.0;

  document.getElementById("kpiLag").textContent = `${lagDays} Days`;
  document.getElementById("kpiRetailCompare").textContent =
    `${unmitigatedPeak.toFixed(2)} → ${bcpPeak.toFixed(2)} THB/L`;
  document.getElementById("kpiSavings").textContent = `${savings.toFixed(1)}M THB/d`;
  document.getElementById("kpiSavingsSub").textContent =
    `${savingsPct.toFixed(1)}% fiscal leakage reduction`;
  document.getElementById("kpiImportOffset").textContent = `${importOffsetKbd.toFixed(1)} kbd`;

  const maxBar = Math.max(1, blanketBurn);
  const bPct = ((blanketBurn / maxBar) * 100).toFixed(1);
  const tPct = ((targetedBurn / maxBar) * 100).toFixed(1);

  document.getElementById("subsidyBars").innerHTML = `
    <div class="bar-item">
      <div class="bar-label">
        <span>Blanket Mass Subsidy (All Sectors)</span>
        <strong>${blanketBurn.toFixed(1)}M THB / day</strong>
      </div>
      <div class="bar-bg"><div class="bar-fill red" style="width:${bPct}%"></div></div>
    </div>
    <div class="bar-item">
      <div class="bar-label">
        <span>PetroPulse Bio-BCP + Targeted SME/Agri</span>
        <strong>${targetedBurn.toFixed(1)}M THB / day</strong>
      </div>
      <div class="bar-bg"><div class="bar-fill green" style="width:${tPct}%"></div></div>
    </div>
  `;

  const fertSpike = Math.round(deltaCrude * 0.55);
  const fertBcp = Math.max(4, Math.round(fertSpike * 0.42));
  document.getElementById("sectorBody").innerHTML = `
    <tr>
      <td><strong>Agriculture &amp; Crop Inputs</strong></td>
      <td>Petrochemical fertilizer &amp; farm pump cost surge (+${fertSpike}%)</td>
      <td>High Oil Fund drain; fertilizer pass-through unaddressed</td>
      <td><strong>+${fertBcp}% capped impact</strong> + domestic cassava/cane E20 demand boost</td>
    </tr>
    <tr>
      <td><strong>SME Freight &amp; Cold-Chain</strong></td>
      <td>Diesel accounts for 35–45% of fleet operating margin</td>
      <td>Subsidizes private luxury fleets equally (fiscal leakage)</td>
      <td><strong>32.00 THB/L targeted fleet card cap</strong> preserves SME freight margin</td>
    </tr>
    <tr>
      <td><strong>Household CPI &amp; Underwriting</strong></td>
      <td>Food/transport CPI erodes disposable income &amp; insurance lapse risk</td>
      <td>Short-lived cap until Oil Fund borrowing limit saturates</td>
      <td><strong>${lagDays}-day early shock absorber</strong> prevents panic hoarding &amp; CPI spike</td>
    </tr>
  `;

  latestSeries = [];
  const upstreamPeakDay = 8;
  const downstreamPeakDay = upstreamPeakDay + lagDays;
  for (let d = 0; d <= 30; d++) {
    const crudePulse = deltaCrude * Math.exp(-Math.pow(d - upstreamPeakDay, 2) / 14.0);
    const downPulse = Math.exp(-Math.pow(d - downstreamPeakDay, 2) / 18.0);
    const crudeUsd = BASE_CRUDE + crudePulse;
    const rawDiesel = BASE_DIESEL + (unmitigatedPeak - BASE_DIESEL) * downPulse;
    const bcpDiesel = BASE_DIESEL + (bcpPeak - BASE_DIESEL) * downPulse;
    latestSeries.push({ day: d, crudeUsd, rawDiesel, bcpDiesel });
  }

  drawChart(upstreamPeakDay, downstreamPeakDay);
}

function drawChart(upDay, downDay) {
  const canvas = document.getElementById("shockwaveCanvas");
  const ctx = canvas.getContext("2d");
  const W = canvas.width;
  const H = canvas.height;
  ctx.clearRect(0, 0, W, H);

  const pad = { l: 48, r: 24, t: 26, b: 34 };
  const plotW = W - pad.l - pad.r;
  const plotH = H - pad.t - pad.b;

  const xOf = (day) => pad.l + (day / 30) * plotW;
  const yDiesel = (val) => pad.t + (1 - (val - 29.5) / 16.0) * plotH;
  const yCrude = (usd) => pad.t + (1 - (usd - 70.0) / 75.0) * plotH;

  ctx.fillStyle = "rgba(56, 189, 248, 0.09)";
  ctx.fillRect(xOf(upDay), pad.t, xOf(downDay) - xOf(upDay), plotH);

  ctx.strokeStyle = "#1e293b";
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const gy = pad.t + (i / 4) * plotH;
    ctx.beginPath();
    ctx.moveTo(pad.l, gy);
    ctx.lineTo(W - pad.r, gy);
    ctx.stroke();
  }

  const plotCurve = (vals, color, dashed = false) => {
    ctx.save();
    ctx.strokeStyle = color;
    ctx.lineWidth = 2.6;
    if (dashed) ctx.setLineDash([6, 4]);
    ctx.beginPath();
    vals.forEach((pt, idx) => {
      if (idx === 0) ctx.moveTo(pt.x, pt.y);
      else ctx.lineTo(pt.x, pt.y);
    });
    ctx.stroke();
    ctx.restore();
  };

  plotCurve(latestSeries.map((r) => ({ x: xOf(r.day), y: yCrude(r.crudeUsd) })), "#38bdf8");
  plotCurve(latestSeries.map((r) => ({ x: xOf(r.day), y: yDiesel(r.rawDiesel) })), "#f87171", true);
  plotCurve(latestSeries.map((r) => ({ x: xOf(r.day), y: yDiesel(r.bcpDiesel) })), "#34d399");

  ctx.fillStyle = "#93c5fd";
  ctx.font = "bold 11px sans-serif";
  ctx.fillText(`LAG GAP: ${downDay - upDay} DAYS`, xOf(upDay) + 6, pad.t + 16);

  ctx.fillStyle = "#94a3b8";
  ctx.font = "11px sans-serif";
  for (let d = 0; d <= 30; d += 5) {
    ctx.fillText(`D${d}`, xOf(d) - 8, H - 10);
  }
  ctx.fillText("THB/L", 8, pad.t + 10);
}

document.getElementById("exportScenarioBtn").addEventListener("click", () => {
  const header = "day,eia_crude_usd_bbl,unmitigated_diesel_thb_l,petropulse_bcp_diesel_thb_l\n";
  const rows = latestSeries
    .map((r) => `${r.day},${r.crudeUsd.toFixed(2)},${r.rawDiesel.toFixed(2)},${r.bcpDiesel.toFixed(2)}`)
    .join("\n");
  const blob = new Blob([header + rows], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "petropulse_shockwave_scenario.csv";
  a.click();
  URL.revokeObjectURL(url);
});

["crudeSlider", "lagSlider", "bioSlider", "exciseSlider"].forEach((id) => {
  document.getElementById(id).addEventListener("input", computeSimulation);
});

computeSimulation();
