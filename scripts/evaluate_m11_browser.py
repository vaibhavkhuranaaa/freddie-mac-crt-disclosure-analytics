#!/usr/bin/env python3
"""Collect safe M11 browser evidence from the loopback public and private surfaces."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import time
from datetime import date
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data/derived/m11_browser_evaluation.json"
SCREENSHOTS = ROOT / "evaluation/m11-browser"
REQUIRED_LOCAL_HEADERS = {
    "content-security-policy",
    "x-content-type-options",
    "x-frame-options",
    "referrer-policy",
    "permissions-policy",
    "cross-origin-opener-policy",
    "cross-origin-resource-policy",
}


class BrowserCheckError(RuntimeError):
    pass


def command(session: str, *arguments: str, allowed_domains: bool = False) -> dict[str, Any]:
    executable = shutil.which("agent-browser")
    if not executable:
        raise BrowserCheckError("agent-browser is not installed")
    invocation = [executable, "--session", session]
    if allowed_domains:
        invocation.extend(["--allowed-domains", "127.0.0.1"])
    invocation.extend(["--json", *arguments])
    completed = subprocess.run(
        invocation,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    if completed.returncode != 0:
        raise BrowserCheckError(completed.stderr.strip() or completed.stdout.strip())
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise BrowserCheckError(f"agent-browser returned invalid JSON: {completed.stdout[:240]}") from error
    if not payload.get("success"):
        raise BrowserCheckError(str(payload.get("error") or payload))
    return payload.get("data") or {}


def evaluate(session: str, script: str) -> Any:
    return command(session, "eval", script).get("result")


def response_headers(url: str, headers: dict[str, str] | None = None) -> tuple[int, dict[str, str]]:
    request = Request(url, method="HEAD", headers=headers or {})
    try:
        with urlopen(request, timeout=10) as response:
            return response.status, {key.lower(): value for key, value in response.headers.items()}
    except HTTPError as error:
        return error.code, {key.lower(): value for key, value in error.headers.items()}


def a11y_summary(session: str) -> dict[str, Any]:
    result = command(session, "a11y", "--tags", "wcag2a,wcag2aa")
    counts = result["counts"]
    return {
        "axe_version": result["axeVersion"],
        "violations": counts["violations"],
        "incomplete": counts["incomplete"],
        "passes": counts["passes"],
        "violation_ids": [item["id"] for item in result.get("violations", [])],
        "incomplete_ids": [item["id"] for item in result.get("incomplete", [])],
    }


def contrast_ratio(foreground: str, background: str) -> float:
    def luminance(color: str) -> float:
        channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
        linear = [
            value / 12.92
            if value <= 0.04045
            else ((value + 0.055) / 1.055) ** 2.4
            for value in channels
        ]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    lighter, darker = sorted(
        (luminance(foreground), luminance(background)), reverse=True
    )
    return (lighter + 0.05) / (darker + 0.05)


def manual_contrast_review() -> dict[str, float]:
    return {
        "chart_axis_on_white": round(contrast_ratio("#596169", "#ffffff"), 3),
        "chart_axis_on_paper": round(contrast_ratio("#596169", "#eef1ef"), 3),
        "evidence_pass_on_white": round(contrast_ratio("#176150", "#ffffff"), 3),
        "evidence_pass_on_selected_row": round(
            contrast_ratio("#176150", "#f6ffd6"), 3
        ),
    }


def public_checks(url: str, session: str) -> dict[str, Any]:
    workflow_started = time.perf_counter()
    command(session, "open", url, allowed_domains=True)
    command(session, "wait", "--load", "networkidle")
    SCREENSHOTS.mkdir(parents=True, exist_ok=True)
    command(session, "screenshot", str(SCREENSHOTS / "public-desktop.png"))
    desktop_a11y = a11y_summary(session)
    vitals = command(session, "vitals", url)
    initial = evaluate(
        session,
        "({hasContent:document.body.innerText.trim().length>0,workspaceVisible:!document.getElementById('workspace').classList.contains('hidden'),pulse:document.getElementById('pulse-change').textContent,defaultRank:document.getElementById('sort-filter').value,rankMeasureCount:document.getElementById('sort-filter').options.length,dealCount:document.getElementById('deal-filter').options.length,publicHasLoanControls:Boolean(document.getElementById('load-loans')),userAgent:navigator.userAgent})",
    )
    command(session, "focus", '#watchlist-body tr[data-deal="2024-HQA2"] .deal-select')
    command(session, "press", "Enter")
    keyboard = evaluate(
        session,
        "({deal:new URL(location.href).searchParams.get('deal'),selected:document.querySelector('#watchlist-body tr[aria-selected=\"true\"]')?.dataset.deal,activeTag:document.activeElement?.tagName})",
    )
    feedback_ms = evaluate(
        session,
        "(async()=>{const s=document.getElementById('sort-filter');s.value='d60_plus_rate';const t=performance.now();s.dispatchEvent(new Event('change',{bubbles:true}));await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));return performance.now()-t})()",
    )
    period_valid = evaluate(
        session,
        "(async()=>{const s=document.getElementById('period-filter');s.value='202307';s.dispatchEvent(new Event('change',{bubbles:true}));await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));return {deals:document.getElementById('deal-filter').options.length,period:new URL(location.href).searchParams.get('period')}})()",
    )
    workflow = evaluate(
        session,
        "({pulse:document.getElementById('pulse').innerText.length>0,watchlist:document.querySelectorAll('#watchlist-body tr').length>0,comparison:document.getElementById('comparison-summary').innerText.length>0,drivers:document.getElementById('driver-body').innerText.length>0,flows:document.getElementById('flow-grid').innerText.length>0,evidence:document.getElementById('metric-definition').innerText.length>0,boundary:document.querySelector('.boundary').innerText.includes('controlled local workbench')})",
    )
    command(session, "network", "route", "**/crt_public_projection.json", "--abort")
    command(session, "reload")
    command(session, "wait", "--text", "Unable to load aggregate data.")
    error_state = evaluate(
        session,
        "({visible:!document.getElementById('error').classList.contains('hidden'),recovery:document.getElementById('error-message').innerText.includes('Rebuild the public projection')})",
    )
    command(session, "network", "unroute")
    command(session, "errors", "--clear")
    command(session, "reload")
    command(session, "wait", "--load", "networkidle")
    responsive: dict[str, Any] = {}
    for name, width, height in (
        ("zoom_equivalent_320", 320, 844),
        ("mobile", 390, 844),
        ("tablet", 768, 1024),
        ("desktop", 1440, 900),
    ):
        command(session, "set", "viewport", str(width), str(height))
        command(session, "reload")
        command(session, "wait", "--load", "networkidle")
        responsive[name] = evaluate(
            session,
            "({viewport:{width:innerWidth,height:innerHeight},bodyOverflow:document.documentElement.scrollWidth>innerWidth,workspaceVisible:!document.getElementById('workspace').classList.contains('hidden'),tablesScrollable:[...document.querySelectorAll('.table-scroll')].every(e=>e.scrollWidth<=e.clientWidth||getComputedStyle(e).overflowX==='auto')})",
        )
        if name == "mobile":
            evaluate(
                session,
                "document.documentElement.style.scrollBehavior='auto';scrollTo(0,0)",
            )
            command(session, "wait", "--fn", "window.scrollY===0")
            command(session, "screenshot", str(SCREENSHOTS / "public-mobile.png"))
    mobile_a11y = a11y_summary(session)
    contrast = manual_contrast_review()
    contrast_resolved = min(contrast.values()) >= 4.5
    command(session, "set", "media", "light", "reduced-motion")
    reduced_motion = evaluate(session, "matchMedia('(prefers-reduced-motion: reduce)').matches")
    errors = command(session, "errors").get("errors", [])
    console = command(session, "console").get("messages", [])
    status, headers = response_headers(url)
    command(session, "close")
    workflow_seconds = round(time.perf_counter() - workflow_started, 3)
    checks = {
        "page_has_meaningful_content": initial["hasContent"] and initial["workspaceVisible"],
        "default_rank_is_portfolio_contribution": initial["defaultRank"] == "total_contribution_bps",
        "five_visible_rank_measures": initial["rankMeasureCount"] == 5,
        "public_has_no_restricted_row_control": initial["publicHasLoanControls"] is False,
        "keyboard_row_selection_updates_url_and_state": keyboard["deal"] == keyboard["selected"] == "2024-HQA2",
        "period_valid_deals": period_valid == {"deals": 5, "period": "202307"},
        "filter_feedback_under_100_ms": float(feedback_ms) <= 100,
        "five_minute_technical_self_test_under_300_seconds": workflow_seconds <= 300 and all(workflow.values()),
        "error_state_names_recovery": all(error_state.values()),
        "desktop_wcag_a_aa_zero_violations": desktop_a11y["violations"] == 0,
        "desktop_manual_contrast_review_resolves_axe_incomplete": set(
            desktop_a11y["incomplete_ids"]
        )
        <= {"color-contrast"}
        and contrast_resolved,
        "mobile_wcag_a_aa_zero_violations": mobile_a11y["violations"] == 0,
        "mobile_manual_contrast_review_resolves_axe_incomplete": set(
            mobile_a11y["incomplete_ids"]
        )
        <= {"color-contrast"}
        and contrast_resolved,
        "responsive_profiles_have_no_body_overflow": all(not item["bodyOverflow"] for item in responsive.values()),
        "responsive_profiles_keep_workspace_visible": all(item["workspaceVisible"] for item in responsive.values()),
        "wide_tables_remain_locally_scrollable": all(item["tablesScrollable"] for item in responsive.values()),
        "reduced_motion_preference_detected": reduced_motion is True,
        "no_unexpected_page_errors": not errors,
        "no_console_messages": not console,
        "local_public_headers_present": status == 200 and REQUIRED_LOCAL_HEADERS <= set(headers),
        "lcp_under_2500_ms": float(vitals["lcp"]["startTime"]) <= 2_500,
        "fcp_under_1800_ms": float(vitals["fcp"]) <= 1_800,
        "ttfb_under_800_ms": float(vitals["ttfb"]) <= 800,
        "cls_under_0_1": float(vitals["cls"]["score"]) < 0.1,
    }
    return {
        "status": "pass" if all(checks.values()) else "fail",
        "checks": checks,
        "browser": {"engine": "Chromium via agent-browser", "user_agent": initial["userAgent"]},
        "a11y": {
            "desktop": desktop_a11y,
            "mobile": mobile_a11y,
            "manual_contrast_ratios": contrast,
            "minimum_required_ratio": 4.5,
            "note": "Axe cannot determine SVG image-node backgrounds; the exact foreground/background pairs were calculated separately.",
        },
        "responsive": responsive,
        "performance": {
            "local_lab_only": True,
            "ttfb_ms": vitals["ttfb"],
            "fcp_ms": vitals["fcp"],
            "lcp_ms": vitals["lcp"]["startTime"],
            "cls": vitals["cls"]["score"],
            "inp": vitals.get("inp"),
            "filter_feedback_ms": round(float(feedback_ms), 3),
            "technical_self_test_seconds": workflow_seconds,
            "note": "INP is not claimed because the local synthetic run did not produce a field-style INP sample.",
        },
        "error_state": error_state,
        "screenshots": [
            str((SCREENSHOTS / "public-desktop.png").relative_to(ROOT)),
            str((SCREENSHOTS / "public-mobile.png").relative_to(ROOT)),
        ],
    }


def private_checks(url: str, session: str) -> dict[str, Any]:
    command(session, "open", url, allowed_domains=True)
    command(session, "wait", "--load", "networkidle")
    accessibility = a11y_summary(session)
    contrast = manual_contrast_review()
    contrast_resolved = min(contrast.values()) >= 4.5
    initial = evaluate(
        session,
        "({workspaceVisible:!document.getElementById('workspace').classList.contains('hidden'),rowsDeferred:document.getElementById('loan-table-body').innerText.includes('Rows are not loaded'),loanRequestAbsent:!performance.getEntriesByType('resource').some(e=>e.name.includes('/api/loans')),identifiersDisabled:document.getElementById('show-identifiers').disabled,defaultRank:document.getElementById('sort-filter').value})",
    )
    command(session, "focus", '#watchlist-body tr[data-deal="2024-HQA2"]')
    command(session, "press", "Enter")
    command(
        session,
        "wait",
        "--fn",
        "new URL(location.href).searchParams.get('deal')==='2024-HQA2'&&document.querySelector('#watchlist-body tr[aria-selected=\"true\"]')?.dataset.deal==='2024-HQA2'",
    )
    keyboard = evaluate(
        session,
        "({deal:new URL(location.href).searchParams.get('deal'),selected:document.querySelector('#watchlist-body tr[aria-selected=\"true\"]')?.dataset.deal})",
    )
    command(session, "set", "viewport", "390", "844")
    command(session, "reload")
    command(session, "wait", "--load", "networkidle")
    responsive = evaluate(
        session,
        "({bodyOverflow:document.documentElement.scrollWidth>innerWidth,workspaceVisible:!document.getElementById('workspace').classList.contains('hidden'),tablesScrollable:[...document.querySelectorAll('.table-scroll')].every(e=>e.scrollWidth<=e.clientWidth||getComputedStyle(e).overflowX==='auto')})",
    )
    command(session, "click", "#load-loans")
    command(session, "wait", "--fn", "document.getElementById('loan-page-status').textContent.includes('restricted rows;')")
    on_demand = evaluate(
        session,
        "({rowCount:document.querySelectorAll('#loan-table-body tr').length,masked:/^restricted-/.test(document.querySelector('#loan-table-body tr td')?.textContent||''),identifiersRevealed:document.getElementById('show-identifiers').checked,requestObserved:performance.getEntriesByType('resource').some(e=>e.name.includes('/api/loans'))})",
    )
    errors = command(session, "errors").get("errors", [])
    console = command(session, "console").get("messages", [])
    status, headers = response_headers(url)
    rejected_status, _ = response_headers(
        url,
        {"Host": "example.com", "Origin": "https://example.com"},
    )
    command(session, "close")
    checks = {
        "workspace_visible": initial["workspaceVisible"],
        "restricted_rows_deferred": initial["rowsDeferred"] and initial["loanRequestAbsent"],
        "identifier_reveal_disabled_before_load": initial["identifiersDisabled"],
        "default_rank_is_portfolio_contribution": initial["defaultRank"] == "total_contribution_bps",
        "keyboard_row_selection_updates_url_and_state": keyboard["deal"]
        == keyboard["selected"]
        == "2024-HQA2",
        "mobile_has_no_body_overflow": responsive["bodyOverflow"] is False,
        "mobile_workspace_visible": responsive["workspaceVisible"],
        "mobile_tables_locally_scrollable": responsive["tablesScrollable"],
        "explicit_row_action_loads_50_masked_rows": on_demand["rowCount"] == 50
        and on_demand["masked"]
        and on_demand["requestObserved"],
        "identifiers_remain_masked_by_default": on_demand["identifiersRevealed"] is False,
        "wcag_a_aa_zero_violations": accessibility["violations"] == 0,
        "manual_contrast_review_resolves_axe_incomplete": set(
            accessibility["incomplete_ids"]
        )
        <= {"color-contrast"}
        and contrast_resolved,
        "no_unexpected_page_errors": not errors,
        "no_console_messages": not console,
        "local_private_headers_present": status == 200 and REQUIRED_LOCAL_HEADERS <= set(headers),
        "non_loopback_host_and_origin_rejected": rejected_status == 421,
    }
    return {
        "status": "pass" if all(checks.values()) else "fail",
        "checks": checks,
        "a11y": {
            **accessibility,
            "manual_contrast_ratios": contrast,
            "minimum_required_ratio": 4.5,
            "note": "Axe cannot determine SVG image-node and partially obscured table backgrounds; the exact foreground/background pairs were calculated separately.",
        },
        "responsive": responsive,
        "restricted_row_probe": {
            "rows_loaded_after_explicit_action": on_demand["rowCount"],
            "identifiers_masked": on_demand["masked"],
            "identifiers_revealed": on_demand["identifiersRevealed"],
            "raw_rows_or_identifiers_retained_in_evidence": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate M11 browser behavior on loopback only.")
    parser.add_argument("--public-url", default="http://127.0.0.1:8010/")
    parser.add_argument("--private-url", default="http://127.0.0.1:8011/")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    stamp = str(time.time_ns())
    public = public_checks(args.public_url, f"crt-m11-public-{stamp}")
    private = private_checks(args.private_url, f"crt-m11-private-{stamp}")
    report = {
        "report_version": 1,
        "evaluation_date": date.today().isoformat(),
        "milestone": "M11",
        "status": "pass" if public["status"] == private["status"] == "pass" else "fail",
        "scope": "Local Chromium lab evidence for the public candidate and loopback private workbench.",
        "public": public,
        "private": private,
        "browser_coverage": {
            "verified": [
                "Chromium desktop",
                "Chromium tablet viewport",
                "Chromium mobile viewport",
                "Chromium 320 CSS-pixel reflow (400% zoom equivalent at 1280 CSS pixels)",
            ],
            "not_available": ["Firefox", "Safari", "field Core Web Vitals"],
            "claim_boundary": "No cross-engine or real-user-monitoring claim is made.",
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
