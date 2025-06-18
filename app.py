import streamlit as st
import pandas as pd
import requests
import io
import matplotlib.pyplot as plt
import seaborn as sns

API_URL = "https://price-optimization-n20m.onrender.com/predict/"

st.set_page_config(page_title="Price Optimization Predictor", page_icon="💸", layout="wide")
st.title("💸 Price Optimization – Customer Continuation After Price Increase")

st.markdown(
    """This tool lets revenue managers at booking platforms (Expedia, Kayak, …) **score individual
    customers or entire files** to see who is likely to keep buying after a price increase.
    Upload an Excel sheet or play with single-customer inputs. You can also explore aggregate
    probability distributions under *Visual Analytics*.""")

menu = st.sidebar.radio(
    "Select mode",
    ["1 Single Prediction", "2 Batch Prediction (Excel)", "3 Visual Analytics"],
    format_func=lambda x: x.split(" ")[1]
)

# ────────────────────────────────────────────────────────────────────────────────
# 1 -- Single-customer prediction
# ────────────────────────────────────────────────────────────────────────────────
if menu.startswith("1"):
    st.header("Single-customer Prediction")

    total_spent = st.number_input("Total spent (USD)", min_value=0.0, value=0.0, step=10.0)
    avg_order_value = st.number_input("Average order value (USD)", min_value=0.0, value=0.0, step=5.0)
    avg_purchase_frequency = st.number_input("Average purchase frequency (per month)", min_value=0.0, value=0.0, step=0.1)
    days_since_last_purchase = st.number_input("Days since last purchase", min_value=0, value=30, step=1)
    discount_behavior = st.number_input("Discount behaviour (share of orders with coupon)", min_value=0.0, max_value=1.0, value=0.2, step=0.05, format="%.2f")
    loyalty_program_member = st.selectbox("Loyalty program member", options=[0, 1], format_func=lambda x: "Yes" if x else "No")
    days_in_advance = st.number_input("Days booked in advance", min_value=0, value=14, step=1)
    flight_type = st.selectbox("Flight type", options=["domestic", "international"])
    cabin_class = st.selectbox("Cabin class", options=["economy", "business"])

    if st.button("Predict"):
        payload = {
            "total_spent": total_spent,
            "avg_order_value": avg_order_value,
            "avg_purchase_frequency": avg_purchase_frequency,
            "days_since_last_purchase": days_since_last_purchase,
            "discount_behavior": discount_behavior,
            "loyalty_program_member": loyalty_program_member,
            "days_in_advance": days_in_advance,
            "flight_type": flight_type,
            "cabin_class": cabin_class
        }

        with st.spinner("Calling prediction API…"):
            resp = requests.post(API_URL, json=payload, timeout=10)

        if resp.status_code == 200:
            out = resp.json()
            label = "✅ Likely to **continue** buying" if out["will_buy_after_price_increase"] else "⚠️ Likely to **stop** buying"
            prob = out["probability"]
            st.markdown(f"### {label}\nProbability of continuing: **{prob:.1%}**")
        else:
            st.error(f"API error {resp.status_code}: {resp.text}")

# ────────────────────────────────────────────────────────────────────────────────
# 2 -- Batch prediction
# ────────────────────────────────────────────────────────────────────────────────
elif menu.startswith("2"):
    st.header("Batch Prediction – Upload Excel")

    uploaded = st.file_uploader("Upload .xlsx file containing the 9 input columns", type=["xlsx"])

    if uploaded is not None:
        df = pd.read_excel(uploaded)
        st.write("Preview of uploaded data:", df.head())

        if st.button("Run batch prediction"):
            preds, probs = [], []

            for _, row in df.iterrows():
                payload = row.to_dict()
                resp = requests.post(API_URL, json=payload, timeout=10)
                if resp.ok:
                    out = resp.json()
                    preds.append(out["will_buy_after_price_increase"])
                    probs.append(out["probability"])
                else:
                    preds.append(None)
                    probs.append(None)

            df["Prediction"] = preds
            df["Probability"] = probs

            st.success("Batch prediction complete.")
            st.write(df.head())

            # Download
            towrite = io.BytesIO()
            with pd.ExcelWriter(towrite, engine="openpyxl") as writer:
                df.to_excel(writer, index=False)
            towrite.seek(0)
            st.download_button(
                label="Download results as Excel",
                data=towrite,
                file_name="predictions.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

# ────────────────────────────────────────────────────────────────────────────────
# 3 -- Visual analytics
# ────────────────────────────────────────────────────────────────────────────────
else:
    st.header("Visual Analytics – Explore existing predictions")

    uploaded = st.file_uploader("Upload an Excel file *with* Prediction & Probability columns", type=["xlsx"])

    if uploaded is not None:
        df = pd.read_excel(uploaded)
        if {"Prediction", "Probability"}.issubset(df.columns):
            st.write("Preview:", df.head())

            pct = df["Prediction"].mean() * 100
            st.metric("Share predicted to continue buying", f"{pct:.2f}%")

            st.subheader("Probability distribution")
            fig1 = plt.figure(figsize=(8, 4))
            sns.histplot(df["Probability"], bins=20, kde=True)
            plt.xlabel("Probability of continuing")
            plt.ylabel("Frequency")
            st.pyplot(fig1)

            st.subheader("Segment counts")
            count_df = df["Prediction"].value_counts().rename(index={0: "Stop", 1: "Continue"})
            st.bar_chart(count_df)
        else:
            st.error("File must contain 'Prediction' and 'Probability' columns.")
