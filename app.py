import os
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from streamlit_option_menu import option_menu

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="E-Comersales",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------- SESSION STATE ----------------
if "df" not in st.session_state:
    st.session_state.df = None

# ================================================================
# DATA LOADING
# ================================================================
APP_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DATA_PATH = os.path.join(APP_DIR, "amazon_flipkart_sales_seasonal_3000_final.csv")


@st.cache_data(show_spinner=False)
def load_data(file):
    """Load either an uploaded file or the bundled sample dataset, and
    derive the helper columns the charts/insights rely on."""
    try:
        if file is not None:
            if file.name.lower().endswith((".xlsx", ".xls")):
                df = pd.read_excel(file)
            else:
                df = pd.read_csv(file)
        else:
            df = pd.read_csv(DEFAULT_DATA_PATH)
    except (FileNotFoundError, OSError):
        return None

    if "Day of order" in df.columns:
        df["Day of order"] = pd.to_datetime(df["Day of order"], errors="coerce")
        df["Month"] = df["Day of order"].dt.to_period("M").dt.to_timestamp()
        df["Year"] = df["Day of order"].dt.year
        df["Weekday"] = df["Day of order"].dt.day_name()
    if "Festival_Sale" in df.columns:
        df["Festival_Sale"] = df["Festival_Sale"].fillna("No Festival")
    return df


REQUIRED_COLUMNS = {
    "Platform", "prod_category", "act_price", "dis_price", "dis_percent",
    "Day of order", "State_", "cust_rating", "Festival_Sale", "mode_of_pay",
}

# ================================================================
# COLORS & STYLING HELPERS
# ================================================================
SEAGREEN = "#2E8B57"
BLUE = "#4FC3F7"
ORANGE = "#FF8C00"
PURPLE = "#BA68C8"
PALETTE = ["#2E8B57", "#4FC3F7", "#FF8C00", "#BA68C8", "#E57373",
           "#FFD54F", "#90A4AE", "#F06292", "#64B5F6", "#AED581"]
PLATFORM_COLORS = {"Amazon": SEAGREEN, "Flipkart": BLUE}
CARD_BG = "#1f1f1f"
GRID = "#333333"
TXT = "#e0e0e0"

# Wikimedia-hosted brand logos (public reference logos, loaded by URL)
AMAZON_LOGO_URL = "C:\\Users\\HARMANPREET SINGH\\Downloads\\amazon logo.png"
FLIPKART_LOGO_URL = "C:\\Users\\HARMANPREET SINGH\\Downloads\\flipkartlogo.svg"


def style_fig(fig, title, height=430):
    fig.update_layout(
        title=dict(text=title, font=dict(size=19, color=SEAGREEN, family="Arial Black"), x=0.02, xanchor="left"),
        paper_bgcolor=CARD_BG,
        plot_bgcolor=CARD_BG,
        font=dict(color=TXT, size=12),
        margin=dict(l=40, r=30, t=65, b=40),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=TXT, size=11)),
        height=height,
        hoverlabel=dict(bgcolor="#2b2b2b", font_color="#f5f5f5", font_size=12),
    )
    fig.update_xaxes(gridcolor=GRID, zerolinecolor=GRID, color=TXT, title_font=dict(size=13, color=TXT))
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=GRID, color=TXT, title_font=dict(size=13, color=TXT))
    fig.update_annotations(font=dict(color=TXT, size=13))
    return fig


def format_inr(value):
    if pd.isna(value):
        return "₹0"
    if value >= 1e7:
        return f"₹{value/1e7:.2f} Cr"
    elif value >= 1e5:
        return f"₹{value/1e5:.2f} L"
    elif value >= 1e3:
        return f"₹{value/1e3:.1f} K"
    return f"₹{value:,.0f}"


def join_natural(items):
    items = list(items)
    if not items:
        return "none"
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def leader_badge(amz_val, flp_val):
    """Returns (badge_html, leader_name, margin_pct) comparing Amazon vs Flipkart."""
    if amz_val == flp_val:
        return '<span class="leader-badge badge-tied">🤝 Dead heat</span>', "Tied", 0.0
    leader = "Amazon" if amz_val > flp_val else "Flipkart"
    lo, hi = min(amz_val, flp_val), max(amz_val, flp_val)
    margin = (hi - lo) / lo * 100 if lo != 0 else 100.0
    cls = "badge-amazon" if leader == "Amazon" else "badge-flipkart"
    qualifier = "narrowly " if margin < 3 else ""
    html = f'<span class="leader-badge {cls}">🏆 {leader} {qualifier}leads (+{margin:.1f}%)</span>'
    return html, leader, margin


# ================================================================
# CHART BUILDER FUNCTIONS — 15 charts, all Amazon vs Flipkart focused
# ================================================================

# 1. Platform Overview — Revenue Share & Order Volume (pie + bar combo)
def chart_platform_overview(df):
    p = df.groupby("Platform").agg(Revenue=("dis_price", "sum"), Orders=("prod_id", "count")).reindex(["Amazon", "Flipkart"]).reset_index()
    colors = [PLATFORM_COLORS.get(pl, "#888") for pl in p["Platform"]]
    fig = make_subplots(rows=1, cols=2, specs=[[{"type": "domain"}, {"type": "xy"}]],
                         subplot_titles=("Revenue Share", "Order Volume"))
    fig.add_trace(go.Pie(labels=p["Platform"], values=p["Revenue"], hole=0.55, marker=dict(colors=colors),
                          textfont=dict(color="#0d0d0d", size=13),
                          hovertemplate="%{label}<br>₹%{value:,.0f} (%{percent})<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Bar(x=p["Platform"], y=p["Orders"], marker_color=colors, showlegend=False,
                          text=p["Orders"], texttemplate="%{text:,}", textposition="outside",
                          hovertemplate="%{x}<br>%{y:,} orders<extra></extra>"), row=1, col=2)
    fig.update_yaxes(title_text="Orders", row=1, col=2)
    return style_fig(fig, "🛍️ Platform Overview — Revenue Share & Order Volume", height=400)


