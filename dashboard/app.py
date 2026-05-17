"""Streamlit dashboard — Supply Chain Anomaly Detector."""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

API_BASE = os.environ.get("ANOMALY_API", "http://localhost:8000")
API_V1 = f"{API_BASE}/api/v1"

DARK_BG = "#0b0b0b"
PANEL = "#141414"
OK = "#00C896"
BAD = "#FF4B4B"
WARN = "#FFB347"
INFO = "#FFD700"

PLOTLY_TEMPLATE = "plotly_dark"

st.set_page_config(
    page_title="Supply Chain Anomaly Detector",
    page_icon="⚠️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
def inject_css() -> None:
    css_path = ROOT / "assets" / "style.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>",
                    unsafe_allow_html=True)


inject_css()


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------
def api_get(path: str, params: Dict[str, Any] | None = None, timeout: float = 8.0):
    try:
        r = requests.get(f"{API_V1}{path}", params=params, timeout=timeout)
        return r.status_code, (r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text), r.elapsed.total_seconds() * 1000
    except Exception as e:  # noqa: BLE001
        return 0, {"error": str(e)}, 0.0


def api_post(path: str, payload: Any, timeout: float = 30.0):
    try:
        r = requests.post(f"{API_V1}{path}", json=payload, timeout=timeout)
        return r.status_code, (r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text), r.elapsed.total_seconds() * 1000
    except Exception as e:  # noqa: BLE001
        return 0, {"error": str(e)}, 0.0


@st.cache_data(ttl=10)
def fetch_status() -> Dict[str, Any]:
    code, data, _ = api_get("/status")
    if code != 200:
        return {"online": False}
    return {"online": True, **data}


@st.cache_data(ttl=15)
def fetch_history(domain: str | None, severity_min: float, limit: int = 500) -> pd.DataFrame:
    params: Dict[str, Any] = {"severity_min": severity_min, "limit": limit}
    if domain and domain != "All":
        params["domain"] = domain.lower()
    code, data, _ = api_get("/anomalies/history", params=params)
    if code != 200 or "items" not in data:
        return pd.DataFrame()
    return pd.DataFrame(data["items"])


@st.cache_data(ttl=15)
def fetch_stats() -> Dict[str, Any]:
    code, data, _ = api_get("/anomalies/stats")
    return data if code == 200 else {}


@st.cache_data(ttl=30)
def fetch_dataset(domain: str, limit: int = 5000) -> pd.DataFrame:
    code, data, _ = api_get(f"/data/{domain}", params={"limit": limit})
    if code != 200:
        return pd.DataFrame()
    return pd.DataFrame(data.get("records", []))


@st.cache_data(ttl=60)
def fetch_model_info(domain: str) -> Dict[str, Any]:
    code, data, _ = api_get(f"/models/{domain}")
    return data if code == 200 else {}


def severity_color(s: float) -> str:
    if s >= 70:
        return BAD
    if s >= 40:
        return WARN
    return INFO


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
def sidebar() -> Dict[str, Any]:
    st.sidebar.markdown("## ⚠️ Anomaly Detector")
    st.sidebar.caption("Project 4 — Logistics Portfolio")

    status = fetch_status()
    pill = "online" if status.get("online") else "offline"
    st.sidebar.markdown(
        f'<span class="api-pill {pill}">API: {pill.upper()}</span>',
        unsafe_allow_html=True,
    )
    st.sidebar.markdown("---")

    domain = st.sidebar.selectbox(
        "Domain filter",
        ["All", "Operators", "Inventory", "Routes", "Deliveries"],
        index=0,
    )
    today = datetime.now().date()
    date_range = st.sidebar.date_input(
        "Date range",
        value=(today - timedelta(days=30), today),
    )
    severity = st.sidebar.slider("Min severity", 0, 100, 0, 5)
    entity_query = st.sidebar.text_input("Entity filter (operator / SKU / supplier)", "")
    auto_refresh = st.sidebar.toggle("Auto-refresh (30s)", value=False)

    st.sidebar.markdown("---")
    col_a, col_b = st.sidebar.columns(2)
    if col_a.button("🔄 Run detection", use_container_width=True):
        run_detection_on_all()
    if col_b.button("🧠 Train models", use_container_width=True):
        train_all_models()

    if st.sidebar.button("📡 Simulate real-time tick", use_container_width=True):
        simulate_tick(domain.lower() if domain != "All" else "operators")

    st.sidebar.markdown("---")
    st.sidebar.caption(f"API base: `{API_BASE}`")
    st.sidebar.caption("Made by Iyad Belkadi")

    return {
        "domain": domain,
        "date_range": date_range,
        "severity": severity,
        "entity_query": entity_query.strip(),
        "auto_refresh": auto_refresh,
        "status": status,
    }


