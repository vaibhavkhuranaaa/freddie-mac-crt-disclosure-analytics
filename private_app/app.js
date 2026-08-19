"use strict";

const state = {
  bootstrap: null,
  overview: null,
  deal: null,
  loans: null,
  loanOffset: 0,
  loanLimit: 50,
  requestedDeal: "",
  initialized: false,
};

const $ = (id) => document.getElementById(id);
const number = (value) => (value === null || value === undefined ? null : Number(value));
const escapeHtml = (value) =>
  String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
const compactMoney = (value) =>
  value === null || value === undefined
    ? "Unavailable"
    : new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        notation: "compact",
        maximumFractionDigits: 2,
      }).format(number(value));
const money = (value) =>
  value === null || value === undefined
    ? "Unavailable"
    : new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        maximumFractionDigits: 0,
      }).format(number(value));
const count = (value) =>
  value === null || value === undefined
    ? "Unavailable"
    : new Intl.NumberFormat("en-US").format(number(value));
const percent = (value, digits = 2) =>
  value === null || value === undefined
    ? "Unavailable"
    : `${(number(value) * 100).toFixed(digits)}%`;
const basisPoints = (value, digits = 2) => {
  if (value === null || value === undefined) return "Unavailable";
  const amount = number(value);
  return `${amount > 0 ? "+" : ""}${amount.toFixed(digits)} bp`;
};
const signedClass = (value) => (number(value) > 0 ? "positive" : number(value) < 0 ? "negative" : "");
const queryString = (parameters) => new URLSearchParams(parameters).toString();
const periodLabel = (period) =>
  new Intl.DateTimeFormat("en-US", { month: "short", year: "numeric", timeZone: "UTC" }).format(
    new Date(`${period.slice(0, 4)}-${period.slice(4)}-01T00:00:00Z`),
  );
const SORTS = {
  total_contribution_bps: { label: "Portfolio contribution", format: basisPoints, metric: "d60_total_contribution_bps" },
  d60_change_1m_bps: { label: "Deal monthly change", format: basisPoints, metric: "d60_change_bps" },
  d60_plus_rate: { label: "D60+ level", format: (value) => percent(value, 3), metric: "d60_plus_rate" },
  current_to_d30_rate_upb: { label: "Current to D30", format: percent, metric: "current_to_d30_roll_rate" },
  d30_to_d60_rate_upb: { label: "D30 to D60", format: percent, metric: "d30_to_d60_roll_rate" },
};
const LOAN_PURPOSE = {
  P: "Purchase",
  C: "Cash-out refinance",
  N: "No-cash-out refinance",
  R: "Refinance, unspecified",
  9: "Unavailable",
};
const OCCUPANCY = {
  P: "Primary residence",
  S: "Second home",
  I: "Investment property",
  O: "Owner occupied",
  9: "Unavailable",
};
const MODIFICATION = { Y: "Current-period modification", P: "Prior-period modification" };
const ASSISTANCE = { F: "Forbearance", R: "Repayment plan", T: "Trial plan" };
const DEFERRAL = { C: "Current-period deferral", P: "Prior-period deferral" };

async function api(path, parameters = {}) {
  const suffix = Object.keys(parameters).length ? `?${queryString(parameters)}` : "";
  const response = await fetch(`${path}${suffix}`, { headers: { Accept: "application/json" } });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.error || "The local analytical query failed.");
  return payload;
}

function setAnnouncement(message) {
  $("announcement").textContent = "";
  window.setTimeout(() => {
    $("announcement").textContent = message;
  }, 20);
}

function setBusy(busy) {
  ["period-filter", "deal-filter", "sort-filter", "export-evidence"].forEach((id) => {
    $(id).disabled = busy;
  });
}

function showError(error) {
  $("loading-state").classList.add("hidden");
  $("workspace").classList.add("hidden");
  $("error-message").textContent = `${error.message} Reset the affected filter or verify the restricted database.`;
  $("error-state").classList.remove("hidden");
  setBusy(false);
}

function clearError() {
  $("error-state").classList.add("hidden");
}

function currentFilters() {
  return {
    period: $("period-filter").value,
    deal: $("deal-filter").value,
    sort: $("sort-filter").value,
  };
}