# 2. Platform Performance Radar (5 normalized metrics)
def chart_performance_radar(df):
    grp = df.groupby("Platform")
    metric_series = {
        "Revenue": grp["dis_price"].sum(),
        "Orders": grp["prod_id"].count(),
        "Avg Order Value": grp["dis_price"].mean(),
        "Avg Rating": grp["cust_rating"].mean(),
        "Avg Discount %": grp["dis_percent"].mean(),
    }
    labels, amz_vals, flp_vals = [], [], []
    for name, s in metric_series.items():
        a, f = s.get("Amazon", 0), s.get("Flipkart", 0)
        mx = max(a, f) if max(a, f) > 0 else 1
        labels.append(name)
        amz_vals.append(round(a / mx * 100, 1))
        flp_vals.append(round(f / mx * 100, 1))
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=amz_vals + [amz_vals[0]], theta=labels + [labels[0]], name="Amazon",
                                   line=dict(color=SEAGREEN, width=2), fillcolor="rgba(46,139,87,0.25)", fill="toself"))
    fig.add_trace(go.Scatterpolar(r=flp_vals + [flp_vals[0]], theta=labels + [labels[0]], name="Flipkart",
                                   line=dict(color=BLUE, width=2), fillcolor="rgba(79,195,247,0.25)", fill="toself"))
    fig.update_layout(polar=dict(bgcolor=CARD_BG,
                                  radialaxis=dict(visible=True, range=[0, 100], gridcolor=GRID, color=TXT, showticklabels=False),
                                  angularaxis=dict(gridcolor=GRID, color=TXT, tickfont=dict(size=12))))
    return style_fig(fig, "📡 Platform Performance Radar (relative scale)", height=440)


# 3. Monthly Revenue Trend — Amazon vs Flipkart
def chart_monthly_revenue(df):
    m = df.groupby(["Month", "Platform"])["dis_price"].sum().reset_index()
    fig = go.Figure()
    for plat in ["Amazon", "Flipkart"]:
        d = m[m["Platform"] == plat]
        fig.add_trace(go.Scatter(x=d["Month"], y=d["dis_price"], name=plat, mode="lines+markers",
                                  line=dict(color=PLATFORM_COLORS[plat], width=3), marker=dict(size=5),
                                  hovertemplate="%{x|%b %Y}<br>₹%{y:,.0f}<extra>" + plat + "</extra>"))
    fig.update_xaxes(title_text="Month", nticks=12, tickformat="%b %Y")
    fig.update_yaxes(title_text="Revenue (₹)")
    return style_fig(fig, "📈 Monthly Revenue Trend — Amazon vs Flipkart", height=430)


# 4. Monthly Order Volume Trend — Amazon vs Flipkart
def chart_monthly_orders(df):
    m = df.groupby(["Month", "Platform"])["prod_id"].count().reset_index(name="Orders")
    fig = go.Figure()
    for plat in ["Amazon", "Flipkart"]:
        d = m[m["Platform"] == plat]
        fig.add_trace(go.Scatter(x=d["Month"], y=d["Orders"], name=plat, mode="lines+markers",
                                  line=dict(color=PLATFORM_COLORS[plat], width=3, dash="dot" if plat == "Flipkart" else "solid"),
                                  marker=dict(size=5),
                                  hovertemplate="%{x|%b %Y}<br>%{y} orders<extra>" + plat + "</extra>"))
    fig.update_xaxes(title_text="Month", nticks=12, tickformat="%b %Y")
    fig.update_yaxes(title_text="Orders")
    return style_fig(fig, "📦 Monthly Order Volume Trend — Amazon vs Flipkart", height=430)


# 5. Revenue by Day of the Week — Amazon vs Flipkart
def chart_weekday_comparison(df):
    order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    w = df.groupby(["Weekday", "Platform"])["dis_price"].sum().reset_index()
    fig = px.bar(w, x="Weekday", y="dis_price", color="Platform", barmode="group",
                 category_orders={"Weekday": order}, color_discrete_map=PLATFORM_COLORS)
    fig.update_traces(hovertemplate="%{x} — %{fullData.name}<br>₹%{y:,.0f}<extra></extra>")
    fig.update_xaxes(title_text="")
    fig.update_yaxes(title_text="Revenue (₹)")
    return style_fig(fig, "📅 Revenue by Day of the Week — Amazon vs Flipkart", height=420)


# 6. Festival Sale Performance — Amazon vs Flipkart
def chart_festival_comparison(df):
    order = ["No Festival", "GIF", "BBD", "BF"]
    f = df.groupby(["Festival_Sale", "Platform"])["prod_id"].count().reset_index(name="Orders")
    fig = px.bar(f, x="Festival_Sale", y="Orders", color="Platform", barmode="group",
                 category_orders={"Festival_Sale": order}, color_discrete_map=PLATFORM_COLORS)
    fig.update_traces(hovertemplate="%{x} — %{fullData.name}<br>%{y:,} orders<extra></extra>")
    fig.update_xaxes(title_text="")
    fig.update_yaxes(title_text="Orders")
    return style_fig(fig, "🎉 Festival Sale Performance — Amazon vs Flipkart", height=420)


# 7. Revenue & Orders by Category — Amazon vs Flipkart (combo: 2 subplots)
def chart_category_revenue_orders(df):
    cat = df.groupby(["prod_category", "Platform"]).agg(Revenue=("dis_price", "sum"), Orders=("prod_id", "count")).reset_index()
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Revenue by Category", "Orders by Category"), shared_yaxes=False)
    for plat in ["Amazon", "Flipkart"]:
        d = cat[cat["Platform"] == plat]
        fig.add_trace(go.Bar(x=d["prod_category"], y=d["Revenue"], name=plat, marker_color=PLATFORM_COLORS[plat],
                              legendgroup=plat, hovertemplate="%{x}<br>₹%{y:,.0f}<extra>" + plat + "</extra>"), row=1, col=1)
        fig.add_trace(go.Bar(x=d["prod_category"], y=d["Orders"], name=plat, marker_color=PLATFORM_COLORS[plat],
                              legendgroup=plat, showlegend=False, hovertemplate="%{x}<br>%{y} orders<extra>" + plat + "</extra>"), row=1, col=2)
    fig.update_layout(barmode="group")
    fig.update_xaxes(tickangle=-30)
    fig.update_yaxes(title_text="Revenue (₹)", row=1, col=1)
    fig.update_yaxes(title_text="Orders", row=1, col=2)
    return style_fig(fig, "🏬 Revenue & Orders by Category — Amazon vs Flipkart", height=460)


