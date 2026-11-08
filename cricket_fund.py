import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- PAGE SETUP & FUTURISTIC THEME ---
st.set_page_config(
    page_title="Squad Fund Tracker",
    page_icon="🏏",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Cyberpunk/Futuristic Styling
st.markdown("""
    <style>
    .main {
        background-color: #0b0f19;
    }
    .metric-card {
        background: linear-gradient(135deg, #111827 0%, #1f2937 100%);
        padding: 22px;
        border-radius: 14px;
        border-left: 6px solid #00f2fe;
        box-shadow: 0 4px 20px rgba(0, 242, 254, 0.1);
        margin-bottom: 15px;
    }
    .metric-card h3 {
        margin: 6px 0 0 0;
        font-size: 28px;
        color: #f8fafc;
        font-weight: 700;
    }
    .metric-card p {
        margin: 0;
        font-size: 13px;
        letter-spacing: 1px;
        text-transform: uppercase;
        color: #94a3b8;
    }
    .metric-card small {
        color: #38bdf8;
        font-size: 12px;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #1e293b;
        border-radius: 8px 8px 0px 0px;
        padding: 10px 20px;
        color: #e2e8f0;
    }
    .stTabs [aria-selected="true"] {
        background-color: #0284c7 !important;
        color: #ffffff !important;
    }
    </style>
""", unsafe_allow_html=True)

MONTHLY_CONTRIBUTION = 100
ADMIN_PIN = "1234"

# --- DATABASE SETUP (LOCAL SQLITE) ---
DB_NAME = "cricket_funds.db"

def get_db():
    conn = sqlite3.connect(DB_NAME)
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    # 1. Players Table
    c.execute("""
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """)
    
    # 2. Payments Table
    c.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            player_id INTEGER,
            month_year TEXT,
            paid_status INTEGER DEFAULT 0,
            PRIMARY KEY (player_id, month_year),
            FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE
        )
    """)
    
    # 3. Expenses Table
    c.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item TEXT NOT NULL,
            amount REAL NOT NULL,
            date TEXT NOT NULL
        )
    """)

    # 4. Extra Funds / Donations Table
    c.execute("""
        CREATE TABLE IF NOT EXISTS extra_funds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            donor_name TEXT NOT NULL,
            amount REAL NOT NULL,
            date TEXT NOT NULL,
            notes TEXT
        )
    """)
    
    # Pre-seed Core Players
    squad = [
        "Aryan", "Anik", "Santanu", "Dipta", "Kankan", "Rony", "Rohit", "Banty",
        "Vivek", "Abhishek", "Joydeep", "Alto", "Pinaki", "Gulan da", "Ayan da", "Abhirup"
    ]
    for p in squad:
        c.execute("INSERT OR IGNORE INTO players (name) VALUES (?)", (p,))
        
    conn.commit()
    conn.close()

init_db()

# --- DYNAMIC 6-MONTH BLOCK GENERATION ---
def get_month_options():
    now = datetime.now()
    cur_year = now.year
    cur_month = now.month
    
    options = []
    # Baseline: 05-2026 to 12-2026
    for m in range(5, 13):
        options.append(f"{m:02d}-2026")
        
    # Future 6-month block unlocking
    for y in range(2027, cur_year + 1):
        if y == cur_year:
            if cur_month >= 1:
                for m in range(1, 7):
                    options.append(f"{m:02d}-{y}")
            if cur_month >= 7:
                for m in range(7, 13):
                    options.append(f"{m:02d}-{y}")
        else:
            for m in range(1, 13):
                options.append(f"{m:02d}-{y}")
                
    options.reverse()
    return options

month_options = get_month_options()
current_month_str = datetime.now().strftime("%m-%Y")
default_idx = month_options.index(current_month_str) if current_month_str in month_options else 0

# --- HEADER SECTION ---
col_head, col_sel = st.columns([3, 1])
with col_head:
    st.title("⚡ CRICKET SQUAD TREASURY")
    st.caption("Local High-Performance Ledger & Expense Engine")
with col_sel:
    selected_month = st.selectbox("📅 Target Month", month_options, index=default_idx)

# --- ENSURE PLAYERS SYNC FOR SELECTED MONTH ---
conn = get_db()
c = conn.cursor()
c.execute("SELECT id FROM players")
player_ids = [row[0] for row in c.fetchall()]
for pid in player_ids:
    c.execute("INSERT OR IGNORE INTO payments (player_id, month_year, paid_status) VALUES (?, ?, 0)", (pid, selected_month))
conn.commit()

# --- RETRIEVE DATA ---
df_payments = pd.read_sql_query(f"""
    SELECT p.id, p.name, COALESCE(pm.paid_status, 0) as paid
    FROM players p
    LEFT JOIN payments pm ON p.id = pm.player_id AND pm.month_year = '{selected_month}'
    ORDER BY p.name ASC
""", conn)