def run_detection_on_all() -> None:
    with st.spinner("Running detection across all 4 domains…"):
        for d in ("operators", "inventory", "routes", "deliveries"):
            df = fetch_dataset(d, limit=300)
            if df.empty:
                continue
            api_post(f"/detect/{d}", df.to_dict(orient="records"))
        fetch_history.clear()
        fetch_stats.clear()
    st.toast("Detection complete", icon="✅")


def train_all_models() -> None:
    with st.spinner("Retraining all models…"):
        code, _, ms = api_post("/train", {"domain": "all"})
    if code == 200:
        fetch_model_info.clear()
        st.toast(f"Training complete ({ms:.0f} ms)", icon="🧠")
    else:
        st.toast("Training failed", icon="❌")


def simulate_tick(domain: str) -> None:
    code, data, _ = api_post("/stream/tick", {"domain": domain, "force_anomaly": False})
    if code == 200:
        if data.get("is_anomaly"):
            st.toast(f"⚠️ Anomaly detected · {data.get('severity', 0):.0f}/100", icon="⚠️")
        else:
            st.toast("Tick processed — normal", icon="✅")


# ---------------------------------------------------------------------------
# Tab 1 — Live monitor
# ---------------------------------------------------------------------------
def metric_card(label: str, value: Any, klass: str = "") -> str:
    return (
        f'<div class="metric-card {klass}">'
        f'<div class="label">{label}</div>'
        f'<div class="value">{value}</div>'
        f"</div>"
    )


def tab_live(sb: Dict[str, Any]) -> None:
    st.subheader("Live Monitor")
    if not sb["status"].get("online"):
        st.markdown('<div class="alert-banner">🛑 API offline — start the FastAPI server (python start.py)</div>',
                    unsafe_allow_html=True)
        return

    stats = fetch_stats()
    history = fetch_history(None, 0, limit=500)
    today_str = datetime.now().date().isoformat()
    today_count = int(history["detected_at"].str.startswith(today_str).sum()) if not history.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(metric_card("Anomalies today", today_count, "bad" if today_count else "ok"),
                unsafe_allow_html=True)
    c2.markdown(metric_card("Total tracked", stats.get("total_anomalies", 0), "info"),
                unsafe_allow_html=True)
    high = stats.get("severity_distribution", {}).get("high", 0)
    c3.markdown(metric_card("High severity", high, "bad" if high else "ok"),
                unsafe_allow_html=True)
    trained = sum(1 for v in sb["status"].get("trained", {}).values() if v)
    c4.markdown(metric_card("Models trained", f"{trained}/4", "ok"), unsafe_allow_html=True)

    st.markdown("### Domain breakdown")
    cols = st.columns(4)
    domains = ["operators", "inventory", "routes", "deliveries"]
    icons = {"operators": "👷", "inventory": "📦", "routes": "🛣️", "deliveries": "🚚"}
    for col, d in zip(cols, domains):
        count = stats.get("by_domain", {}).get(d, 0)
        klass = "bad" if count > 20 else ("warn" if count > 5 else "ok")
        col.markdown(metric_card(f"{icons[d]} {d.title()}", count, klass), unsafe_allow_html=True)

    st.markdown("### Severity gauge (max active)")
    max_sev = float(history["severity"].max()) if not history.empty else 0.0
    g = go.Figure(go.Indicator(
        mode="gauge+number",
        value=max_sev,
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": severity_color(max_sev)},
            "steps": [
                {"range": [0, 40], "color": "#1e1e1e"},
                {"range": [40, 70], "color": "#2b2410"},
                {"range": [70, 100], "color": "#2b1010"},
            ],
        },
    ))
    g.update_layout(template=PLOTLY_TEMPLATE, height=260, margin=dict(l=20, r=20, t=20, b=20),
                    paper_bgcolor=DARK_BG)
    st.plotly_chart(g, use_container_width=True, key="live_gauge")

    st.markdown("### Real-time feed (last 20)")
    if history.empty:
        st.info("No anomalies yet — try clicking **Run detection** in the sidebar.")
    else:
        feed = history.head(20)[["detected_at", "domain", "entity", "severity", "severity_band", "likely_cause"]]
        st.dataframe(feed, hide_index=True, use_container_width=True)