# 8. Category Leadership — Revenue Difference (diverging bar)
def chart_category_leadership(df):
    cp = df.groupby(["prod_category", "Platform"])["dis_price"].sum().unstack(fill_value=0)
    if "Amazon" not in cp.columns:
        cp["Amazon"] = 0
    if "Flipkart" not in cp.columns:
        cp["Flipkart"] = 0
    cp["diff"] = cp["Amazon"] - cp["Flipkart"]
    cp = cp.sort_values("diff")
    colors = [SEAGREEN if v >= 0 else BLUE for v in cp["diff"]]
    fig = go.Figure(go.Bar(
        x=cp["diff"], y=cp.index, orientation="h", marker_color=colors,
        hovertemplate="<b>%{y}</b><br>Amazon − Flipkart: ₹%{x:,.0f}<extra></extra>"))
    fig.add_vline(x=0, line_color=GRID, line_width=1)
    fig.update_xaxes(title_text="Revenue Difference (₹) — Amazon leads right, Flipkart leads left")
    fig.update_yaxes(title_text="")
    return style_fig(fig, "⚖️ Category Leadership — Who Wins Each Category", height=460)


# 9. Category Mix — Amazon vs Flipkart (2 pies side by side)
def chart_category_mix(df, category_colors):
    cm = df.groupby(["Platform", "prod_category"])["dis_price"].sum().reset_index()
    amz, flp = cm[cm["Platform"] == "Amazon"], cm[cm["Platform"] == "Flipkart"]
    fig = make_subplots(rows=1, cols=2, specs=[[{"type": "domain"}, {"type": "domain"}]],
                         subplot_titles=("Amazon's Category Mix", "Flipkart's Category Mix"))
    fig.add_trace(go.Pie(labels=amz["prod_category"], values=amz["dis_price"], hole=0.4,
                          marker=dict(colors=[category_colors.get(c, "#888") for c in amz["prod_category"]]),
                          textfont=dict(color="#0d0d0d", size=10), textposition="inside",
                          hovertemplate="%{label}<br>₹%{value:,.0f} (%{percent})<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Pie(labels=flp["prod_category"], values=flp["dis_price"], hole=0.4,
                          marker=dict(colors=[category_colors.get(c, "#888") for c in flp["prod_category"]]),
                          textfont=dict(color="#0d0d0d", size=10), textposition="inside",
                          hovertemplate="%{label}<br>₹%{value:,.0f} (%{percent})<extra></extra>"), row=1, col=2)
    return style_fig(fig, "🧩 Category Mix — Where Each Platform's Revenue Comes From", height=440)


# 10. Average Discount % by Category — Amazon vs Flipkart
def chart_discount_by_category(df):
    d = df.groupby(["prod_category", "Platform"])["dis_percent"].mean().reset_index()
    fig = px.bar(d, x="prod_category", y="dis_percent", color="Platform", barmode="group",
                 color_discrete_map=PLATFORM_COLORS)
    fig.update_traces(hovertemplate="%{x} — %{fullData.name}<br>Avg Discount: %{y:.1f}%<extra></extra>")
    fig.update_xaxes(title_text="", tickangle=-30)
    fig.update_yaxes(title_text="Avg Discount %")
    return style_fig(fig, "🏷️ Average Discount % by Category — Amazon vs Flipkart", height=440)


# 11. Price & Discount Distribution — Amazon vs Flipkart (combo: 2 box plots)
def chart_price_discount_distribution(df):
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Price Distribution", "Discount % Distribution"))
    for plat in ["Amazon", "Flipkart"]:
        d = df[df["Platform"] == plat]
        fig.add_trace(go.Box(y=d["act_price"], name=plat, marker_color=PLATFORM_COLORS[plat],
                              legendgroup=plat, showlegend=True), row=1, col=1)
        fig.add_trace(go.Box(y=d["dis_percent"], name=plat, marker_color=PLATFORM_COLORS[plat],
                              legendgroup=plat, showlegend=False), row=1, col=2)
    fig.update_yaxes(title_text="Actual Price (₹)", row=1, col=1)
    fig.update_yaxes(title_text="Discount %", row=1, col=2)
    return style_fig(fig, "💰 Price & Discount Distribution — Amazon vs Flipkart", height=440)


# 12. Price vs Discount Relationship — Amazon vs Flipkart (scatter)
def chart_price_discount_scatter(df):
    sample = df.sample(min(1200, len(df)), random_state=42) if len(df) > 1200 else df
    fig = px.scatter(sample, x="act_price", y="dis_percent", color="Platform",
                      color_discrete_map=PLATFORM_COLORS, opacity=0.55)
    fig.update_traces(marker=dict(size=6), hovertemplate="Price: ₹%{x:,.0f}<br>Discount: %{y}%<extra>%{fullData.name}</extra>")
    fig.update_xaxes(title_text="Actual Price (₹)")
    fig.update_yaxes(title_text="Discount %")
    return style_fig(fig, "🔎 Price vs Discount Relationship — Amazon vs Flipkart", height=440)


# 13. Payment Method Mix — Amazon vs Flipkart (2 pies)
def chart_payment_mix(df):
    pm = df.groupby(["Platform", "mode_of_pay"])["prod_id"].count().reset_index(name="Count")
    amz, flp = pm[pm["Platform"] == "Amazon"], pm[pm["Platform"] == "Flipkart"]
    fig = make_subplots(rows=1, cols=2, specs=[[{"type": "domain"}, {"type": "domain"}]],
                         subplot_titles=("Amazon", "Flipkart"))
    fig.add_trace(go.Pie(labels=amz["mode_of_pay"], values=amz["Count"], hole=0.45, marker=dict(colors=PALETTE),
                          textfont=dict(color="#0d0d0d", size=11),
                          hovertemplate="%{label}<br>%{value:,} orders (%{percent})<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Pie(labels=flp["mode_of_pay"], values=flp["Count"], hole=0.45, marker=dict(colors=PALETTE),
                          textfont=dict(color="#0d0d0d", size=11),
                          hovertemplate="%{label}<br>%{value:,} orders (%{percent})<extra></extra>"), row=1, col=2)
    return style_fig(fig, "💳 Payment Method Mix — Amazon vs Flipkart", height=440)


# 14. Customer Rating Distribution — Amazon vs Flipkart
def chart_rating_comparison(df):
    r = df.groupby(["cust_rating", "Platform"]).size().reset_index(name="Count")
    fig = px.bar(r, x="cust_rating", y="Count", color="Platform", barmode="group",
                 color_discrete_map=PLATFORM_COLORS)
    fig.update_traces(hovertemplate="%{x} star — %{fullData.name}<br>%{y:,} orders<extra></extra>")
    fig.update_xaxes(title_text="Rating (stars)", dtick=1)
    fig.update_yaxes(title_text="Orders")
    return style_fig(fig, "⭐ Customer Rating Distribution — Amazon vs Flipkart", height=420)