function syncUrl() {
  const filters = currentFilters();
  const url = new URL(window.location.href);
  url.searchParams.set("period", filters.period);
  url.searchParams.set("deal", filters.deal);
  url.searchParams.set("sort", filters.sort);
  window.history.replaceState({}, "", url);
}

function populateControls() {
  const url = new URL(window.location.href);
  const requestedPeriod = url.searchParams.get("period");
  state.requestedDeal = url.searchParams.get("deal") || "";
  const requestedSort = url.searchParams.get("sort");
  $("period-filter").innerHTML = state.bootstrap.periods
    .map((period) => `<option value="${escapeHtml(period)}">${escapeHtml(periodLabel(period))}</option>`)
    .join("");
  if (state.bootstrap.periods.includes(requestedPeriod)) $("period-filter").value = requestedPeriod;
  if ([...$("sort-filter").options].some((option) => option.value === requestedSort)) {
    $("sort-filter").value = requestedSort;
  }
  $("metric-picker").innerHTML = state.bootstrap.metric_catalog
    .map(
      (metric) =>
        `<option value="${escapeHtml(metric.metric_id)}">${escapeHtml(metric.metric_id.replaceAll("_", " "))}</option>`,
    )
    .join("");
  $("metric-picker").value = SORTS[$("sort-filter").value].metric;
  renderMetricDefinition();
}

function populateDealControl(availableDeals, preferred = $("deal-filter").value || state.requestedDeal) {
  $("deal-filter").innerHTML = availableDeals
    .map((deal) => `<option value="${escapeHtml(deal)}">${escapeHtml(deal)}</option>`)
    .join("");
  $("deal-filter").value = availableDeals.includes(preferred) ? preferred : availableDeals[0];
  state.requestedDeal = "";
}

function renderMetricDefinition() {
  const metric = state.bootstrap.metric_catalog.find(
    (item) => item.metric_id === $("metric-picker").value,
  );
  if (!metric) return;
  $("metric-definition").innerHTML = `
    <div><dt>Definition</dt><dd>${escapeHtml(metric.definition)}</dd></div>
    <div><dt>Method</dt><dd>${escapeHtml(metric.method)}</dd></div>
    <div><dt>Decision</dt><dd>${escapeHtml(metric.supported_decision)}</dd></div>
    <div><dt>Desired direction</dt><dd>${escapeHtml(metric.desired_direction)}</dd></div>
    <div><dt>Verified baseline</dt><dd>${escapeHtml(metric.baseline)}</dd></div>
    <div><dt>Limitation</dt><dd>${escapeHtml(metric.limitation)}</dd></div>`;
}

function renderPulse() {
  const portfolio = state.overview.portfolio;
  const contributor = [...state.overview.decomposition]
    .filter((item) => item.total_contribution_bps !== null)
    .sort((a, b) => number(b.total_contribution_bps) - number(a.total_contribution_bps))[0];
  $("pulse-period").textContent = `As of ${periodLabel(portfolio.reporting_period)}`;
  $("pulse-summary").textContent = `${count(portfolio.eligible_active_loans)} eligible active loans across ${state.overview.watchlist.length} deals.`;
  $("pulse-upb").textContent = compactMoney(portfolio.eligible_current_upb);
  $("pulse-population").textContent = `${count(portfolio.eligible_active_loans)} active loans; ${compactMoney(portfolio.excluded_ra_upb)} REO UPB excluded`;
  $("pulse-d60").textContent = percent(portfolio.d60_plus_rate, 3);
  $("pulse-change").textContent = basisPoints(portfolio.d60_change_1m_bps, 2);
  $("pulse-change").className = signedClass(portfolio.d60_change_1m_bps);
  $("pulse-change-context").textContent = `${basisPoints(portfolio.d60_change_3m_bps, 2)} over three reporting periods`;
  $("pulse-driver").textContent = contributor ? contributor.deal_id : "No prior comparison";
  $("pulse-driver-detail").textContent = contributor
    ? `${basisPoints(contributor.total_contribution_bps, 2)} total contribution; ${basisPoints(contributor.rate_effect_bps, 2)} rate effect`
    : "The first observed month has no attribution baseline";
  $("evidence-population").textContent = `${compactMoney(portfolio.eligible_current_upb)} across ${count(portfolio.eligible_active_loans)} active loans`;
  $("evidence-reo").textContent = `${compactMoney(portfolio.excluded_ra_upb)} across ${count(portfolio.excluded_ra_records)} rows`;
  $("evidence-unknown").textContent = `${compactMoney(portfolio.excluded_xx_upb)} across ${count(portfolio.excluded_xx_records)} rows`;
}