# ---------------------------------------------------------------------------
# Helpers for domain tabs
# ---------------------------------------------------------------------------
def detect_and_merge(domain: str) -> pd.DataFrame:
    df = fetch_dataset(domain, limit=2000)
    if df.empty:
        return df
    code, data, _ = api_post(f"/detect/{domain}", df.to_dict(orient="records"))
    if code != 200:
        df["is_anomaly"] = False
        df["severity"] = 0.0
        df["explanation"] = ""
        return df
    res = pd.DataFrame(data["results"])
    df = df.reset_index(drop=True)
    df["is_anomaly"] = res["is_anomaly"]
    df["severity"] = res["severity"]
    df["severity_band"] = res["severity_band"]
    df["explanation"] = res["explanation"]
    df["likely_cause"] = res["likely_cause"]
    return df


# ---------------------------------------------------------------------------
# Tab 2 — Operators
# ---------------------------------------------------------------------------
def tab_operators() -> None:
    st.subheader("Operator Anomalies")
    df = detect_and_merge("operators")
    if df.empty:
        st.info("No operator data available.")
        return
    anom = df[df["is_anomaly"]]
    st.caption(f"{len(anom)} anomalies / {len(df)} records")

    fig = px.scatter(
        df, x="picks_per_hour", y="error_rate",
        color=df["is_anomaly"].map({True: "anomaly", False: "normal"}),
        color_discrete_map={"anomaly": BAD, "normal": OK},
        hover_data=["operator_name", "shift", "distance_m", "stock_accuracy"],
        title="Picks/h vs Error rate",
    )
    fig.update_layout(template=PLOTLY_TEMPLATE, paper_bgcolor=DARK_BG, plot_bgcolor=DARK_BG)
    st.plotly_chart(fig, use_container_width=True, key="op_scatter")

    if not anom.empty:
        timeline = anom.groupby(["date", "operator_name"]).size().reset_index(name="anomalies")
        fig2 = px.bar(timeline, x="date", y="anomalies", color="operator_name",
                      title="Anomaly events per operator")
        fig2.update_layout(template=PLOTLY_TEMPLATE, paper_bgcolor=DARK_BG, plot_bgcolor=DARK_BG)
        st.plotly_chart(fig2, use_container_width=True, key="op_timeline")

        st.markdown("### Anomalous operators")
        st.dataframe(
            anom[["date", "operator_name", "shift", "picks_per_hour", "error_rate",
                  "distance_m", "stock_accuracy", "severity", "likely_cause"]]
            .sort_values("severity", ascending=False)
            .head(50),
            hide_index=True, use_container_width=True,
        )

    st.markdown("### Feature distribution: normal vs anomalous")
    feature = st.selectbox("Feature", ["picks_per_hour", "error_rate", "distance_m", "stock_accuracy"],
                           key="op_feature")
    fig3 = px.histogram(df, x=feature, color=df["is_anomaly"].map({True: "anomaly", False: "normal"}),
                        nbins=40, color_discrete_map={"anomaly": BAD, "normal": OK},
                        barmode="overlay", opacity=0.75)
    fig3.update_layout(template=PLOTLY_TEMPLATE, paper_bgcolor=DARK_BG, plot_bgcolor=DARK_BG)
    st.plotly_chart(fig3, use_container_width=True, key="op_hist")