# 15. Top 10 States by Revenue — Amazon vs Flipkart (grouped horizontal bar)
def chart_state_comparison(df):
    total_by_state = df.groupby("State_")["dis_price"].sum().sort_values(ascending=False)
    top_states = total_by_state.head(10).index.tolist()
    s = df[df["State_"].isin(top_states)].groupby(["State_", "Platform"])["dis_price"].sum().reset_index()
    fig = px.bar(s, x="dis_price", y="State_", color="Platform", orientation="h", barmode="group",
                 category_orders={"State_": top_states[::-1]}, color_discrete_map=PLATFORM_COLORS)
    fig.update_traces(hovertemplate="%{y} — %{fullData.name}<br>₹%{x:,.0f}<extra></extra>")
    fig.update_xaxes(title_text="Revenue (₹)")
    fig.update_yaxes(title_text="")
    return style_fig(fig, "🌍 Top 10 States by Revenue — Amazon vs Flipkart", height=480)


# ---------------- CUSTOM CSS ----------------
st.markdown("""
    <style>
        html, body {
            margin: 0;
            padding: 0;
        }

        .stApp {
            background: linear-gradient(180deg, #2b2b2b 0%, #0d0d0d 100%);
            color: #f5f5f5;
            min-height: 100vh;
        }

        header[data-testid="stHeader"] {
            background: transparent;
        }

        .block-container {
            padding-top: 2.5rem;
            padding-bottom: 2rem;
            padding-left: 3rem;
            padding-right: 3rem;
            max-width: 100%;
        }

        section[data-testid="stSidebar"] {
            background-color: #1a1a1a;
            border-right: 1px solid #3a3a3a;
        }

        section[data-testid="stSidebar"] > div {
            background-color: #1a1a1a;
        }

        .sidebar-title {
            text-align: center;
            font-size: 1.8rem;
            font-weight: 800;
            color: #2E8B57;
            padding-top: 20px;
            padding-bottom: 10px;
            text-shadow: 1px 1px 4px rgba(0,0,0,0.6);
        }

        .sidebar-divider {
            border: none;
            border-top: 1px solid #3a3a3a;
            margin: 0px 10px 15px 10px;
        }

        /* Main title at the top of every page */
        .page-title {
            text-align: center;
            font-size: 2.6rem;
            font-weight: 800;
            color: #2E8B57;
            margin-bottom: 5px;
            text-shadow: 2px 2px 6px rgba(0,0,0,0.6);
        }

        .page-subtitle {
            text-align: center;
            font-size: 1.05rem;
            color: #cccccc;
            margin-bottom: 25px;
        }

        /* Solid, visible-color section headings used across pages */
        .section-heading-lg {
            font-size: 1.9rem;
            font-weight: 800;
            color: #2E8B57;
            margin-top: 10px;
            margin-bottom: 12px;
        }

        .section-heading-sm {
            font-size: 1.25rem;
            font-weight: 700;
            color: #2E8B57;
            margin-top: 8px;
            margin-bottom: 8px;
        }

        .section-heading-alt {
            font-size: 1.25rem;
            font-weight: 700;
            color: #4FC3F7;
            margin-top: 8px;
            margin-bottom: 8px;
        }

        .info-card {
            background-color: #1f1f1f;
            border: 1px solid #3a3a3a;
            border-radius: 12px;
            padding: 25px;
            margin: 10px 0px;
            box-shadow: 0px 4px 10px rgba(0,0,0,0.4);
        }

        .info-card h3 {
            color: #2E8B57;
        }

        .info-card p, .info-card li {
            color: #e0e0e0;
            line-height: 1.6;
        }

        .kpi-card {
            background-color: #1f1f1f;
            border: 1px solid #3a3a3a;
            border-left: 4px solid #2E8B57;
            border-radius: 10px;
            padding: 14px 16px;
            text-align: center;
            box-shadow: 0px 4px 10px rgba(0,0,0,0.35);
            margin-bottom: 10px;
        }
        .kpi-value {
            font-size: 1.5rem;
            font-weight: 800;
            color: #2E8B57;
        }
        .kpi-label {
            font-size: 0.78rem;
            color: #aaaaaa;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .kpi-split {
            font-size: 0.95rem;
            color: #e0e0e0;
            margin-top: 4px;
        }
        .kpi-split b.amz { color: #2E8B57; }
        .kpi-split b.flp { color: #4FC3F7; }

        /* Leader badges used on the Insights page */
        .leader-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 14px;
            font-size: 0.78rem;
            font-weight: 700;
            margin-top: 8px;
        }
        .badge-amazon { background-color: rgba(46,139,87,0.18); color: #3CB371; border: 1px solid #2E8B57; }
        .badge-flipkart { background-color: rgba(79,195,247,0.18); color: #4FC3F7; border: 1px solid #4FC3F7; }
        .badge-tied { background-color: rgba(170,170,170,0.18); color: #cccccc; border: 1px solid #888888; }

        div[data-testid="stPlotlyChart"] {
            background-color: #1f1f1f;
            border: 1px solid #3a3a3a;
            border-radius: 12px;
            padding: 8px;
            box-shadow: 0px 4px 10px rgba(0,0,0,0.4);
            margin-bottom: 18px;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 6px;
        }
        .stTabs [data-baseweb="tab"] {
            background-color: #1a1a1a;
            border-radius: 8px 8px 0 0;
            padding: 10px 16px;
            color: #cccccc;
            font-size: 14px;
        }
        .stTabs [aria-selected="true"] {
            background-color: #2E8B57 !important;
            color: #ffffff !important;
            font-weight: 700;
        }

        div[data-testid="stMetric"] {
            background-color: #1f1f1f;
            border: 1px solid #3a3a3a;
            border-radius: 10px;
            padding: 10px;
        }

        footer {visibility: hidden;}
        #MainMenu {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# ---------------- SIDEBAR: TITLE, DIVIDER, THEN NAV ----------------
with st.sidebar:
    st.markdown('<div class="sidebar-title">🛒 E-Comersales</div>', unsafe_allow_html=True)
    st.markdown('<hr class="sidebar-divider">', unsafe_allow_html=True)

    selected = option_menu(
        menu_title=None,
        options=["Home", "Upload Dataset", "Data Visualisation", "Insights and Trends"],
        icons=["house", "cloud-upload", "bar-chart-line", "lightbulb"],
        orientation="vertical",
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "#1a1a1a"},
            "icon": {"color": "#2E8B57", "font-size": "18px"},
            "nav-link": {
                "font-size": "16px",
                "text-align": "left",
                "margin": "4px 0px",
                "color": "#f5f5f5",
                "padding": "12px",
                "border-radius": "8px",
                "--hover-color": "#333333",
            },
            "nav-link-selected": {"background-color": "#2E8B57", "color": "#ffffff", "font-weight": "700"},
        }
    )


def show_page_title():
    st.markdown('<div class="page-title">E-Comersales</div>', unsafe_allow_html=True)


# ================================================================
# PAGE: HOME
# ================================================================
if selected == "Home":
    show_page_title()
    st.markdown('<div class="page-subtitle">Your all-in-one E-Commerce Sales Analytics Dashboard</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-heading-lg">📊 Project Introduction</div>', unsafe_allow_html=True)
    st.markdown("""
        <div class="info-card">
            <p><b>E-Comersales</b> is a sales analytics project built around one central question:
            when it comes to India's e-commerce space, how do <b>Amazon</b> and <b>Flipkart</b> actually
            compare? Using order-level data spanning <b>2024–2026</b> across <b>10 product categories</b>
            and <b>33 states</b>, this dashboard puts the two platforms side by side on revenue, pricing,
            discounts, customer ratings, and regional performance.</p>
        </div>
    """, unsafe_allow_html=True)

    logo_col1, logo_col2, logo_col3 = st.columns([1, 1, 1])
    with logo_col1:
        st.image(AMAZON_LOGO_URL, width=260)
    with logo_col3:
        st.image(FLIPKART_LOGO_URL, width=260)

    st.markdown("""
        <div class="info-card">
            <p>Every chart and insight in this project is built to answer the same underlying question
            from a different angle — <i>who's winning, where, and why</i> — so the comparison stays the
            throughline from the raw data all the way to the final takeaways.</p>
        </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-heading-sm">🎯 What This Dashboard Answers</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
            <div class="info-card">
                <h3>🆚 Amazon vs Flipkart</h3>
                <p>Which platform generates more revenue and orders, which categories each one
                dominates, and how pricing and discounting behavior differs between them.</p>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
            <div class="info-card">
                <h3>🎉 Festival Sale Impact</h3>
                <p>Whether events like GIF and BBD genuinely drive higher order volumes and deeper
                discounts on each platform, or whether the effect is smaller than expected.</p>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("""
        <div class="info-card">
            <h3>🔑 Key Features</h3>
            <p>✔️ Upload your own Amazon/Flipkart-style sales data (CSV/Excel)<br>
            ✔️ 15 interactive Plotly charts, all built around the platform comparison<br>
            ✔️ Automatically generated insights and trends<br>
            ✔️ Clean, dark-themed dashboard UI</p>
        </div>
    """, unsafe_allow_html=True)

# ================================================================
# PAGE: UPLOAD DATASET
# ================================================================
elif selected == "Upload Dataset":
    show_page_title()
    st.markdown('<div class="page-subtitle">Import your own sales data to power the dashboard</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-heading-sm">📁 Upload Dataset</div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Upload your sales data (CSV or Excel)", type=["csv", "xlsx"])

    if uploaded_file:
        new_df = load_data(uploaded_file)
        if new_df is not None:
            st.session_state.df = new_df
            st.success(f"File '{uploaded_file.name}' uploaded successfully — {len(new_df):,} rows loaded.")
        else:
            st.error("Could not read that file. Please check the format and try again.")

    active_df = st.session_state.df if st.session_state.df is not None else load_data(None)

    if active_df is None:
        st.info("No dataset available yet — upload a CSV or Excel file above to get started.")
    else:
        if st.session_state.df is None:
            st.info("Showing the bundled sample dataset (`amazon_flipkart_sales_seasonal_3000_final.csv`). "
                    "Upload your own file above to replace it.")

        df = active_df
        n_rows_total = len(df)
        n_cols_total = df.shape[1]
        n_duplicates = int(df.duplicated().sum())
        n_missing = int(df.isna().sum().sum())

        st.markdown('<div class="section-heading-sm">📋 Dataset Summary</div>', unsafe_allow_html=True)
        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.markdown(f'<div class="kpi-card"><div class="kpi-value">{n_rows_total:,}</div>'
                        f'<div class="kpi-label">Rows</div></div>', unsafe_allow_html=True)
        with k2:
            st.markdown(f'<div class="kpi-card"><div class="kpi-value">{n_cols_total}</div>'
                        f'<div class="kpi-label">Columns</div></div>', unsafe_allow_html=True)
        with k3:
            st.markdown(f'<div class="kpi-card"><div class="kpi-value">{n_duplicates:,}</div>'
                        f'<div class="kpi-label">Duplicate Rows</div></div>', unsafe_allow_html=True)
        with k4:
            st.markdown(f'<div class="kpi-card"><div class="kpi-value">{n_missing:,}</div>'
                        f'<div class="kpi-label">Missing Values</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-heading-sm">📄 Dataset</div>', unsafe_allow_html=True)

        slider_max = max(n_rows_total, 1)
        default_rows = min(20, slider_max)
        n_rows = st.slider("Rows to preview", min_value=1, max_value=slider_max, value=default_rows)

        tab1, tab2, tab3 = st.tabs(["🔍 Preview", "🧬 Column Info", "🔢 Value Counts"])

        with tab1:
            st.dataframe(df.head(n_rows), width="stretch")

        with tab2:
            col_info = pd.DataFrame({
                "Column": df.columns,
                "Data Type": df.dtypes.astype(str).values,
                "Non-Null Count": df.notna().sum().values,
                "Null Count": df.isna().sum().values,
                "Unique Values": [df[c].nunique() for c in df.columns],
            })
            st.dataframe(col_info, width="stretch", hide_index=True)

        with tab3:
            default_col = "Platform" if "Platform" in df.columns else df.columns[0]
            vc_col = st.selectbox("Choose a column", options=df.columns.tolist(),
                                   index=df.columns.tolist().index(default_col))
            vc = df[vc_col].value_counts().reset_index()
            vc.columns = [vc_col, "Count"]
            st.dataframe(vc, width="stretch", hide_index=True)

            if df[vc_col].nunique() <= 40:
                vc_chart = vc.head(20).sort_values("Count")
                fig_vc = go.Figure(go.Bar(x=vc_chart["Count"], y=vc_chart[vc_col].astype(str), orientation="h",
                                           marker_color=SEAGREEN))
                fig_vc.update_xaxes(title_text="Count")
                fig_vc.update_yaxes(title_text="")
                st.plotly_chart(style_fig(fig_vc, f"Value Counts — {vc_col}", height=min(500, 100 + 28 * len(vc_chart))), width="stretch")
            else:
                st.caption(f"'{vc_col}' has {df[vc_col].nunique():,} unique values — too many to chart, showing the table above instead.")

# ================================================================
# PAGE: DATA VISUALISATION
# ================================================================
elif selected == "Data Visualisation":
    show_page_title()
    st.markdown('<div class="page-subtitle">Amazon vs Flipkart — 15 charts comparing the two platforms</div>', unsafe_allow_html=True)

    df = st.session_state.df if st.session_state.df is not None else load_data(None)

    if df is None:
        st.warning("The bundled sample dataset couldn't be found next to this script.")
        st.caption("Make sure `amazon_flipkart_sales_seasonal_3000_final.csv` sits in the same folder as this app, "
                    "or upload a file on the Upload Dataset page.")
    else:
        missing = REQUIRED_COLUMNS - set(df.columns)
        if missing:
            st.error("This dataset is missing columns the charts need: " + ", ".join(sorted(missing)))
        elif not {"Amazon", "Flipkart"}.issubset(set(df["Platform"].dropna().unique())):
            st.error("This page compares Amazon vs Flipkart specifically, but the loaded dataset's "
                     "'Platform' column doesn't contain both. Upload a dataset with both platforms present.")
        else:
            st.markdown('<div class="section-heading-sm">🔍 Filters</div>', unsafe_allow_html=True)
            fcol1, fcol2 = st.columns(2)
            with fcol1:
                category_opts = sorted(df["prod_category"].dropna().unique().tolist())
                category_filter = st.multiselect("Category", options=category_opts, default=category_opts, key="viz_category_filter")
            with fcol2:
                year_opts = sorted(df["Year"].dropna().unique().tolist())
                year_filter = st.multiselect("Year", options=year_opts, default=year_opts, key="viz_year_filter")

            df_f = df[df["prod_category"].isin(category_filter) & df["Year"].isin(year_filter)]
            if df_f.empty or not {"Amazon", "Flipkart"}.issubset(set(df_f["Platform"].unique())):
                st.warning("Selected filters leave one platform with no data — showing the full dataset instead.")
                df_f = df

            category_colors = {cat: PALETTE[i % len(PALETTE)] for i, cat in enumerate(sorted(df["prod_category"].dropna().unique()))}

            amz_f = df_f[df_f["Platform"] == "Amazon"]
            flp_f = df_f[df_f["Platform"] == "Flipkart"]

            k1, k2, k3, k4 = st.columns(4)
            with k1:
                st.markdown(f'<div class="kpi-card"><div class="kpi-value">{format_inr(df_f["dis_price"].sum())}</div>'
                            f'<div class="kpi-label">Total Revenue</div>'
                            f'<div class="kpi-split"><b class="amz">{format_inr(amz_f["dis_price"].sum())}</b> · '
                            f'<b class="flp">{format_inr(flp_f["dis_price"].sum())}</b></div></div>', unsafe_allow_html=True)
            with k2:
                st.markdown(f'<div class="kpi-card"><div class="kpi-value">{len(df_f):,}</div>'
                            f'<div class="kpi-label">Total Orders</div>'
                            f'<div class="kpi-split"><b class="amz">{len(amz_f):,}</b> · '
                            f'<b class="flp">{len(flp_f):,}</b></div></div>', unsafe_allow_html=True)
            with k3:
                st.markdown(f'<div class="kpi-card"><div class="kpi-value">{format_inr(df_f["dis_price"].mean())}</div>'
                            f'<div class="kpi-label">Avg Order Value</div>'
                            f'<div class="kpi-split"><b class="amz">{format_inr(amz_f["dis_price"].mean())}</b> · '
                            f'<b class="flp">{format_inr(flp_f["dis_price"].mean())}</b></div></div>', unsafe_allow_html=True)
            with k4:
                st.markdown(f'<div class="kpi-card"><div class="kpi-value">{df_f["cust_rating"].mean():.2f} ⭐</div>'
                            f'<div class="kpi-label">Avg Rating</div>'
                            f'<div class="kpi-split"><b class="amz">{amz_f["cust_rating"].mean():.2f}</b> · '
                            f'<b class="flp">{flp_f["cust_rating"].mean():.2f}</b></div></div>', unsafe_allow_html=True)
            st.caption("🟢 Amazon · 🔵 Flipkart")

            st.markdown("<br>", unsafe_allow_html=True)

            tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
                "📊 Overview", "📈 Trends", "🏬 Category", "💰 Pricing & Discounts", "💳 Customers & Payments", "🌍 Geography"
            ])

            with tab1:
                st.caption("A snapshot of how the two platforms stack up overall.")
                st.plotly_chart(chart_platform_overview(df_f), width="stretch")
                st.plotly_chart(chart_performance_radar(df_f), width="stretch")

            with tab2:
                st.caption("Revenue and order trends over time, weekdays, and festival sales.")
                st.plotly_chart(chart_monthly_revenue(df_f), width="stretch")
                st.plotly_chart(chart_monthly_orders(df_f), width="stretch")
                c1, c2 = st.columns(2)
                with c1:
                    st.plotly_chart(chart_weekday_comparison(df_f), width="stretch")
                with c2:
                    st.plotly_chart(chart_festival_comparison(df_f), width="stretch")

            with tab3:
                st.caption("Which platform wins which categories, and how their product mix differs.")
                st.plotly_chart(chart_category_revenue_orders(df_f), width="stretch")
                st.plotly_chart(chart_category_leadership(df_f), width="stretch")
                st.plotly_chart(chart_category_mix(df_f, category_colors), width="stretch")

            with tab4:
                st.caption("How pricing and discounting behavior compares across platforms.")
                st.plotly_chart(chart_discount_by_category(df_f), width="stretch")
                st.plotly_chart(chart_price_discount_distribution(df_f), width="stretch")
                st.plotly_chart(chart_price_discount_scatter(df_f), width="stretch")

            with tab5:
                st.caption("How customers pay, and how they rate their purchases, on each platform.")
                st.plotly_chart(chart_payment_mix(df_f), width="stretch")
                st.plotly_chart(chart_rating_comparison(df_f), width="stretch")

            with tab6:
                st.caption("Where each platform's revenue comes from across India.")
                st.plotly_chart(chart_state_comparison(df_f), width="stretch")