function renderWatchlist() {
  const selectedDeal = $("deal-filter").value;
  const config = SORTS[$("sort-filter").value];
  $("selected-measure-heading").textContent = config.label;
  $("watchlist-context").textContent = `${state.overview.watchlist.length} deals ranked by ${config.label.toLowerCase()}, highest first.`;
  $("watchlist-body").innerHTML = state.overview.watchlist
    .map((item, index) => {
      const selected = item.deal_id === selectedDeal;
      const evidence = item.loan_match_rate === null || item.loan_match_rate === undefined
        ? "No prior comparison"
        : number(item.loan_match_rate) === 1
          ? "100% prior-loan match"
          : `${percent(item.loan_match_rate, 2)} prior-loan match`;
      return `<tr tabindex="0" data-deal="${escapeHtml(item.deal_id)}" aria-selected="${selected}">
        <td class="rank">${index + 1}</td>
        <td class="deal-name">${escapeHtml(item.deal_id)}</td>
        <td class="num">${percent(item.d60_plus_rate, 3)}</td>
        <td class="num ${signedClass(item.d60_change_1m_bps)}">${basisPoints(item.d60_change_1m_bps, 2)}</td>
        <td class="num">${compactMoney(item.d60_plus_upb)}</td>
        <td class="num ${signedClass(item[$("sort-filter").value])}">${config.format(item[$("sort-filter").value])}</td>
        <td class="num ${signedClass(item.rate_effect_bps)}">${basisPoints(item.rate_effect_bps, 2)}</td>
        <td class="num ${signedClass(item.mix_effect_bps)}">${basisPoints(item.mix_effect_bps, 2)}</td>
        <td class="evidence-pass">${evidence}</td>
      </tr>`;
    })
    .join("");
  $("watchlist-body").querySelectorAll("tr").forEach((row) => {
    const select = async () => {
      if ($("deal-filter").value === row.dataset.deal) return;
      $("deal-filter").value = row.dataset.deal;
      state.loanOffset = 0;
      syncUrl();
      await loadDeal();
      renderWatchlist();
      setAnnouncement(`${row.dataset.deal} selected for investigation.`);
    };
    row.addEventListener("click", select);
    row.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        select();
      }
    });
  });
}

function summaryMeasure(label, value, detail = "") {
  return `<div class="summary-measure"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong>${detail ? `<span>${escapeHtml(detail)}</span>` : ""}</div>`;
}

function renderComparison() {
  const current = state.deal.current;
  const portfolio = state.overview.portfolio;
  $("compare-context").textContent = `${current.deal_id} versus the eligible-UPB-weighted portfolio at ${periodLabel(current.reporting_period)}.`;
  $("legend-deal").textContent = current.deal_id;
  const difference = (number(current.d60_plus_rate) - number(portfolio.d60_plus_rate)) * 10000;
  $("compare-summary").innerHTML = [
    summaryMeasure("Selected D60+", percent(current.d60_plus_rate, 3), compactMoney(current.d60_plus_upb)),
    summaryMeasure("Portfolio D60+", percent(portfolio.d60_plus_rate, 3), compactMoney(portfolio.d60_plus_upb)),
    summaryMeasure("Selected versus portfolio", basisPoints(difference, 2), "Level difference"),
    summaryMeasure("Selected three-period change", basisPoints(current.d60_change_3m_bps, 2), "Persistence check"),
  ].join("");
  renderTrendChart();
}