# ---------------------------------------------------------------------------
# Tab 3 — Inventory
# ---------------------------------------------------------------------------
def tab_inventory() -> None:
    st.subheader("Inventory Anomalies")
    df = detect_and_merge("inventory")
    if df.empty:
        st.info("No inventory data available.")
        return
    anom = df[df["is_anomaly"]]
    st.caption(f"{len(anom)} anomalies / {len(df)} records")

    pivot = df.pivot_table(index="sku", columns="date", values="severity",
                           aggfunc="max", fill_value=0)
    pivot = pivot.head(45)
    fig = px.imshow(pivot, color_continuous_scale="Inferno", aspect="auto",
                    title="Anomaly score — SKU × Day")
    fig.update_layout(template=PLOTLY_TEMPLATE, paper_bgcolor=DARK_BG, plot_bgcolor=DARK_BG,
                      height=600)
    st.plotly_chart(fig, use_container_width=True, key="inv_heatmap")

    sku_pick = st.selectbox("SKU detail", sorted(df["sku"].unique()), key="inv_sku")
    sub = df[df["sku"] == sku_pick].sort_values("date")
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=sub["date"], y=sub["stock_level"], mode="lines", line=dict(color=OK),
                              name="Stock level"))
    a = sub[sub["is_anomaly"]]
    if not a.empty:
        fig2.add_trace(go.Scatter(x=a["date"], y=a["stock_level"], mode="markers",
                                  marker=dict(size=12, color=BAD, symbol="x"), name="anomaly"))
    fig2.update_layout(template=PLOTLY_TEMPLATE, paper_bgcolor=DARK_BG, plot_bgcolor=DARK_BG,
                       title=f"Stock level — {sku_pick}")
    st.plotly_chart(fig2, use_container_width=True, key="inv_stock")

    if not anom.empty:
        st.markdown("### Anomalous SKU events")
        st.dataframe(
            anom[["date", "sku", "name", "zone_name", "units_sold", "stock_level",
                  "demand_vs_forecast_ratio", "severity", "likely_cause"]]
            .sort_values("severity", ascending=False)
            .head(60),
            hide_index=True, use_container_width=True,
        )

    by_zone = anom.groupby("zone_name").size().reset_index(name="anomalies") if "zone_name" in anom.columns else pd.DataFrame()
    if not by_zone.empty:
        fig3 = px.bar(by_zone, x="zone_name", y="anomalies", color="anomalies",
                      color_continuous_scale="Reds", title="Anomalies by zone")
        fig3.update_layout(template=PLOTLY_TEMPLATE, paper_bgcolor=DARK_BG, plot_bgcolor=DARK_BG)
        st.plotly_chart(fig3, use_container_width=True, key="inv_zone")


# ---------------------------------------------------------------------------
# Tab 4 — Routes
# ---------------------------------------------------------------------------
def tab_routes() -> None:
    st.subheader("Picking Route Anomalies")
    df = detect_and_merge("routes")
    if df.empty:
        st.info("No route data available.")
        return
    anom = df[df["is_anomaly"]]
    st.caption(f"{len(anom)} anomalies / {len(df)} records")

    fig = px.scatter(df, x="total_distance_m", y="total_time_min",
                     color=df["is_anomaly"].map({True: "anomaly", False: "normal"}),
                     color_discrete_map={"anomaly": BAD, "normal": OK},
                     size="sku_count", hover_data=["order_id", "operator_name", "door_crossings"],
                     title="Route distance vs time")
    fig.update_layout(template=PLOTLY_TEMPLATE, paper_bgcolor=DARK_BG, plot_bgcolor=DARK_BG)
    st.plotly_chart(fig, use_container_width=True, key="rt_scatter")

    fig2 = px.box(df, x="operator_name", y="picks_per_km",
                  color=df["is_anomaly"].map({True: "anomaly", False: "normal"}),
                  color_discrete_map={"anomaly": BAD, "normal": OK},
                  title="Route efficiency by operator")
    fig2.update_layout(template=PLOTLY_TEMPLATE, paper_bgcolor=DARK_BG, plot_bgcolor=DARK_BG)
    st.plotly_chart(fig2, use_container_width=True, key="rt_box")

    if not anom.empty:
        st.markdown("### Anomalous routes")
        st.dataframe(
            anom[["order_id", "timestamp", "operator_name", "total_distance_m",
                  "total_time_min", "door_crossings", "picks_per_km", "severity", "likely_cause"]]
            .sort_values("severity", ascending=False)
            .head(50),
            hide_index=True, use_container_width=True,
        )

    fig3 = px.histogram(df, x="cold_exposure_sec",
                        color=df["is_anomaly"].map({True: "anomaly", False: "normal"}),
                        color_discrete_map={"anomaly": BAD, "normal": OK},
                        nbins=40, barmode="overlay", opacity=0.75,
                        title="Cold exposure outliers")
    fig3.update_layout(template=PLOTLY_TEMPLATE, paper_bgcolor=DARK_BG, plot_bgcolor=DARK_BG)
    st.plotly_chart(fig3, use_container_width=True, key="rt_cold")


