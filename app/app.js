"use strict";

const state = { data: null, period: "", deal: "", sort: "total_contribution_bps", records: null, recordStatus: "all", recordOffset: 0, recordLimit: 25, recordRequestId: 0, recordTrigger: null };
const $ = (id) => document.getElementById(id);
const num = (value) => (value === null || value === undefined ? null : Number(value));
const esc = (value) => String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
const month = (period) => new Intl.DateTimeFormat("en-US", { month: "short", year: "numeric", timeZone: "UTC" }).format(new Date(`${period.slice(0, 4)}-${period.slice(4)}-01T00:00:00Z`));
const money = (value) => value === null || value === undefined ? "Unavailable" : new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", notation: "compact", maximumFractionDigits: 2 }).format(num(value));
const count = (value) => value === null || value === undefined ? "Unavailable" : new Intl.NumberFormat("en-US").format(num(value));
const pct = (value, digits = 2) => value === null || value === undefined ? "Unavailable" : `${(num(value) * 100).toFixed(digits)}%`;
const bp = (value, digits = 2) => value === null || value === undefined ? "Unavailable" : `${num(value) > 0 ? "+" : ""}${num(value).toFixed(digits)} bp`;
const signed = (value) => num(value) > 0 ? "positive" : num(value) < 0 ? "negative" : "";
const SORTS = {
  total_contribution_bps: { label: "Portfolio contribution", format: bp, metric: "d60_total_contribution_bps" },
  d60_change_1m_bps: { label: "Deal monthly change", format: bp, metric: "d60_change_bps" },
  d60_plus_rate: { label: "D60+ level", format: (value) => pct(value, 3), metric: "d60_plus_rate" },
  current_to_d30_rate_upb: { label: "Current to D30", format: pct, metric: "current_to_d30_roll_rate" },
  d30_to_d60_rate_upb: { label: "D30 to D60", format: pct, metric: "d30_to_d60_roll_rate" },
};

function announce(message) {
  $("announcement").textContent = "";
  window.setTimeout(() => { $("announcement").textContent = message; }, 20);
}

function currentRows() {
  return state.data.deal_periods.filter((row) => row.reporting_period === state.period);
}

function sortedRows() {
  return currentRows().sort((a, b) => (num(b[state.sort]) ?? -Infinity) - (num(a[state.sort]) ?? -Infinity) || a.deal_id.localeCompare(b.deal_id));
}

function syncUrl() {
  const url = new URL(window.location.href);
  url.searchParams.set("period", state.period);
  url.searchParams.set("deal", state.deal);
  url.searchParams.set("sort", state.sort);
  window.history.replaceState({}, "", url);
}

function populateDeals(preferred = state.deal) {
  const rows = sortedRows();
  $("deal-filter").innerHTML = rows.map((row) => `<option value="${esc(row.deal_id)}">${esc(row.deal_id)}</option>`).join("");
  state.deal = rows.some((row) => row.deal_id === preferred) ? preferred : rows[0]?.deal_id || "";
  $("deal-filter").value = state.deal;
}

function summary(label, value, detail = "") {
  return `<div class="summary"><span>${esc(label)}</span><strong>${esc(value)}</strong>${detail ? `<span>${esc(detail)}</span>` : ""}</div>`;
}

function renderPulse(rows, portfolio) {
  const contributor = [...rows].filter((row) => num(row.total_contribution_bps) !== null).sort((a, b) => num(b.total_contribution_bps) - num(a.total_contribution_bps))[0];
  $("docket-month").textContent = `${month(state.period)} review`;
  $("docket-file").textContent = `SURV / ${state.period.slice(0, 4)}-${state.period.slice(4)}`;
  $("folio-period").textContent = `${state.period.slice(2, 4)} / ${state.period.slice(4)}`;
  $("pulse-period").textContent = `As of ${month(state.period)}`;
  $("pulse-context").textContent = `${count(portfolio.eligible_active_loans)} eligible active loans across ${rows.length} reported deals.`;
  $("pulse-upb").textContent = money(portfolio.eligible_current_upb);
  $("pulse-population").textContent = `${count(portfolio.eligible_active_loans)} active loans; ${money(portfolio.excluded_ra_upb)} REO UPB excluded`;
  $("pulse-d60").textContent = pct(portfolio.d60_plus_rate, 3);
  $("pulse-change").textContent = bp(portfolio.d60_change_1m_bps);
  $("pulse-change").className = signed(portfolio.d60_change_1m_bps);
  $("pulse-three-month").textContent = `${bp(portfolio.d60_change_3m_bps)} over three reporting months`;
  $("pulse-driver").textContent = contributor?.deal_id || "No prior comparison";
  $("pulse-driver-detail").textContent = contributor ? `${bp(contributor.total_contribution_bps)} contribution; ${bp(contributor.rate_effect_bps)} rate effect` : "The first observed month has no attribution baseline";
}

