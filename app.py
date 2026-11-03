"""
Telco churn dashboard (Streamlit).

"""
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Telco Churn Dashboard", page_icon="📉", layout="wide")

RED, GREY = "#d1495b", "#9aa5b1"
TIER_ORDER = ["Low", "Medium", "High"]
BUCKET_ORDER = ["0-12", "13-24", "25-48", "49-72"]


@st.cache_data
def load_data() -> pd.DataFrame:
    df = pd.read_csv("D:/My Resume/IBM_TELECOM/telcom/customer_risk_scores.csv")
    df["tenure_bucket"] = pd.cut(df["tenure_months"], bins=[-1, 12, 24, 48, 72],
                                 labels=BUCKET_ORDER).astype(str)
    df["risk_tier"] = pd.Categorical(df["risk_tier"], categories=TIER_ORDER, ordered=True)
    return df


def churn_rate_table(data: pd.DataFrame, col: str, order=None) -> pd.DataFrame:
    out = (data.groupby(col, observed=True)["churn_value"]
               .agg(customers="count", churn_rate=lambda s: s.mean() * 100)
               .reset_index())
    if order:
        out[col] = pd.Categorical(out[col], categories=order, ordered=True)
        out = out.sort_values(col)
    return out


def rate_chart(data: pd.DataFrame, col: str, title: str, order=None):
    t = churn_rate_table(data, col, order)
    fig = px.bar(t, x=col, y="churn_rate", text_auto=".1f", color_discrete_sequence=[RED],
                 hover_data={"customers": True, "churn_rate": ":.1f"})
    fig.update_layout(title=title, xaxis_title="", yaxis_title="Churn rate (%)",
                      margin=dict(t=50, b=10), height=340)
    return fig


df = load_data()

# ------------------------------ Sidebar filters ------------------------------
st.sidebar.header("Filters")
contracts = st.sidebar.multiselect("Contract", sorted(df["contract"].unique()),
                                   default=sorted(df["contract"].unique()))
internet = st.sidebar.multiselect("Internet service", sorted(df["internet_service"].unique()),
                                  default=sorted(df["internet_service"].unique()))
tenure_range = st.sidebar.slider("Tenure (months)", 0, int(df["tenure_months"].max()),
                                 (0, int(df["tenure_months"].max())))

view = df[df["contract"].isin(contracts)
          & df["internet_service"].isin(internet)
          & df["tenure_months"].between(*tenure_range)]

st.title("📉 Customer Churn Dashboard")
st.caption("IBM Telco sample dataset · 7,043 customers · risk scores are out-of-fold "
           "predictions from the best-performing model")

if view.empty:
    st.warning("No customers match these filters. Widen the filters in the sidebar.")
    st.stop()

# ------------------------------ KPIs ------------------------------
churned = view[view["churn_value"] == 1]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Customers", f"{len(view):,}")
c2.metric("Churn rate", f"{view['churn_value'].mean():.1%}")
c3.metric("Monthly revenue lost", f"${churned['monthly_charges'].sum():,.0f}",
          f"{churned['monthly_charges'].sum() / view['monthly_charges'].sum():.1%} of total",
          delta_color="off")
c4.metric("Annualized revenue lost", f"${churned['monthly_charges'].sum() * 12:,.0f}")

tab1, tab2, tab3 = st.tabs(["Churn drivers", "Risk tiers", "Retention scenario"])

# ------------------------------ Tab 1: drivers ------------------------------
with tab1:
    a, b = st.columns(2)
    a.plotly_chart(rate_chart(view, "contract", "Churn rate by contract",
                              ["Month-to-month", "One year", "Two year"]),
                   use_container_width=True)
    b.plotly_chart(rate_chart(view, "tenure_bucket", "Churn rate by tenure (months)",
                              BUCKET_ORDER), use_container_width=True)
    c, d = st.columns(2)
    c.plotly_chart(rate_chart(view, "internet_service", "Churn rate by internet service"),
                   use_container_width=True)
    avg = (view.groupby("churn_value")[["tenure_months", "monthly_charges"]].mean().round(1)
               .rename(index={0: "Stayed", 1: "Churned"}))
    d.subheader("Average profile")
    d.dataframe(avg.rename(columns={"tenure_months": "Tenure (months)",
                                    "monthly_charges": "Monthly charges ($)"}),
                use_container_width=True)
    d.caption("Churners pay more per month but have far shorter tenure.")

# ------------------------------ Tab 2: risk tiers ------------------------------
with tab2:
    tiers = (view.groupby("risk_tier", observed=True)
                 .agg(customers=("customer_id", "count"),
                      actual_churn_rate=("churn_value", lambda s: s.mean() * 100),
                      avg_monthly_charge=("monthly_charges", "mean"))
                 .reset_index())
    a, b = st.columns([1, 1])
    fig = px.bar(tiers, x="risk_tier", y="customers", text_auto=True,
                 color="risk_tier",
                 color_discrete_map={"Low": GREY, "Medium": "#e9a03b", "High": RED},
                 category_orders={"risk_tier": TIER_ORDER})
    fig.update_layout(title="Customers by predicted risk tier", showlegend=False,
                      xaxis_title="", margin=dict(t=50, b=10), height=340)
    a.plotly_chart(fig, use_container_width=True)
    b.subheader("Does the model rank risk correctly?")
    b.dataframe(tiers.rename(columns={"risk_tier": "Tier", "customers": "Customers",
                                      "actual_churn_rate": "Actual churn rate (%)",
                                      "avg_monthly_charge": "Avg monthly charge ($)"})
                     .round(1), use_container_width=True, hide_index=True)
    b.caption("Tiers: Low ≤ 0.40, Medium 0.40 to 0.70, High > 0.70 predicted probability.")

    st.subheader("Retention targets: high-risk customers who are still active")
    targets = (view[(view["risk_tier"] == "High") & (view["churn_value"] == 0)]
               .sort_values("churn_probability", ascending=False)
               [["customer_id", "contract", "tenure_months", "internet_service",
                 "monthly_charges", "churn_probability"]])
    st.write(f"**{len(targets):,}** customers to contact first (sorted by risk).")
    st.dataframe(targets, use_container_width=True, hide_index=True)
    st.download_button("Download target list (CSV)", targets.to_csv(index=False),
                       "retention_targets.csv", "text/csv")

# ------------------------------ Tab 3: scenario ------------------------------
with tab3:
    st.markdown("Estimate the payoff of a retention campaign aimed at the **High** risk tier. "
                "The two sliders are **assumptions**, not facts from the data.")
    s1, s2 = st.columns(2)
    save_rate = s1.slider("Share of would-be churners a retention offer keeps", 0, 60, 20, 5,
                          format="%d%%") / 100
    offer_cost = s2.slider("Cost per customer contacted ($)", 5, 100, 30, 5)

    high = view[view["risk_tier"] == "High"]
    high_churners = high[high["churn_value"] == 1]
    at_risk = high_churners["monthly_charges"].sum() * 12
    saved = at_risk * save_rate
    cost = len(high) * offer_cost

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("High-risk customers", f"{len(high):,}")
    m2.metric("Annual revenue at risk", f"${at_risk:,.0f}")
    m3.metric("Revenue retained", f"${saved:,.0f}")
    m4.metric("Net benefit", f"${saved - cost:,.0f}", f"cost ${cost:,.0f}", delta_color="off")
    share = len(high_churners) / max(len(churned), 1)
    st.caption(f"High tier catches {share:.1%} of all churners in the current selection. "
               "This is a backtest on historical outcomes, so treat it as an estimate.")