# ---------------------------------------------------------------------------
# Tab 5 — Deliveries
# ---------------------------------------------------------------------------
def tab_deliveries() -> None:
    st.subheader("Delivery Anomalies")
    df = detect_and_merge("deliveries")
    if df.empty:
        st.info("No delivery data available.")
        return
    anom = df[df["is_anomaly"]]
    st.caption(f"{len(anom)} anomalies / {len(df)} records")

    fig = px.scatter(df, x="actual_date", y="delay_days",
                     color=df["is_anomaly"].map({True: "anomaly", False: "normal"}),
                     color_discrete_map={"anomaly": BAD, "normal": OK},
                     hover_data=["delivery_id", "supplier", "shortfall_pct", "damage_rate"],
                     title="Deliveries timeline (delay by date)")
    fig.update_layout(template=PLOTLY_TEMPLATE, paper_bgcolor=DARK_BG, plot_bgcolor=DARK_BG)
    st.plotly_chart(fig, use_container_width=True, key="dl_timeline")

    by_supp = df.groupby("supplier")["delay_days"].mean().reset_index().sort_values("delay_days")
    fig2 = px.bar(by_supp, x="supplier", y="delay_days", color="delay_days",
                  color_continuous_scale="Reds", title="Avg delay days by supplier")
    fig2.update_layout(template=PLOTLY_TEMPLATE, paper_bgcolor=DARK_BG, plot_bgcolor=DARK_BG)
    st.plotly_chart(fig2, use_container_width=True, key="dl_supp_delay")

    if not anom.empty:
        st.markdown("### Anomalous deliveries")
        st.dataframe(
            anom[["delivery_id", "supplier", "expected_date", "actual_date", "delay_days",
                  "quantity_ordered", "quantity_received", "shortfall_pct", "damage_rate",
                  "severity", "likely_cause"]]
            .sort_values("severity", ascending=False).head(60),
            hide_index=True, use_container_width=True,
        )

    reliability = (
        df.groupby("supplier")
        .agg(total=("delivery_id", "count"),
             late=("delay_days", lambda x: int((x > 2).sum())),
             dmg=("damage_rate", "mean"))
        .reset_index()
    )
    reliability["score"] = 100 - 100 * reliability["late"] / reliability["total"].clip(lower=1) - reliability["dmg"]
    reliability["score"] = reliability["score"].clip(lower=0, upper=100)
    fig3 = px.bar(reliability.sort_values("score"), x="supplier", y="score",
                  color="score", color_continuous_scale="RdYlGn",
                  title="Supplier reliability score (0-100)")
    fig3.update_layout(template=PLOTLY_TEMPLATE, paper_bgcolor=DARK_BG, plot_bgcolor=DARK_BG)
    st.plotly_chart(fig3, use_container_width=True, key="dl_supp_rel")