function renderTrendChart() {
  const selectedRows = state.deal.series.slice(-18);
  const portfolioByPeriod = new Map(state.deal.portfolio_series.map((item) => [item.reporting_period, item]));
  const points = selectedRows
    .map((item) => ({
      period: item.reporting_period,
      deal: number(item.d60_plus_rate),
      portfolio: number(portfolioByPeriod.get(item.reporting_period)?.d60_plus_rate),
    }))
    .filter((item) => item.portfolio !== null);
  const svg = $("trend-chart");
  if (!points.length) {
    svg.innerHTML = `<title id="trend-chart-title">${escapeHtml(state.deal.deal_id)} and portfolio D60+ history</title><desc id="trend-chart-desc">No comparable history is available for this selection.</desc><text x="30" y="50" class="chart-axis">No comparable history is available for this selection.</text>`;
    $("trend-table-body").innerHTML = '<tr><td colspan="4">No comparable history is available.</td></tr>';
    return;
  }
  const width = 960;
  const height = 300;
  const left = 58;
  const right = 20;
  const top = 20;
  const bottom = 44;
  const values = points.flatMap((item) => [item.deal, item.portfolio]);
  const min = Math.max(0, Math.min(...values) * 0.82);
  const max = Math.max(...values) * 1.12 || 0.01;
  const x = (index) => left + (index * (width - left - right)) / Math.max(points.length - 1, 1);
  const y = (value) => top + ((max - value) / Math.max(max - min, 0.0001)) * (height - top - bottom);
  const path = (key) => points.map((item, index) => `${index ? "L" : "M"} ${x(index).toFixed(1)} ${y(item[key]).toFixed(1)}`).join(" ");
  const grid = [0, 0.5, 1]
    .map((step) => {
      const value = min + (max - min) * step;
      const py = y(value);
      return `<line x1="${left}" y1="${py}" x2="${width - right}" y2="${py}" class="chart-grid"/><text x="4" y="${py + 4}" class="chart-axis">${percent(value, 2)}</text>`;
    })
    .join("");
  const labels = points
    .map((item, index) => (index % 3 === 0 || index === points.length - 1 ? `<text x="${x(index)}" y="${height - 12}" text-anchor="middle" class="chart-axis">${item.period}</text>` : ""))
    .join("");
  const selectedPoints = points.map((item, index) => `<circle cx="${x(index)}" cy="${y(item.deal)}" r="3.2" class="chart-point-selected"><title>${item.period}: ${percent(item.deal, 3)}</title></circle>`).join("");
  const portfolioPoints = points.map((item, index) => `<circle cx="${x(index)}" cy="${y(item.portfolio)}" r="2.8" class="chart-point-portfolio"><title>${item.period}: ${percent(item.portfolio, 3)}</title></circle>`).join("");
  svg.innerHTML = `<title id="trend-chart-title">${escapeHtml(state.deal.deal_id)} and portfolio D60+ history through ${escapeHtml(periodLabel(state.deal.period))}</title><desc id="trend-chart-desc">Two keyed time series compare the selected deal with the eligible-UPB-weighted portfolio for common reporting months.</desc>${grid}<path d="${path("deal")}" class="chart-line-selected"/><path d="${path("portfolio")}" class="chart-line-portfolio"/>${selectedPoints}${portfolioPoints}${labels}`;
  $("trend-table-body").innerHTML = points
    .map((item) => `<tr><td>${item.period}</td><td class="num">${percent(item.deal, 3)}</td><td class="num">${percent(item.portfolio, 3)}</td><td class="num ${signedClass((item.deal - item.portfolio) * 10000)}">${basisPoints((item.deal - item.portfolio) * 10000, 2)}</td></tr>`)
    .join("");
}