function evidenceLabel(row) {
  if (row.loan_match_rate === null || row.loan_match_rate === undefined) return "No prior comparison";
  return num(row.loan_match_rate) === 1 ? "100% prior-loan match" : `${pct(row.loan_match_rate)} prior-loan match`;
}

function renderWatchlist(rows) {
  const config = SORTS[state.sort];
  $("selected-measure-heading").textContent = config.label;
  $("watchlist-context").textContent = `${rows.length} deals ranked by ${config.label.toLowerCase()}, highest first.`;
  $("watchlist-body").innerHTML = rows.map((row, index) => { const selected = row.deal_id === state.deal; return `<tr data-deal="${esc(row.deal_id)}" aria-selected="${selected}"><td>${index + 1}</td><td class="deal-name"><button type="button" class="deal-select" aria-pressed="${selected}" data-deal="${esc(row.deal_id)}"><span>${esc(row.deal_id)}</span><small>${selected ? "Current" : "Open"}</small></button></td><td class="num">${pct(row.d60_plus_rate, 3)}</td><td class="num ${signed(row.d60_change_1m_bps)}">${bp(row.d60_change_1m_bps)}</td><td class="num">${money(row.d60_plus_upb)}</td><td class="num ${signed(row[state.sort])}">${config.format(row[state.sort])}</td><td class="num ${signed(row.rate_effect_bps)}">${bp(row.rate_effect_bps)}</td><td class="num ${signed(row.mix_effect_bps)}">${bp(row.mix_effect_bps)}</td><td class="evidence-pass">${evidenceLabel(row)}</td></tr>`; }).join("");
  $("watchlist-body").querySelectorAll("tr").forEach((row) => {
    const select = () => { state.deal = row.dataset.deal; state.recordOffset = 0; $("deal-filter").value = state.deal; syncUrl(); render(); loadRecords(); announce(`${state.deal} selected for investigation.`); };
    row.querySelector(".deal-select").addEventListener("click", select);
  });
}

function recordValue(value) {
  return value === null || value === undefined || value === "" ? "Unavailable" : String(value);
}

function recordStatus(row) {
  const raw = row.current_loan_delinquency_status;
  if (raw === "00") return "Current";
  if (raw === "01") return "D30";
  if (raw === "02") return "D60";
  if (raw === "RA") return "REO";
  if (/^[0-9]{2}$/.test(raw) && Number(raw) >= 3) return "D90+";
  return raw || (row.zero_balance_code ? `Zero balance ${row.zero_balance_code}` : "Unavailable");
}

function openRecord(index) {
  const row = state.records?.rows[index];
  if (!row) return;
  $("record-detail-title").textContent = `${row.loan_identifier} / ${state.deal} / ${state.period}`;
  $("record-fields").innerHTML = state.records.fields.map((field) => `<div class="${state.records.masked_fields.includes(field) ? "masked-field" : ""}"><dt>${esc(field.replaceAll("_", " "))}</dt><dd>${esc(recordValue(row[field]))}</dd></div>`).join("");
  $("record-detail").classList.remove("hidden");
  $("record-detail-title").focus();
  $("record-detail").scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });
  announce(`All disclosure fields opened for ${row.loan_identifier}.`);
}

function renderRecords() {
  const result = state.records;
  const start = result.total ? result.offset + 1 : 0;
  const end = Math.min(result.offset + result.rows.length, result.total);
  $("records-context").textContent = `${state.deal} at ${month(state.period)}; ${count(result.total)} records match the selected status.`;
  $("records-release").textContent = `${result.fields.length} stored columns / ${result.release}`;
  $("record-page-status").textContent = `${count(start)}-${count(end)} of ${count(result.total)}`;
  $("record-prev").disabled = result.offset === 0;
  $("record-next").disabled = result.offset + result.limit >= result.total;
  $("record-body").innerHTML = result.rows.length ? result.rows.map((row, index) => `<tr><td class="masked-key">${esc(recordValue(row.loan_identifier))}</td><td>${esc(recordValue(row.reference_pool_number))}</td><td>${esc(recordStatus(row))}</td><td class="num">${esc(row.current_actual_upb ? money(row.current_actual_upb) : "Unavailable")}</td><td class="num">${esc(recordValue(row.current_interest_rate))}</td><td class="num">${esc(recordValue(row.classic_fico))}</td><td class="num">${esc(recordValue(row.original_ltv))}</td><td class="num">${esc(recordValue(row.original_dti))}</td><td>${esc(recordValue(row.loan_purpose))}</td><td>${esc(recordValue(row.occupancy_status))}</td><td>${esc(recordValue(row.modification_flag))}</td><td><button type="button" class="record-open" data-index="${index}">Review ${result.fields.length}</button></td></tr>`).join("") : '<tr><td colspan="12">No full records match this status.</td></tr>';
  $("record-body").querySelectorAll(".record-open").forEach((button) => button.addEventListener("click", () => { state.recordTrigger = button; openRecord(Number(button.dataset.index)); }));
}