df_expenses = pd.read_sql_query("""
    SELECT id, item as 'Item / Particulars', amount as 'Amount (₹)', date as 'Date' 
    FROM expenses 
    ORDER BY id DESC
""", conn)

df_extra = pd.read_sql_query("""
    SELECT id, donor_name as 'Source / Donor', amount as 'Amount (₹)', date as 'Date', notes as 'Remarks'
    FROM extra_funds
    ORDER BY id DESC
""", conn)

# Lifetime calculations
c.execute("SELECT SUM(paid_status) FROM payments")
total_paid_units = c.fetchone()[0] or 0
total_collected_lifetime = total_paid_units * MONTHLY_CONTRIBUTION

c.execute("SELECT SUM(amount) FROM expenses")
total_spent_lifetime = c.fetchone()[0] or 0.0

c.execute("SELECT SUM(amount) FROM extra_funds")
total_extra_funds = c.fetchone()[0] or 0.0

conn.close()

# Month-specific Math
total_players = len(df_payments)
paid_count = int(df_payments['paid'].sum())
pending_count = total_players - paid_count
collected_this_month = paid_count * MONTHLY_CONTRIBUTION
pending_this_month = pending_count * MONTHLY_CONTRIBUTION
treasury_balance = (total_collected_lifetime + total_extra_funds) - total_spent_lifetime

# --- TOP METRIC CARDS ---
m1, m2, m3, m4 = st.columns(4)

with m1:
    st.markdown(f"""
        <div class="metric-card" style="border-left-color: #00f2fe;">
            <p>Treasury Balance</p>
            <h3>₹{int(treasury_balance)}</h3>
            <small>Net Cash in Vault</small>
        </div>
    """, unsafe_allow_html=True)

with m2:
    st.markdown(f"""
        <div class="metric-card" style="border-left-color: #10b981;">
            <p>Collected ({selected_month})</p>
            <h3>₹{collected_this_month}</h3>
            <small>{paid_count} / {total_players} Cleared</small>
        </div>
    """, unsafe_allow_html=True)

with m3:
    st.markdown(f"""
        <div class="metric-card" style="border-left-color: #f59e0b;">
            <p>Extra Funds / Donations</p>
            <h3>₹{int(total_extra_funds)}</h3>
            <small>External Contributions</small>
        </div>
    """, unsafe_allow_html=True)

with m4:
    st.markdown(f"""
        <div class="metric-card" style="border-left-color: #a855f7;">
            <p>Total Group Spent</p>
            <h3>₹{int(total_spent_lifetime)}</h3>
            <small>Balls, Kit & Rentals</small>
        </div>
    """, unsafe_allow_html=True)

# --- MAIN TABS ---
tab_roster, tab_exp, tab_extra, tab_admin = st.tabs([
    "🏏 Scoreboard / Roster", 
    "🧾 Expenses", 
    "🎁 Extra Funds", 
    "🔐 Admin Console"
])

with tab_roster:
    st.subheader(f"Payment Status for {selected_month}")
    display_df = df_payments.copy()
    display_df['Status'] = display_df['paid'].apply(lambda x: "🟢 PAID (₹100)" if x == 1 else "🔴 PENDING")
    
    col_t1, col_t2 = st.columns([2, 1])
    with col_t1:
        st.dataframe(
            display_df[['name', 'Status']].rename(columns={'name': 'Player'}),
            use_container_width=True,
            hide_index=True
        )
    with col_t2:
        st.markdown("#### Squad Summary")
        if total_players > 0:
            pct = (paid_count / total_players)
            st.progress(pct)
            st.write(f"**{int(pct * 100)}% Collected** for this month.")
            st.write(f"Pending Dues: **₹{pending_this_month}**")

with tab_exp:
    st.subheader("Equipment & Match Expenditure")
    if df_expenses.empty:
        st.info("No expenses recorded yet. All treasury funds intact!")
    else:
        st.dataframe(df_expenses[['Item / Particulars', 'Amount (₹)', 'Date']], use_container_width=True, hide_index=True)

with tab_extra:
    st.subheader("External Contributions & Uncle Donations")
    if df_extra.empty:
        st.info("No external donations logged yet.")
    else:
        st.dataframe(df_extra[['Source / Donor', 'Amount (₹)', 'Date', 'Remarks']], use_container_width=True, hide_index=True)