function renderDrivers() {
  const totals = state.overview.decomposition_totals;
  $("driver-total").innerHTML = [
    summaryMeasure("Rate effect", basisPoints(totals.rate_effect_bps, 3), "Within-deal performance"),
    summaryMeasure("Mix effect", basisPoints(totals.mix_effect_bps, 3), "Portfolio composition"),
    summaryMeasure("Exact total", basisPoints(totals.total_contribution_bps, 3), "Portfolio D60+ change"),
  ].join("");
  const variance = Math.abs(number(totals.total_contribution_bps) - number(state.overview.portfolio.d60_change_1m_bps));
  $("driver-identity").textContent = `Identity variance ${variance.toExponential(2)} bp`;
  const top = state.overview.decomposition.slice(0, 10);
  const maxAbs = Math.max(...top.map((item) => Math.abs(number(item.total_contribution_bps))), 0.01);
  $("driver-bars").innerHTML = top
    .map((item) => {
      const value = number(item.total_contribution_bps);
      const width = Math.min(49, (Math.abs(value) / maxAbs) * 49);
      const x = value >= 0 ? 50 : 50 - width;
      return `<div class="driver-row"><strong>${escapeHtml(item.deal_id)}</strong><svg class="driver-track" viewBox="0 0 100 10" preserveAspectRatio="none" aria-hidden="true"><line x1="50" y1="0" x2="50" y2="10" class="driver-zero"/><rect x="${x.toFixed(2)}" y="2" width="${width.toFixed(2)}" height="6" class="driver-fill ${value >= 0 ? "adverse" : "favorable"}"/></svg><span class="driver-value ${signedClass(value)}">${basisPoints(value, 2)}</span></div>`;
    })
    .join("");
  $("driver-table-body").innerHTML = top
    .map((item) => {
      const value = number(item.total_contribution_bps);
      const interpretation = value > 0 ? "Added to deterioration" : value < 0 ? "Offset deterioration" : "No net contribution";
      return `<tr><td class="deal-name">${escapeHtml(item.deal_id)}</td><td class="num ${signedClass(item.rate_effect_bps)}">${basisPoints(item.rate_effect_bps, 3)}</td><td class="num ${signedClass(item.mix_effect_bps)}">${basisPoints(item.mix_effect_bps, 3)}</td><td class="num ${signedClass(value)}">${basisPoints(value, 3)}</td><td>${interpretation}</td></tr>`;
    })
    .join("");
}

function flowMeasure(label, rate, countValue, denominator) {
  return `<div class="flow-measure"><span>${escapeHtml(label)}</span><strong>${percent(rate, 2)}</strong><small>${count(countValue)} loans${denominator ? `; ${escapeHtml(denominator)}` : ""}</small></div>`;
}

function renderFlows() {
  const flow = state.deal.flow;
  if (!flow) {
    $("flow-grid").innerHTML = '<div class="flow-measure"><span>Adjacent-period flow</span><strong>Unavailable</strong><small>The selected period has no comparable prior observation.</small></div>';
    $("flow-match").textContent = "Prior-period comparison unavailable";
  } else {
    $("flow-match").textContent = `${percent(flow.loan_match_rate, 2)} loan match`;
    $("flow-context").textContent = `${state.deal.deal_id} at ${state.deal.period}; ${count(flow.matched_records)} prior rows matched.`;
    $("flow-grid").innerHTML = [
      flowMeasure("Current to D30", flow.current_to_d30_rate_upb, flow.current_to_d30_loans, "prior-current UPB"),
      flowMeasure("D30 to D60", flow.d30_to_d60_rate_upb, flow.d30_to_d60_loans, "prior-D30 UPB"),
      flowMeasure("Cure", flow.cure_rate_upb, flow.cured_loans, "prior-D30+ UPB"),
      flowMeasure("Voluntary payoff", flow.voluntary_payoff_rate_upb, flow.voluntary_payoff_loans, "beginning UPB"),
      flowMeasure("Credit-event exit", flow.credit_event_exit_rate_upb, flow.credit_event_exit_loans, "beginning UPB"),
      flowMeasure("New modification", state.deal.current.new_modification_rate_count, flow.new_modification_loans, "active loans"),
    ].join("");
  }
  const riskByLayer = new Map(state.deal.risk_layers.map((layer) => [number(layer.risk_layer_count), layer]));
  $("risk-layers").innerHTML = [0, 1, 2, 3, 4]
    .map((layerNumber) => {
      const layer = riskByLayer.get(layerNumber);
      return `<div class="risk-layer ${layerNumber >= 2 ? "high" : ""}"><span>${layerNumber} condition${layerNumber === 1 ? "" : "s"}</span><strong>${percent(layer?.upb_share ?? 0, 2)}</strong></div>`;
    })
    .join("");
  $("pool-table-body").innerHTML = state.deal.pools.length
    ? state.deal.pools.map((pool) => `<tr><td>${escapeHtml(pool.reference_pool_number)}</td><td class="num">${compactMoney(pool.eligible_current_upb)}</td><td class="num">${percent(pool.d60_plus_rate, 3)}</td><td class="num ${signedClass(pool.d60_change_1m_bps)}">${basisPoints(pool.d60_change_1m_bps, 2)}</td><td class="num">${percent(pool.assistance_exposure_share, 2)}</td></tr>`).join("")
    : '<tr><td colspan="5">No reference-pool rows match this selection.</td></tr>';
}