# ================================================================
# PAGE: INSIGHTS AND TRENDS
# ================================================================
elif selected == "Insights and Trends":
    show_page_title()
    st.markdown('<div class="page-subtitle">Automatically generated insights — Amazon vs Flipkart</div>', unsafe_allow_html=True)

    df = st.session_state.df if st.session_state.df is not None else load_data(None)

    if df is None:
        st.warning("The bundled sample dataset couldn't be found next to this script.")
        st.caption("Upload a file on the Upload Dataset page to generate insights.")
    else:
        missing = REQUIRED_COLUMNS - set(df.columns)
        if missing:
            st.error("This dataset is missing columns needed for insights: " + ", ".join(sorted(missing)))
        elif not {"Amazon", "Flipkart"}.issubset(set(df["Platform"].dropna().unique())):
            st.error("Insights compare Amazon vs Flipkart specifically, but the loaded dataset's "
                     "'Platform' column doesn't contain both.")
        else:
            amz = df[df["Platform"] == "Amazon"]
            flp = df[df["Platform"] == "Flipkart"]

            # ---------- Head-to-Head Scorecard ----------
            st.markdown('<div class="section-heading-lg">🏆 Head-to-Head Scorecard</div>', unsafe_allow_html=True)

            rev_badge, rev_leader, rev_margin = leader_badge(amz["dis_price"].sum(), flp["dis_price"].sum())
            ord_badge, ord_leader, ord_margin = leader_badge(len(amz), len(flp))
            aov_badge, aov_leader, aov_margin = leader_badge(amz["dis_price"].mean(), flp["dis_price"].mean())
            rat_badge, rat_leader, rat_margin = leader_badge(amz["cust_rating"].mean(), flp["cust_rating"].mean())
            disc_badge, disc_leader, disc_margin = leader_badge(amz["dis_percent"].mean(), flp["dis_percent"].mean())

            sc1, sc2, sc3, sc4, sc5 = st.columns(5)
            with sc1:
                st.markdown(f'<div class="info-card"><h3>💰 Revenue</h3>'
                            f'<p>Amazon: {format_inr(amz["dis_price"].sum())}<br>Flipkart: {format_inr(flp["dis_price"].sum())}</p>'
                            f'{rev_badge}</div>', unsafe_allow_html=True)
            with sc2:
                st.markdown(f'<div class="info-card"><h3>📦 Orders</h3>'
                            f'<p>Amazon: {len(amz):,}<br>Flipkart: {len(flp):,}</p>'
                            f'{ord_badge}</div>', unsafe_allow_html=True)
            with sc3:
                st.markdown(f'<div class="info-card"><h3>🧾 Avg Order Value</h3>'
                            f'<p>Amazon: {format_inr(amz["dis_price"].mean())}<br>Flipkart: {format_inr(flp["dis_price"].mean())}</p>'
                            f'{aov_badge}</div>', unsafe_allow_html=True)
            with sc4:
                st.markdown(f'<div class="info-card"><h3>⭐ Avg Rating</h3>'
                            f'<p>Amazon: {amz["cust_rating"].mean():.2f}<br>Flipkart: {flp["cust_rating"].mean():.2f}</p>'
                            f'{rat_badge}</div>', unsafe_allow_html=True)
            with sc5:
                st.markdown(f'<div class="info-card"><h3>🏷️ Avg Discount</h3>'
                            f'<p>Amazon: {amz["dis_percent"].mean():.1f}%<br>Flipkart: {flp["dis_percent"].mean():.1f}%</p>'
                            f'{disc_badge}</div>', unsafe_allow_html=True)

            # ---------- Key Insights ----------
            st.markdown('<div class="section-heading-lg">🔍 Key Insights</div>', unsafe_allow_html=True)

            # Category leadership
            cp = df.groupby(["prod_category", "Platform"])["dis_price"].sum().unstack(fill_value=0)
            if "Amazon" not in cp.columns:
                cp["Amazon"] = 0
            if "Flipkart" not in cp.columns:
                cp["Flipkart"] = 0
            cp["diff"] = cp["Amazon"] - cp["Flipkart"]
            amazon_cats = cp[cp["diff"] > 0].sort_values("diff", ascending=False).index.tolist()
            flipkart_cats = cp[cp["diff"] < 0].sort_values("diff").index.tolist()

            # Geography
            amz_top_state = amz.groupby("State_")["dis_price"].sum().idxmax() if len(amz) else "N/A"
            flp_top_state = flp.groupby("State_")["dis_price"].sum().idxmax() if len(flp) else "N/A"

            # Payment preference
            amz_top_pay = amz["mode_of_pay"].value_counts().idxmax() if len(amz) else "N/A"
            flp_top_pay = flp["mode_of_pay"].value_counts().idxmax() if len(flp) else "N/A"
            amz_top_pay_pct = amz["mode_of_pay"].value_counts(normalize=True).max() * 100 if len(amz) else 0
            flp_top_pay_pct = flp["mode_of_pay"].value_counts(normalize=True).max() * 100 if len(flp) else 0

            ic1, ic2 = st.columns(2)
            with ic1:
                cat_text = ""
                if amazon_cats:
                    cat_text += f"Amazon leads in <b>{join_natural(amazon_cats)}</b>. "
                if flipkart_cats:
                    cat_text += f"Flipkart leads in <b>{join_natural(flipkart_cats)}</b>."
                st.markdown(f"""
                    <div class="info-card">
                        <h3>🏬 Category Leadership</h3>
                        <p>{cat_text if cat_text else "Not enough category data to compare."}</p>
                    </div>
                """, unsafe_allow_html=True)

            with ic2:
                st.markdown(f"""
                    <div class="info-card">
                        <h3>🌍 Regional Strongholds</h3>
                        <p>Amazon's strongest state by revenue is <b>{amz_top_state}</b>, while Flipkart's is
                        <b>{flp_top_state}</b>{" — the same state, so both platforms compete hardest in the same market." if amz_top_state == flp_top_state else " — suggesting the two platforms may draw on different regional customer bases."}</p>
                    </div>
                """, unsafe_allow_html=True)

            ic3, ic4 = st.columns(2)
            with ic3:
                st.markdown(f"""
                    <div class="info-card">
                        <h3>💳 Payment Preference</h3>
                        <p>Amazon shoppers most often pay by <b>{amz_top_pay}</b> ({amz_top_pay_pct:.0f}% of orders),
                        while Flipkart shoppers most often use <b>{flp_top_pay}</b> ({flp_top_pay_pct:.0f}% of orders).</p>
                    </div>
                """, unsafe_allow_html=True)

            with ic4:
                if aov_leader != "Tied" and rev_leader != "Tied" and aov_leader != rev_leader:
                    nuance = (f"Interestingly, <b>{rev_leader}</b> generates more total revenue, but "
                              f"<b>{aov_leader}</b> shoppers spend more per order on average — one platform "
                              f"wins on volume, the other on order value.")
                else:
                    nuance = (f"<b>{rev_leader}</b> leads on both total revenue and average order value, "
                              f"a consistent edge across scale and spend-per-order.")
                st.markdown(f"""
                    <div class="info-card">
                        <h3>🧾 Revenue vs Order Value</h3>
                        <p>{nuance}</p>
                    </div>
                """, unsafe_allow_html=True)

            # ---------- Trends ----------
            st.markdown('<div class="section-heading-lg">📈 Trends</div>', unsafe_allow_html=True)

            yearly = df.groupby(["Year", "Platform"])["dis_price"].sum().unstack(fill_value=0)
            years_sorted = sorted(yearly.index.tolist())

            trend_col1, trend_col2 = st.columns([3, 2])

            with trend_col1:
                if len(years_sorted) >= 2:
                    fy, ly = years_sorted[0], years_sorted[-1]
                    amz_fy, amz_ly = yearly.loc[fy].get("Amazon", 0), yearly.loc[ly].get("Amazon", 0)
                    flp_fy, flp_ly = yearly.loc[fy].get("Flipkart", 0), yearly.loc[ly].get("Flipkart", 0)
                    amz_growth = ((amz_ly - amz_fy) / amz_fy * 100) if amz_fy != 0 else None
                    flp_growth = ((flp_ly - flp_fy) / flp_fy * 100) if flp_fy != 0 else None

                    def trend_phrase(name, growth):
                        if growth is None:
                            return f"{name}'s revenue trend from {fy} to {ly} isn't computable (no baseline)."
                        direction = "grew" if growth > 0 else ("declined" if growth < 0 else "stayed flat")
                        return f"{name}'s revenue {direction} {abs(growth):.1f}% from {fy} to {ly}"

                    amz_phrase = trend_phrase("Amazon", amz_growth)
                    flp_phrase = trend_phrase("Flipkart", flp_growth)

                    if amz_growth is not None and flp_growth is not None:
                        if (amz_growth > 0) != (flp_growth > 0):
                            combined = (f"{amz_phrase}, while {flp_phrase.split(chr(39)+'s',1)[1] if False else flp_phrase.lower().replace('flipkart', 'flipkart', 1)}"
                                        f" — the two platforms are moving in <b>opposite directions</b> over the period.")
                        else:
                            combined = f"{amz_phrase}, and {flp_phrase[0].lower() + flp_phrase[1:]}."
                    else:
                        combined = f"{amz_phrase}. {flp_phrase}."

                    st.markdown(f"""
                        <div class="info-card">
                            <h3>📆 Year-over-Year Trajectory</h3>
                            <p>{combined}</p>
                        </div>
                    """, unsafe_allow_html=True)

                    yoy_fig = go.Figure()
                    for plat in ["Amazon", "Flipkart"]:
                        if plat in yearly.columns:
                            yoy_fig.add_trace(go.Scatter(x=yearly.index, y=yearly[plat], name=plat, mode="lines+markers",
                                                          line=dict(color=PLATFORM_COLORS[plat], width=3), marker=dict(size=8),
                                                          hovertemplate="%{x}<br>₹%{y:,.0f}<extra>" + plat + "</extra>"))
                    yoy_fig.update_xaxes(title_text="Year", dtick=1)
                    yoy_fig.update_yaxes(title_text="Revenue (₹)")
                    st.plotly_chart(style_fig(yoy_fig, "Revenue by Year — Amazon vs Flipkart", height=380), width="stretch")
                else:
                    st.markdown("""
                        <div class="info-card">
                            <h3>📆 Year-over-Year Trajectory</h3>
                            <p>The loaded dataset only spans a single year, so a year-over-year trend can't be computed.</p>
                        </div>
                    """, unsafe_allow_html=True)

            with trend_col2:
                amz_best_day = amz.groupby("Weekday")["dis_price"].sum().idxmax() if len(amz) else "N/A"
                flp_best_day = flp.groupby("Weekday")["dis_price"].sum().idxmax() if len(flp) else "N/A"
                amz_fest_share = (amz["Festival_Sale"] != "No Festival").mean() * 100 if len(amz) else 0
                flp_fest_share = (flp["Festival_Sale"] != "No Festival").mean() * 100 if len(flp) else 0

                st.markdown(f"""
                    <div class="info-card">
                        <h3>📅 Weekly Pattern</h3>
                        <p>Amazon's biggest revenue day is <b>{amz_best_day}</b>; Flipkart's is <b>{flp_best_day}</b>.</p>
                    </div>
                """, unsafe_allow_html=True)

                more_festival_driven = "Amazon" if amz_fest_share > flp_fest_share else ("Flipkart" if flp_fest_share > amz_fest_share else None)
                fest_text = (f"<b>{more_festival_driven}</b> shoppers are more sale-driven — festival sales make up "
                             f"{max(amz_fest_share, flp_fest_share):.0f}% of their orders, vs "
                             f"{min(amz_fest_share, flp_fest_share):.0f}% for the other platform."
                             if more_festival_driven else
                             f"Both platforms see about the same share of orders during festival sales (~{amz_fest_share:.0f}%).")
                st.markdown(f"""
                    <div class="info-card">
                        <h3>🎉 Festival Sale Reliance</h3>
                        <p>{fest_text}</p>
                    </div>
                """, unsafe_allow_html=True)

            st.caption("Insights and trends recalculate automatically from whichever dataset is currently loaded "
                       "(uploaded file, or the bundled sample data).")