async function loadRecords() {
  const requestId = ++state.recordRequestId;
  $("records-loading").classList.remove("hidden");
  $("records-error").classList.add("hidden");
  $("record-detail").classList.add("hidden");
  try {
    const query = new URLSearchParams({ period: state.period, deal: state.deal, status: state.recordStatus, limit: state.recordLimit, offset: state.recordOffset });
    const response = await fetch(`/api/records?${query}`, { headers: { Accept: "application/json" } });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "The full-data query failed.");
    if (result.classification !== "public-full-record-masked" || !Array.isArray(result.masked_fields) || !result.masked_fields.includes("loan_identifier") || !result.masked_fields.includes("postal_code_3_digit")) throw new Error("The record response did not pass the masking boundary.");
    if (requestId !== state.recordRequestId) return;
    state.records = result;
    renderRecords();
    announce(`${count(result.rows.length)} full records loaded for ${state.deal}.`);
  } catch (error) {
    if (requestId !== state.recordRequestId) return;
    state.records = null;
    $("record-body").innerHTML = '<tr><td colspan="12">Full records are temporarily unavailable.</td></tr>';
    $("record-page-status").textContent = "Records unavailable";
    $("records-error").textContent = `${error.message} Retry this deal and month.`;
    $("records-error").classList.remove("hidden");
  } finally {
    if (requestId === state.recordRequestId) $("records-loading").classList.add("hidden");
  }
}

function renderChart(selected) {
  const portfolioByPeriod = new Map(state.data.portfolio_periods.map((row) => [row.reporting_period, row]));
  const points = state.data.deal_periods.filter((row) => row.deal_id === state.deal && row.reporting_period <= state.period).slice(-18).map((row) => ({ period: row.reporting_period, deal: num(row.d60_plus_rate), portfolio: num(portfolioByPeriod.get(row.reporting_period)?.d60_plus_rate) })).filter((row) => row.portfolio !== null);
  const svg = $("trend-chart");
  const title = `<title id="chart-title">${esc(state.deal)} and portfolio D60+ history through ${esc(month(state.period))}</title><desc id="chart-desc">Two keyed series compare the selected deal with the portfolio for common reporting months.</desc>`;
  if (!points.length) { svg.innerHTML = `${title}<text x="30" y="50" class="chart-axis">No comparable history is available.</text>`; return; }
  const mobile = window.matchMedia("(max-width: 700px)").matches;
  const width = mobile ? 360 : 920, height = mobile ? 220 : 290, left = mobile ? 44 : 58, right = mobile ? 12 : 20, top = 20, bottom = mobile ? 34 : 42;
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  const values = points.flatMap((point) => [point.deal, point.portfolio]);
  const min = Math.max(0, Math.min(...values) * .82), max = Math.max(...values) * 1.12 || .01;
  const x = (index) => left + index * (width - left - right) / Math.max(points.length - 1, 1);
  const y = (value) => top + (max - value) / Math.max(max - min, .0001) * (height - top - bottom);
  const path = (key) => points.map((point, index) => `${index ? "L" : "M"} ${x(index).toFixed(1)} ${y(point[key]).toFixed(1)}`).join(" ");
  const grid = [0, .5, 1].map((step) => { const value = min + (max - min) * step, py = y(value); return `<line x1="${left}" y1="${py}" x2="${width - right}" y2="${py}" class="chart-grid"/><text x="4" y="${py + 4}" class="chart-axis">${pct(value, 2)}</text>`; }).join("");
  const labelStep = mobile ? Math.ceil(points.length / 4) : 3;
  const labels = points.map((point, index) => index % labelStep === 0 || index === points.length - 1 ? `<text x="${x(index)}" y="${height - 11}" text-anchor="middle" class="chart-axis">${esc(month(point.period))}</text>` : "").join("");
  svg.innerHTML = `${title}${grid}<path d="${path("deal")}" class="chart-line-deal"/><path d="${path("portfolio")}" class="chart-line-portfolio"/>${labels}`;
  $("trend-table").innerHTML = points.map((point) => `<tr><td>${month(point.period)}</td><td class="num">${pct(point.deal, 3)}</td><td class="num">${pct(point.portfolio, 3)}</td><td class="num ${signed((point.deal - point.portfolio) * 10000)}">${bp((point.deal - point.portfolio) * 10000)}</td></tr>`).join("");
  $("legend-deal").textContent = selected.deal_id;
}