with tab_admin:
    st.subheader("Admin Control Center")
    admin_pin = st.text_input("Enter 4-Digit Admin PIN", type="password", key="admin_pin_input")
    
    if admin_pin == ADMIN_PIN:
        st.success("Authorized. You can modify records below.")
        
        admin_mode = st.radio(
            "Choose Action", 
            [
                "Update Member Payments", 
                "Log Extra Fund / Donation", 
                "Log New Expense", 
                "Add New Member", 
                "Delete / Remove Member"
            ], 
            horizontal=True
        )
        
        conn = get_db()
        c = conn.cursor()
        
        if admin_mode == "Update Member Payments":
            st.write(f"#### Check off members who paid for **{selected_month}**:")
            cols = st.columns(2)
            updated_vals = {}
            for i, row in df_payments.iterrows():
                target_col = cols[i % 2]
                with target_col:
                    checked = st.checkbox(f"{row['name']}", value=(row['paid'] == 1), key=f"p_{row['id']}")
                    updated_vals[row['id']] = 1 if checked else 0
                    
            if st.button("💾 Save Payment Status", type="primary"):
                for pid, status in updated_vals.items():
                    c.execute("""
                        UPDATE payments 
                        SET paid_status = ? 
                        WHERE player_id = ? AND month_year = ?
                    """, (status, pid, selected_month))
                conn.commit()
                st.toast("Payments updated successfully!")
                st.rerun()
                
        elif admin_mode == "Log Extra Fund / Donation":
            st.write("#### Add Extra Income / Donor Contribution:")
            c_f1, c_f2 = st.columns([2, 1])
            with c_f1:
                donor_name = st.text_input("Donor / Source (e.g., Sharma Uncle, Tournament Cash Prize)")
                donor_notes = st.text_input("Remarks / Notes (Optional, e.g., For match refreshments)")
            with c_f2:
                donation_amt = st.number_input("Amount (₹)", min_value=0.0, step=50.0)
                
            if st.button("🎁 Deposit Extra Fund", type="primary"):
                if donor_name.strip() and donation_amt > 0:
                    today = datetime.now().strftime("%d-%b-%Y")
                    c.execute(
                        "INSERT INTO extra_funds (donor_name, amount, date, notes) VALUES (?, ?, ?, ?)",
                        (donor_name.strip(), donation_amt, today, donor_notes.strip())
                    )
                    conn.commit()
                    st.toast(f"Added ₹{donation_amt} from {donor_name} to Treasury!")
                    st.rerun()
                else:
                    st.error("Please enter a valid donor name and amount.")

        elif admin_mode == "Log New Expense":
            st.write("#### Debit Cash from Treasury:")
            c_e1, c_e2 = st.columns([2, 1])
            with c_e1:
                item_name = st.text_input("Item Description (e.g., 2 Vicky Tennis Balls)")
            with c_e2:
                item_price = st.number_input("Amount (₹)", min_value=0.0, step=10.0)
                
            if st.button("💸 Record Expense", type="primary"):
                if item_name and item_price > 0:
                    today = datetime.now().strftime("%d-%b-%Y")
                    c.execute("INSERT INTO expenses (item, amount, date) VALUES (?, ?, ?)", (item_name, item_price, today))
                    conn.commit()
                    st.toast(f"Logged ₹{item_price} for {item_name}")
                    st.rerun()
                else:
                    st.error("Please enter a valid item name and amount.")
                    
        elif admin_mode == "Add New Member":
            st.write("#### Add a Permanent Squad Member:")
            new_member = st.text_input("Member Full Name")
            if st.button("➕ Add Member", type="primary"):
                if new_member.strip():
                    try:
                        c.execute("INSERT INTO players (name) VALUES (?)", (new_member.strip(),))
                        conn.commit()
                        st.toast(f"{new_member} added to squad!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("This player is already in the roster.")
                else:
                    st.error("Name cannot be empty.")
                    
        elif admin_mode == "Delete / Remove Member":
            st.write("#### Remove an Inactive / Exited Player:")
            c.execute("SELECT id, name FROM players ORDER BY name ASC")
            all_players = c.fetchall()
            
            if all_players:
                player_dict = {name: pid for pid, name in all_players}
                player_to_remove = st.selectbox("Select Player to Delete", list(player_dict.keys()))
                
                confirm = st.checkbox(f"Yes, remove '{player_to_remove}' permanently from squad")
                if st.button("🗑️ Remove Player", type="primary"):
                    if confirm:
                        pid = player_dict[player_to_remove]
                        c.execute("DELETE FROM payments WHERE player_id = ?", (pid,))
                        c.execute("DELETE FROM players WHERE id = ?", (pid,))
                        conn.commit()
                        st.toast(f"{player_to_remove} has been removed.")
                        st.rerun()
                    else:
                        st.warning("Please tick the confirmation checkbox first.")
            else:
                st.info("No players left in roster.")

        conn.close()
    elif admin_pin != "":
        st.error("Incorrect PIN. Modifications locked.")