function renderLoans() {
  const result = state.loans;
  if (!result) {
    $("loan-page-status").textContent = "No restricted rows loaded";
    $("loan-prev").disabled = true;
    $("loan-next").disabled = true;
    $("loan-table-body").innerHTML = '<tr><td colspan="13">Rows are not loaded. Use the explicit local-access action above.</td></tr>';
    return;
  }
  const start = result.total ? result.offset + 1 : 0;
  const end = Math.min(result.offset + result.rows.length, result.total);
  $("loan-page-status").textContent = `${count(start)}-${count(end)} of ${count(result.total)} restricted rows; identifiers ${result.identifiers_revealed ? "revealed" : "masked"}`;
  $("loan-prev").disabled = result.offset === 0;
  $("loan-next").disabled = result.offset + result.limit >= result.total;
  $("loan-table-body").innerHTML = result.rows.length
    ? result.rows.map((row) => {
        const assistance = ASSISTANCE[row.borrower_assistance_plan] || DEFERRAL[row.payment_deferral_flag] || "None reported";
        return `<tr><td>${escapeHtml(row.loan_identifier)}</td><td>${escapeHtml(row.reference_pool_number)}</td><td>${escapeHtml(row.performance_state)}</td><td>${escapeHtml(row.zero_balance_code || "Active")}</td><td class="num">${money(row.current_upb)}</td><td class="num">${count(row.risk_layer_count)}</td><td class="num">${row.classic_fico_value ?? "Unavailable"}</td><td class="num">${row.original_ltv_value ?? "Unavailable"}</td><td class="num">${row.original_dti_value ?? "Unavailable"}</td><td>${escapeHtml(LOAN_PURPOSE[row.loan_purpose] || row.loan_purpose || "Unavailable")}</td><td>${escapeHtml(OCCUPANCY[row.occupancy_status] || row.occupancy_status || "Unavailable")}</td><td>${escapeHtml(MODIFICATION[row.modification_flag] || "None reported")}</td><td>${escapeHtml(assistance)}</td></tr>`;
      }).join("")
    : '<tr><td colspan="13">No permitted rows match these filters. Clear a status or risk-layer filter to recover the view.</td></tr>';
}

function renderAll() {
  renderPulse();
  renderWatchlist();
  renderComparison();
  renderDrivers();
  renderFlows();
  renderLoans();
  $("source-status").textContent = `${state.bootstrap.periods.length} periods and ${state.bootstrap.deals.length} deals available from the read-only local layer`;
  $("source-version").textContent = `Metric ${state.deal.current.metric_version}; restricted-derived analytics`;
}

async function loadLoans() {
  const filters = currentFilters();
  state.loans = await api("/api/loans", {
    period: filters.period,
    deal_id: filters.deal,
    status: $("loan-status").value,
    risk_layer: $("loan-risk").value,
    limit: state.loanLimit,
    offset: state.loanOffset,
    include_identifiers: $("show-identifiers").checked,
  });
  renderLoans();
  ["loan-status", "loan-risk", "show-identifiers"].forEach((id) => { $(id).disabled = false; });
  $("load-loans").textContent = "Reload restricted rows";
  setAnnouncement(`${count(state.loans.rows.length)} restricted rows loaded. Identifiers are ${state.loans.identifiers_revealed ? "revealed" : "masked"}.`);
}

async function loadDeal() {
  setBusy(true);
  clearError();
  try {
    const filters = currentFilters();
    state.deal = await api("/api/deal", { period: filters.period, deal_id: filters.deal });
    state.loans = null;
    ["loan-status", "loan-risk", "show-identifiers"].forEach((id) => { $(id).disabled = true; });
    $("load-loans").textContent = "Load 50 restricted rows";
    renderComparison();
    renderFlows();
    renderLoans();
    $("source-version").textContent = `Metric ${state.deal.current.metric_version}; restricted-derived analytics`;
    setBusy(false);
  } catch (error) {
    showError(error);
  }
}