function renderComparison(selected, portfolio) {
  const difference = (num(selected.d60_plus_rate) - num(portfolio.d60_plus_rate)) * 10000;
  $("comparison-context").textContent = `${selected.deal_id} versus the eligible-UPB-weighted portfolio at ${month(state.period)}.`;
  $("comparison-summary").innerHTML = [summary("Selected D60+", pct(selected.d60_plus_rate, 3), money(selected.d60_plus_upb)), summary("Portfolio D60+", pct(portfolio.d60_plus_rate, 3), money(portfolio.d60_plus_upb)), summary("Selected vs portfolio", bp(difference), "Level difference"), summary("Selected 3M change", bp(selected.d60_change_3m_bps), "Persistence check")].join("");
  renderChart(selected);
}

function renderDrivers(rows, portfolio) {
  const comparable = rows.filter((row) => row.total_contribution_bps !== null);
  const rate = comparable.reduce((total, row) => total + num(row.rate_effect_bps), 0), mix = comparable.reduce((total, row) => total + num(row.mix_effect_bps), 0), exact = comparable.reduce((total, row) => total + num(row.total_contribution_bps), 0);
  $("driver-summary").innerHTML = [summary("Rate effect", bp(rate, 3), "Within-deal performance"), summary("Mix effect", bp(mix, 3), "Portfolio composition"), summary("Exact total", bp(exact, 3), "Portfolio D60+ change")].join("");
  $("identity-state").textContent = comparable.length ? `Identity variance ${Math.abs(exact - num(portfolio.d60_change_1m_bps)).toExponential(2)} bp` : "No prior comparison";
  $("driver-body").innerHTML = comparable.length ? [...comparable].sort((a, b) => Math.abs(num(b.total_contribution_bps)) - Math.abs(num(a.total_contribution_bps))).map((row) => { const value = num(row.total_contribution_bps); return `<tr><td class="deal-name">${esc(row.deal_id)}</td><td class="num ${signed(row.rate_effect_bps)}">${bp(row.rate_effect_bps, 3)}</td><td class="num ${signed(row.mix_effect_bps)}">${bp(row.mix_effect_bps, 3)}</td><td class="num ${signed(value)}">${bp(value, 3)}</td><td>${value > 0 ? "Added to deterioration" : value < 0 ? "Offset deterioration" : "No net contribution"}</td></tr>`; }).join("") : '<tr><td colspan="5">The first observed month has no attribution baseline.</td></tr>';
}

function flow(label, rate, denominator) { return `<div class="flow"><span>${esc(label)}</span><strong>${pct(rate, 2)}</strong><small>${esc(denominator)}</small></div>`; }
function renderFlows(selected) {
  $("flow-context").textContent = `${selected.deal_id} at ${month(state.period)}; UPB-weighted adjacent-period transitions.`;
  $("flow-match").textContent = evidenceLabel(selected);
  $("flow-grid").innerHTML = [flow("Current to D30", selected.current_to_d30_rate_upb, "Prior-current UPB"), flow("D30 to D60", selected.d30_to_d60_rate_upb, "Prior-D30 UPB"), flow("Cure", selected.cure_rate_upb, "Prior-D30+ UPB"), flow("Voluntary payoff", selected.voluntary_payoff_rate_upb, "Beginning UPB")].join("");
  const pools = state.data.pool_periods.filter((row) => row.reporting_period === state.period && row.deal_id === state.deal);
  $("pool-body").innerHTML = pools.length ? pools.map((row) => `<tr><td>${esc(row.reference_pool_number)}</td><td class="num">${money(row.eligible_current_upb)}</td><td class="num">${pct(row.d60_plus_rate, 3)}</td><td class="num ${signed(row.d60_change_1m_bps)}">${bp(row.d60_change_1m_bps)}</td></tr>`).join("") : '<tr><td colspan="4">No reference-pool aggregates are available.</td></tr>';
}

