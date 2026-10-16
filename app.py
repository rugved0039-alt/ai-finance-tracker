import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import date

st.set_page_config(page_title="AI Finance Tracker", page_icon="💰", layout="wide")

DB = "finance.db"

def connect():
    return sqlite3.connect(DB)

def setup():
    with connect() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT, type TEXT, category TEXT,
                amount REAL, note TEXT
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS budgets (
                category TEXT PRIMARY KEY,
                amount REAL
            )
        """)

def get_data():
    with connect() as con:
        return pd.read_sql_query("SELECT * FROM transactions ORDER BY date DESC", con)

setup()

st.title("💰 AI Personal Finance & Budget Tracker")
st.caption("Track money • Manage budgets • Understand spending")

menu = st.sidebar.radio(
    "Navigation",
    ["Dashboard", "Add Transaction", "Transaction History",
     "Budget Planner", "AI Money Advisor"]
)

if menu == "Dashboard":
    st.subheader("📊 Financial Dashboard")

    month = st.sidebar.text_input("Month (YYYY-MM)", date.today().strftime("%Y-%m"))
    df = get_data()
    monthly = df[df["date"].str.startswith(month)] if not df.empty else df

    income = monthly.loc[monthly["type"] == "Income", "amount"].sum() if not monthly.empty else 0
    expenses = monthly.loc[monthly["type"] == "Expense", "amount"].sum() if not monthly.empty else 0
    savings = income - expenses

    a, b, c = st.columns(3)
    a.metric("Total Income", f"₹{income:,.2f}")
    b.metric("Total Expenses", f"₹{expenses:,.2f}")
    c.metric("Remaining Balance", f"₹{savings:,.2f}")

    if not monthly.empty:
        expenses_df = monthly[monthly["type"] == "Expense"]
        if not expenses_df.empty:
            st.subheader("Spending by Category")
            category_totals = expenses_df.groupby("category", as_index=False)["amount"].sum()
            st.plotly_chart(
                px.pie(category_totals, names="category", values="amount",
                       title="Expense Breakdown"),
                use_container_width=True
            )

        st.subheader("Recent Transactions")
        st.dataframe(monthly, use_container_width=True)

        st.download_button(
            "Download Transactions as CSV",
            monthly.to_csv(index=False).encode("utf-8"),
            file_name="finance_transactions.csv",
            mime="text/csv"
        )
    else:
        st.info("No transactions for this month. Add your first transaction!")

elif menu == "Add Transaction":
    st.subheader("➕ Add Income or Expense")

    with st.form("transaction_form", clear_on_submit=True):
        transaction_date = st.date_input("Date", date.today())
        transaction_type = st.selectbox("Type", ["Expense", "Income"])
        category = st.selectbox(
            "Category",
            ["Food", "Travel", "Education", "Shopping", "Bills",
             "Health", "Entertainment", "Salary", "Freelance", "Other"]
        )
        amount = st.number_input("Amount (₹)", min_value=0.01, step=10.0)
        note = st.text_input("Description (optional)")
        submitted = st.form_submit_button("Save Transaction")

        if submitted:
            with connect() as con:
                con.execute(
                    "INSERT INTO transactions (date,type,category,amount,note) VALUES (?,?,?,?,?)",
                    (str(transaction_date), transaction_type, category, amount, note)
                )
            st.success("Transaction saved successfully!")
            st.rerun()

elif menu == "Transaction History":
    st.subheader("📚 Transaction History")
    df = get_data()

    if df.empty:
        st.info("No transactions yet.")
    else:
        st.dataframe(df, use_container_width=True)
        selected_id = st.selectbox("Select transaction ID to delete", df["id"].tolist())
        if st.button("Delete Selected Transaction"):
            with connect() as con:
                con.execute("DELETE FROM transactions WHERE id = ?", (selected_id,))
            st.success("Transaction deleted.")
            st.rerun()

elif menu == "Budget Planner":
    st.subheader("🎯 Monthly Budget Planner")

    categories = ["Food", "Travel", "Education", "Shopping", "Bills",
                  "Health", "Entertainment", "Other"]

    with connect() as con:
        budgets_df = pd.read_sql_query("SELECT * FROM budgets", con)

    chosen_category = st.selectbox("Category", categories)
    existing = budgets_df.loc[
        budgets_df["category"] == chosen_category, "amount"
    ] if not budgets_df.empty else pd.Series(dtype=float)
    default_amount = float(existing.iloc[0]) if not existing.empty else 1000.0

    budget_amount = st.number_input(
        "Monthly budget (₹)", min_value=0.0, value=default_amount, step=100.0
    )

    if st.button("Save Budget"):
        with connect() as con:
            con.execute(
                "INSERT OR REPLACE INTO budgets (category, amount) VALUES (?, ?)",
                (chosen_category, budget_amount)
            )
        st.success("Budget saved!")
        st.rerun()

    month = date.today().strftime("%Y-%m")
    df = get_data()
    monthly_expenses = df[
        (df["type"] == "Expense") & df["date"].str.startswith(month)
    ] if not df.empty else df

    if not budgets_df.empty:
        st.subheader("Budget Usage — Current Month")
        for _, row in budgets_df.iterrows():
            spent = monthly_expenses.loc[
                monthly_expenses["category"] == row["category"], "amount"
            ].sum() if not monthly_expenses.empty else 0
            limit = row["amount"]
            st.write(f"**{row['category']}** — ₹{spent:,.0f} / ₹{limit:,.0f}")
            st.progress(min(spent / limit, 1.0) if limit > 0 else 0.0)
            if limit > 0 and spent > limit:
                st.warning(f"{row['category']} budget exceeded!")

elif menu == "AI Money Advisor":
    st.subheader("🤖 Personal Money Insights")
    st.caption("Rule-based financial insights from your recorded transactions.")

    df = get_data()
    month = date.today().strftime("%Y-%m")
    monthly = df[df["date"].str.startswith(month)] if not df.empty else df

    income = monthly.loc[monthly["type"] == "Income", "amount"].sum() if not monthly.empty else 0
    expenses = monthly.loc[monthly["type"] == "Expense", "amount"].sum() if not monthly.empty else 0

    if monthly.empty:
        st.info("Add some income and expenses to receive personalized insights.")
    else:
        if income > 0:
            savings_rate = (income - expenses) / income * 100
            st.metric("Savings Rate", f"{savings_rate:.1f}%")

            if expenses > income:
                st.error("Your expenses are higher than your income. Review non-essential spending.")
            elif savings_rate >= 20:
                st.success("Good work! You're keeping at least 20% of income unspent.")
            elif savings_rate > 0:
                st.info("You're spending most of your income. Try setting a small savings target.")
            else:
                st.warning("Your expenses equal your income. Look for a realistic way to save.")

        expense_rows = monthly[monthly["type"] == "Expense"]
        if not expense_rows.empty:
            totals = expense_rows.groupby("category")["amount"].sum().sort_values(ascending=False)
            top_category = totals.index[0]
            st.write(f"Your highest spending category is **{top_category}** (₹{totals.iloc[0]:,.2f}).")
            st.write("Tip: Set a budget for this category and review it weekly.")

st.sidebar.divider()
st.sidebar.caption("Your data is stored locally in finance.db")