# ---------------------------------------------------------------------------
# Tab 6 — Model performance
# ---------------------------------------------------------------------------
def tab_model_perf() -> None:
    st.subheader("Model Performance")
    domains = ["operators", "inventory", "routes", "deliveries"]
    rows: List[Dict[str, Any]] = []
    importances: Dict[str, Dict[str, float]] = {}
    agreement: Dict[str, float] = {}
    for d in domains:
        info = fetch_model_info(d)
        if not info:
            continue
        for model_name, m in info.get("metrics", {}).items():
            rows.append({"domain": d, "model": model_name, **m})
        importances[d] = info.get("feature_importance", {})
        agreement[d] = float(info.get("agreement_rate", 0.0))

    if not rows:
        st.info("No metrics yet — train the models first.")
        return

    metrics_df = pd.DataFrame(rows)
    st.markdown("### Precision / Recall / F1 / ROC-AUC")
    st.dataframe(metrics_df.round(3), hide_index=True, use_container_width=True)

    fig = px.bar(metrics_df, x="domain", y="f1", color="model", barmode="group",
                 title="F1 score per model per domain")
    fig.update_layout(template=PLOTLY_TEMPLATE, paper_bgcolor=DARK_BG, plot_bgcolor=DARK_BG)
    st.plotly_chart(fig, use_container_width=True, key="mp_f1")

    # ROC-AUC bars (proxy for ROC curve presence)
    fig2 = px.bar(metrics_df, x="model", y="roc_auc", color="domain", barmode="group",
                  title="ROC-AUC per model")
    fig2.update_layout(template=PLOTLY_TEMPLATE, paper_bgcolor=DARK_BG, plot_bgcolor=DARK_BG)
    st.plotly_chart(fig2, use_container_width=True, key="mp_auc")

    st.markdown("### Feature importance (Isolation Forest)")
    chosen = st.selectbox("Domain", domains, key="mp_domain")
    fi = importances.get(chosen, {})
    if fi:
        fi_df = pd.DataFrame({"feature": list(fi.keys()), "importance": list(fi.values())})
        fi_df = fi_df.sort_values("importance", ascending=True)
        fig3 = px.bar(fi_df, x="importance", y="feature", orientation="h",
                      color="importance", color_continuous_scale="Viridis")
        fig3.update_layout(template=PLOTLY_TEMPLATE, paper_bgcolor=DARK_BG, plot_bgcolor=DARK_BG)
        st.plotly_chart(fig3, use_container_width=True, key="mp_fi")

    st.markdown("### Model agreement rate")
    ag_df = pd.DataFrame({"domain": list(agreement.keys()),
                          "agreement_rate": list(agreement.values())})
    fig4 = px.bar(ag_df, x="domain", y="agreement_rate", color="agreement_rate",
                  color_continuous_scale="Greens",
                  title="Rate at which 2+ models agree on flagged points")
    fig4.update_layout(template=PLOTLY_TEMPLATE, paper_bgcolor=DARK_BG, plot_bgcolor=DARK_BG,
                       yaxis=dict(range=[0, 1]))
    st.plotly_chart(fig4, use_container_width=True, key="mp_agree")

    st.markdown("### Confusion matrix (ensemble vs ground truth)")
    df = fetch_dataset(chosen, limit=2000)
    if not df.empty and "true_anomaly" in df.columns:
        code, data, _ = api_post(f"/detect/{chosen}", df.to_dict(orient="records"))
        if code == 200:
            pred = pd.DataFrame(data["results"])["is_anomaly"].astype(int).values
            truth = df["true_anomaly"].astype(int).values
            tp = int(((pred == 1) & (truth == 1)).sum())
            tn = int(((pred == 0) & (truth == 0)).sum())
            fp = int(((pred == 1) & (truth == 0)).sum())
            fn = int(((pred == 0) & (truth == 1)).sum())
            cm = pd.DataFrame([[tn, fp], [fn, tp]],
                              index=["actual normal", "actual anomaly"],
                              columns=["pred normal", "pred anomaly"])
            fig5 = px.imshow(cm, text_auto=True, color_continuous_scale="Blues",
                             title=f"Confusion matrix — {chosen}")
            fig5.update_layout(template=PLOTLY_TEMPLATE, paper_bgcolor=DARK_BG, plot_bgcolor=DARK_BG)
            st.plotly_chart(fig5, use_container_width=True, key="mp_cm")