function renderEvidence() {
  const metricId = SORTS[state.sort].metric;
  const metric = state.data.metric_catalog.find((row) => row.metric_id === metricId) || state.data.metric_catalog.find((row) => row.metric_id === "d60_plus_rate");
  $("metric-definition").innerHTML = metric ? `<div><dt>Definition</dt><dd>${esc(metric.definition)}</dd></div><div><dt>Method</dt><dd>${esc(metric.method)}</dd></div><div><dt>Decision</dt><dd>${esc(metric.supported_decision)}</dd></div><div><dt>Limitation</dt><dd>${esc(metric.limitation)}</dd></div>` : "";
  $("control-list").innerHTML = Object.entries(state.data.controls).filter(([key]) => key !== "maximum_decomposition_variance_bps").map(([key, value]) => `<li><strong>${esc(key.replaceAll("_", " "))}</strong><br>${esc(value)}</li>`).join("");
}

function render() {
  const rows = sortedRows();
  const portfolio = state.data.portfolio_periods.find((row) => row.reporting_period === state.period);
  if (!rows.length || !portfolio) { $("workspace").classList.add("hidden"); $("empty").classList.remove("hidden"); return; }
  $("empty").classList.add("hidden");
  if (!rows.some((row) => row.deal_id === state.deal)) populateDeals();
  const selected = rows.find((row) => row.deal_id === state.deal);
  renderPulse(rows, portfolio); renderWatchlist(rows); renderComparison(selected, portfolio); renderDrivers(rows, portfolio); renderFlows(selected); renderEvidence();
  $("workspace").classList.remove("hidden"); syncUrl();
}

function bindEvents() {
  $("period-filter").addEventListener("change", () => { state.period = $("period-filter").value; state.recordOffset = 0; populateDeals(""); render(); loadRecords(); announce(`Dashboard updated for ${month(state.period)}.`); });
  $("deal-filter").addEventListener("change", () => { state.deal = $("deal-filter").value; state.recordOffset = 0; render(); loadRecords(); announce(`${state.deal} selected for investigation.`); });
  $("sort-filter").addEventListener("change", () => { state.sort = $("sort-filter").value; populateDeals(state.deal); render(); announce(`Deals ranked by ${SORTS[state.sort].label.toLowerCase()}.`); });
  $("record-status").addEventListener("change", () => { state.recordStatus = $("record-status").value; state.recordOffset = 0; loadRecords(); });
  $("record-prev").addEventListener("click", () => { state.recordOffset = Math.max(0, state.recordOffset - state.recordLimit); loadRecords(); });
  $("record-next").addEventListener("click", () => { state.recordOffset += state.recordLimit; loadRecords(); });
  $("record-detail-close").addEventListener("click", () => { $("record-detail").classList.add("hidden"); state.recordTrigger?.focus(); });
}

async function initialize() {
  try {
    const response = await fetch("data/public/crt_public_projection.json", { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error("The reviewed projection is missing.");
    state.data = await response.json();
    if (!state.data.public_release_allowed || state.data.classification !== "approved-aggregate-projection") throw new Error("The projection did not pass the public boundary gate.");
    const url = new URL(window.location.href), periods = state.data.portfolio_periods.map((row) => row.reporting_period).sort().reverse();
    state.period = periods.includes(url.searchParams.get("period")) ? url.searchParams.get("period") : state.data.source_scope.latest_period;
    state.sort = SORTS[url.searchParams.get("sort")] ? url.searchParams.get("sort") : "total_contribution_bps";
    state.deal = url.searchParams.get("deal") || "";
    $("period-filter").innerHTML = periods.map((period) => `<option value="${period}">${month(period)}</option>`).join("");
    $("period-filter").value = state.period; $("sort-filter").value = state.sort; populateDeals(state.deal); bindEvents(); render();
    $("source-scope").textContent = `${count(state.data.source_scope.records)} full loan-period records; ${count(state.data.source_scope.deal_period_groups)} partitions`;
    $("metric-version").textContent = `Metric ${state.data.metric_version}; full-record query plus derived summaries`;
    $("loading").classList.add("hidden");
    await loadRecords();
  } catch (error) {
    $("loading").classList.add("hidden"); $("error-message").textContent = `${error.message} Rebuild the release, then reload.`; $("error").classList.remove("hidden");
  }
}

initialize();