async function loadWorkspace() {
  setBusy(true);
  clearError();
  try {
    const filters = currentFilters();
    state.overview = await api("/api/overview", {
      period: filters.period,
      sort: filters.sort,
      direction: "desc",
    });
    const availableDeals = state.overview.watchlist.map((item) => item.deal_id);
    populateDealControl(availableDeals);
    state.loanOffset = 0;
    syncUrl();
    const selected = currentFilters();
    state.deal = await api("/api/deal", { period: selected.period, deal_id: selected.deal });
    state.loans = null;
    ["loan-status", "loan-risk", "show-identifiers"].forEach((id) => { $(id).disabled = true; });
    $("load-loans").textContent = "Load 50 restricted rows";
    renderAll();
    $("loading-state").classList.add("hidden");
    $("workspace").classList.remove("hidden");
    setBusy(false);
    setAnnouncement(`Workbench updated for ${selected.period}.`);
  } catch (error) {
    showError(error);
  }
}

async function exportEvidence() {
  const filters = currentFilters();
  $("export-evidence").disabled = true;
  try {
    const response = await fetch(`/api/evidence?${queryString({ period: filters.period, deal_id: filters.deal })}`);
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.error || "Evidence export failed.");
    }
    const blob = await response.blob();
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `crt-evidence-${filters.deal}-${filters.period}.json`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(link.href);
    setAnnouncement("Evidence package downloaded. It excludes loan rows and identifiers.");
  } catch (error) {
    showError(error);
  } finally {
    $("export-evidence").disabled = false;
  }
}

function bindEvents() {
  $("period-filter").addEventListener("change", async () => {
    state.loanOffset = 0;
    syncUrl();
    await loadWorkspace();
  });
  $("deal-filter").addEventListener("change", async () => {
    state.loanOffset = 0;
    syncUrl();
    await loadDeal();
    renderWatchlist();
    setAnnouncement(`${$("deal-filter").value} selected for investigation.`);
  });
  $("sort-filter").addEventListener("change", async () => {
    $("metric-picker").value = SORTS[$("sort-filter").value].metric;
    renderMetricDefinition();
    syncUrl();
    await loadWorkspace();
  });
  $("metric-picker").addEventListener("change", renderMetricDefinition);
  $("load-loans").addEventListener("click", async () => {
    state.loanOffset = 0;
    try {
      await loadLoans();
    } catch (error) {
      showError(error);
    }
  });
  $("loan-status").addEventListener("change", async () => {
    state.loanOffset = 0;
    try {
      await loadLoans();
    } catch (error) {
      showError(error);
    }
  });
  $("loan-risk").addEventListener("change", async () => {
    state.loanOffset = 0;
    try {
      await loadLoans();
    } catch (error) {
      showError(error);
    }
  });
  $("show-identifiers").addEventListener("change", async () => {
    state.loanOffset = 0;
    $("loan-warning").textContent = $("show-identifiers").checked
      ? "Restricted identifiers are visible in this local session. Do not capture or distribute this table."
      : "Identifiers are masked by default. Revealing them keeps the session local but increases handling sensitivity.";
    try {
      await loadLoans();
    } catch (error) {
      showError(error);
    }
  });
  $("loan-prev").addEventListener("click", async () => {
    state.loanOffset = Math.max(0, state.loanOffset - state.loanLimit);
    try {
      await loadLoans();
    } catch (error) {
      showError(error);
    }
  });
  $("loan-next").addEventListener("click", async () => {
    state.loanOffset += state.loanLimit;
    try {
      await loadLoans();
    } catch (error) {
      showError(error);
    }
  });
  $("export-evidence").addEventListener("click", exportEvidence);
  $("retry-button").addEventListener("click", initialize);
}

async function initialize() {
  $("loading-state").classList.remove("hidden");
  $("error-state").classList.add("hidden");
  setBusy(true);
  try {
    state.bootstrap = await api("/api/bootstrap");
    if (!state.bootstrap.local_only || state.bootstrap.data_classification !== "restricted-derived-analytics") {
      throw new Error("The service did not confirm the restricted local boundary.");
    }
    populateControls();
    if (!state.initialized) {
      bindEvents();
      state.initialized = true;
    }
    await loadWorkspace();
  } catch (error) {
    showError(error);
  }
}

initialize();