# ---------------------------------------------------------------------------
# Tab 7 — Anomaly Explorer
# ---------------------------------------------------------------------------
def tab_explorer(sb: Dict[str, Any]) -> None:
    st.subheader("Anomaly Explorer")
    hist = fetch_history(sb["domain"], sb["severity"], limit=500)
    if hist.empty:
        st.info("No anomalies match the current filters.")
        return
    if sb["entity_query"]:
        q = sb["entity_query"].lower()
        hist = hist[hist["entity"].str.lower().str.contains(q)]

    st.dataframe(hist, hide_index=True, use_container_width=True)

    st.markdown("### Detail")
    idx = st.number_input("Row index", min_value=0, max_value=max(0, len(hist) - 1), value=0, step=1)
    if not hist.empty:
        row = hist.iloc[int(idx)]
        st.markdown(
            f"**{row['entity']}**  ·  "
            f"<span class='severity-{row['severity_band']}'>{row['severity']:.0f}/100 ({row['severity_band']})</span>",
            unsafe_allow_html=True,
        )
        st.write(f"**Likely cause:** {row['likely_cause']}")
        st.json(row.get("record", {}))

    c1, c2 = st.columns(2)
    csv = hist.to_csv(index=False).encode("utf-8")
    c1.download_button("⬇ Download CSV", csv, file_name="anomalies.csv",
                       mime="text/csv", use_container_width=True)
    try:
        from io import BytesIO
        buf = BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            hist.drop(columns=["record"], errors="ignore").to_excel(w, index=False, sheet_name="anomalies")
        c2.download_button("⬇ Download Excel", buf.getvalue(),
                           file_name="anomalies.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           use_container_width=True)
    except Exception:  # noqa: BLE001
        c2.caption("(openpyxl not available for Excel export)")


# ---------------------------------------------------------------------------
# Tab 8 — Trend Analysis
# ---------------------------------------------------------------------------
def tab_trends() -> None:
    st.subheader("Trend Analysis")
    hist = fetch_history(None, 0, limit=500)
    if hist.empty:
        st.info("No anomalies yet — run detection first.")
        return
    hist["detected_at"] = pd.to_datetime(hist["detected_at"])
    hist["date"] = hist["detected_at"].dt.date.astype(str)
    hist["hour"] = hist["detected_at"].dt.hour
    hist["dow"] = hist["detected_at"].dt.day_name()

    per_day = hist.groupby(["date", "domain"]).size().reset_index(name="count")
    fig = px.area(per_day, x="date", y="count", color="domain",
                  title="Anomaly rate over time")
    fig.update_layout(template=PLOTLY_TEMPLATE, paper_bgcolor=DARK_BG, plot_bgcolor=DARK_BG)
    st.plotly_chart(fig, use_container_width=True, key="tr_rate")

    rolling = hist.groupby("date").size().reset_index(name="count")
    rolling["rolling7"] = rolling["count"].rolling(7, min_periods=1).mean()
    fig2 = px.line(rolling, x="date", y=["count", "rolling7"], title="Rolling 7-day anomaly count")
    fig2.update_layout(template=PLOTLY_TEMPLATE, paper_bgcolor=DARK_BG, plot_bgcolor=DARK_BG)
    st.plotly_chart(fig2, use_container_width=True, key="tr_roll")

    heat = hist.groupby(["dow", "hour"]).size().reset_index(name="count")
    fig3 = px.density_heatmap(heat, x="hour", y="dow", z="count",
                              color_continuous_scale="Inferno",
                              title="Anomalies by hour × day of week")
    fig3.update_layout(template=PLOTLY_TEMPLATE, paper_bgcolor=DARK_BG, plot_bgcolor=DARK_BG)
    st.plotly_chart(fig3, use_container_width=True, key="tr_heat")

    top = hist.groupby("entity").size().reset_index(name="count").sort_values("count", ascending=False).head(15)
    fig4 = px.bar(top, x="count", y="entity", orientation="h",
                  color="count", color_continuous_scale="Reds",
                  title="Most frequently anomalous entities")
    fig4.update_layout(template=PLOTLY_TEMPLATE, paper_bgcolor=DARK_BG, plot_bgcolor=DARK_BG)
    st.plotly_chart(fig4, use_container_width=True, key="tr_top")


# ---------------------------------------------------------------------------
# Tab 9 — API console
# ---------------------------------------------------------------------------
def tab_api_console() -> None:
    st.subheader("API Console")

    endpoints = {
        "GET /api/v1/status": ("GET", "/status", None,
                               "Status of trained models and history size."),
        "POST /api/v1/train": ("POST", "/train", {"domain": "all"},
                               "Retrain models. Body: {'domain': 'all'|domain}."),
        "POST /api/v1/detect/operators": ("POST", "/detect/operators", "<dataset:operators>",
                                          "Detect anomalies in operator shift records."),
        "POST /api/v1/detect/inventory": ("POST", "/detect/inventory", "<dataset:inventory>",
                                          "Detect anomalies in SKU daily records."),
        "POST /api/v1/detect/routes": ("POST", "/detect/routes", "<dataset:routes>",
                                       "Detect anomalies in picking routes."),
        "POST /api/v1/detect/deliveries": ("POST", "/detect/deliveries", "<dataset:deliveries>",
                                           "Detect anomalies in deliveries."),
        "POST /api/v1/stream/tick": ("POST", "/stream/tick", {"domain": "operators", "force_anomaly": False},
                                     "Simulate one real-time tick."),
        "GET /api/v1/anomalies/history": ("GET", "/anomalies/history", {"limit": 50},
                                          "Last detected anomalies (filterable)."),
        "GET /api/v1/anomalies/stats": ("GET", "/anomalies/stats", None,
                                        "Counts by domain + severity distribution."),
    }
    selected = st.selectbox("Endpoint", list(endpoints.keys()))
    method, path, default_body, doc = endpoints[selected]
    st.caption(doc)

    body_text = ""
    if method == "POST":
        if isinstance(default_body, str) and default_body.startswith("<dataset:"):
            domain = default_body.split(":")[1].rstrip(">")
            sample = fetch_dataset(domain, limit=5).to_dict(orient="records")
            body_text = json.dumps(sample, indent=2, default=str)
        elif default_body is not None:
            body_text = json.dumps(default_body, indent=2)
        body_text = st.text_area("Request body (JSON)", body_text, height=220)

    if st.button("📤 Send request", type="primary"):
        if method == "GET":
            code, data, ms = api_get(path)
        else:
            try:
                payload = json.loads(body_text) if body_text else None
            except json.JSONDecodeError as e:
                st.error(f"Invalid JSON: {e}")
                return
            code, data, ms = api_post(path, payload)
        c1, c2 = st.columns(2)
        c1.metric("Status", code)
        c2.metric("Response time", f"{ms:.0f} ms")
        st.json(data if isinstance(data, (dict, list)) else {"raw": data})


# ---------------------------------------------------------------------------
# Tab 10 — Real-time simulation
# ---------------------------------------------------------------------------
def tab_simulation() -> None:
    st.subheader("Real-time Simulation")
    domain = st.selectbox("Domain", ["operators", "inventory", "routes", "deliveries"], key="sim_dom")
    cols = st.columns(3)
    start = cols[0].button("▶ Start (10 ticks)", use_container_width=True)
    inject = cols[1].button("⚠ Inject anomaly", use_container_width=True)
    clear = cols[2].button("🧹 Clear buffer", use_container_width=True)

    if "sim_buffer" not in st.session_state:
        st.session_state.sim_buffer = []

    if clear:
        st.session_state.sim_buffer = []

    def _tick(force: bool) -> None:
        code, data, _ = api_post("/stream/tick", {"domain": domain, "force_anomaly": force})
        if code == 200:
            st.session_state.sim_buffer.append(data)

    if inject:
        _tick(force=True)
    if start:
        prog = st.progress(0)
        for i in range(10):
            _tick(force=False)
            prog.progress((i + 1) / 10)
            time.sleep(0.4)
        prog.empty()

    buf = st.session_state.sim_buffer
    if not buf:
        st.info("Click ▶ to stream synthetic data through the detector.")
        return

    last = buf[-1]
    klass = "bad" if last.get("is_anomaly") else "ok"
    st.markdown(metric_card("Last severity", f'{last["severity"]:.0f}/100', klass),
                unsafe_allow_html=True)
    if last.get("is_anomaly"):
        st.markdown(f'<div class="alert-banner">⚠ Anomaly detected — {last["explanation"]}</div>',
                    unsafe_allow_html=True)

    sev_df = pd.DataFrame([{"i": i, "severity": x["severity"], "anomaly": x["is_anomaly"]}
                           for i, x in enumerate(buf)])
    fig = px.line(sev_df, x="i", y="severity", title="Severity stream",
                  color_discrete_sequence=[OK])
    fig.add_scatter(x=sev_df[sev_df["anomaly"]]["i"], y=sev_df[sev_df["anomaly"]]["severity"],
                    mode="markers", marker=dict(color=BAD, size=12, symbol="x"), name="anomaly")
    fig.update_layout(template=PLOTLY_TEMPLATE, paper_bgcolor=DARK_BG, plot_bgcolor=DARK_BG)
    st.plotly_chart(fig, use_container_width=True, key="sim_line")

    st.markdown("### Stream log")
    log = pd.DataFrame([{
        "generated_at": x["generated_at"],
        "domain": x["domain"],
        "severity": x["severity"],
        "is_anomaly": x["is_anomaly"],
        "summary": (x.get("explanation") or "—")[:140],
    } for x in buf[::-1]])
    st.dataframe(log, hide_index=True, use_container_width=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    sb = sidebar()
    st.title("⚠️ Supply Chain Anomaly Detector")
    st.caption("Operators · Inventory · Picking Routes · Deliveries — Isolation Forest + LOF + DBSCAN ensemble")

    tabs = st.tabs([
        "🎯 Live Monitor", "👷 Operators", "📦 Inventory", "🛣️ Routes",
        "🚚 Deliveries", "🧪 Models", "🔎 Explorer", "📈 Trends",
        "🔌 API Console", "📡 Simulation",
    ])

    with tabs[0]:
        tab_live(sb)
    with tabs[1]:
        tab_operators()
    with tabs[2]:
        tab_inventory()
    with tabs[3]:
        tab_routes()
    with tabs[4]:
        tab_deliveries()
    with tabs[5]:
        tab_model_perf()
    with tabs[6]:
        tab_explorer(sb)
    with tabs[7]:
        tab_trends()
    with tabs[8]:
        tab_api_console()
    with tabs[9]:
        tab_simulation()

    if sb["auto_refresh"]:
        time.sleep(30)
        st.rerun()


if __name__ == "__main__":
    main()
