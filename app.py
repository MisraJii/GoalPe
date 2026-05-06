"""
GoalPe — AI Wealth Coach for the next 100M Indian retail investors.
Streamlit prototype. Not SEBI registered. Educational use only.
"""

import json
import re
from datetime import datetime

import streamlit as st
import google.generativeai as genai
import yfinance as yf
import gspread
from google.oauth2.service_account import Credentials
from streamlit_option_menu import option_menu

# ==========================================
# Page config — MUST be first Streamlit call
# ==========================================
st.set_page_config(
    page_title="GoalPe",
    page_icon="🎯",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ==========================================
# Secrets & clients
# ==========================================
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except Exception as e:
    st.error("Gemini key missing in Streamlit secrets. Add GEMINI_API_KEY.")
    st.stop()

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

@st.cache_resource(show_spinner=False)
def get_gsheet_client():
    try:
        creds_dict = dict(st.secrets["google_credentials"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        return gspread.authorize(creds)
    except Exception as e:
        print(f"[gspread init error] {e}")
        return None

GC = get_gsheet_client()
SHEET_NAME = "GoalPe"
GOALS_WS = "Goals"
USER_ID = "DEMO"  # single demo user for now

# ==========================================
# Global theme
# ==========================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"], .stApp, .stMarkdown, .stButton, .stTextInput, .stChatMessage {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

:root {
    --gp-primary: #0F766E;
    --gp-primary-dark: #115E59;
    --gp-accent: #FACC15;
    --gp-bg: #F8FAFC;
    --gp-card: #FFFFFF;
    --gp-text: #0F172A;
    --gp-muted: #64748B;
    --gp-success: #16A34A;
    --gp-danger: #DC2626;
}

.stApp { background: var(--gp-bg); }

/* Hide Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }

/* Cards */
.gp-card {
    background: var(--gp-card);
    border-radius: 16px;
    padding: 18px 20px;
    box-shadow: 0 2px 12px rgba(15,23,42,0.06);
    margin-bottom: 14px;
    border: 1px solid #EEF2F7;
}
.gp-pill {
    display: inline-block; padding: 4px 12px; border-radius: 999px;
    background: var(--gp-primary); color: #fff;
    font-size: 11px; font-weight: 600; letter-spacing: 0.3px;
    text-transform: uppercase;
}
.gp-pill-accent { background: var(--gp-accent); color: #422006; }
.gp-h { font-size: 22px; font-weight: 700; color: var(--gp-text); margin: 4px 0 2px; }
.gp-sub { color: var(--gp-muted); font-size: 13px; margin: 0; }
.gp-stat-num { font-size: 26px; font-weight: 800; color: var(--gp-primary); }
.gp-row { display: flex; justify-content: space-between; align-items: center; }
.gp-up { color: var(--gp-success); font-weight: 600; }
.gp-down { color: var(--gp-danger); font-weight: 600; }

/* Buttons */
.stButton > button {
    border-radius: 12px; font-weight: 600; padding: 10px 18px;
    background: var(--gp-primary); color: #fff; border: none;
    transition: all 0.15s ease;
}
.stButton > button:hover {
    background: var(--gp-primary-dark);
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(15,118,110,0.25);
}

/* Hero */
.gp-hero {
    background: linear-gradient(135deg, #0F766E 0%, #14B8A6 100%);
    color: #fff; padding: 22px; border-radius: 18px; margin-bottom: 18px;
}
.gp-hero h1 { font-size: 26px; margin: 0 0 4px; font-weight: 800; }
.gp-hero p { margin: 0; opacity: 0.92; font-size: 14px; }

/* Progress override */
.stProgress > div > div > div { background: var(--gp-primary) !important; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# Helpers
# ==========================================
def safe_float(val, default=0.0, min_v=0, max_v=1e10):
    try:
        v = float(val)
        return v if min_v <= v <= max_v else default
    except (ValueError, TypeError):
        return default

def fmt_inr(amount):
    try:
        amount = float(amount)
    except Exception:
        return "₹0"
    if amount >= 1e7:
        return f"₹{amount/1e7:.2f} Cr"
    if amount >= 1e5:
        return f"₹{amount/1e5:.2f} L"
    if amount >= 1e3:
        return f"₹{amount/1e3:.1f}K"
    return f"₹{amount:,.0f}"

def calc_sip(target_amount, months, annual_return=0.12):
    """Monthly SIP needed to reach target_amount in `months` at `annual_return`."""
    r = annual_return / 12
    n = months
    if r == 0:
        return target_amount / n
    return target_amount * r / ((1 + r) ** n - 1)

# ==========================================
# Google Sheets persistence
# ==========================================
def _open_goals_ws():
    if GC is None:
        return None
    try:
        sh = GC.open(SHEET_NAME)
        try:
            ws = sh.worksheet(GOALS_WS)
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title=GOALS_WS, rows=1000, cols=8)
            ws.append_row(["user_id", "name", "amount", "months",
                           "saved", "monthly_sip", "created_at", "id"])
        return ws
    except Exception as e:
        print(f"[sheet open error] {e}")
        return None

@st.cache_data(ttl=20, show_spinner=False)
def load_goals(user_id: str):
    ws = _open_goals_ws()
    if ws is None:
        return []
    try:
        rows = ws.get_all_records()
        return [r for r in rows if str(r.get("user_id")) == user_id]
    except Exception as e:
        print(f"[load_goals] {e}")
        return []

def save_goal(user_id: str, goal: dict):
    ws = _open_goals_ws()
    if ws is None:
        st.toast("⚠️ Couldn't save goal (sheet unavailable)", icon="⚠️")
        return False
    try:
        ws.append_row([
            user_id,
            goal.get("name", "Untitled"),
            safe_float(goal.get("amount")),
            int(safe_float(goal.get("months"), default=12)),
            safe_float(goal.get("saved", 0)),
            round(safe_float(goal.get("monthly_sip", 0)), 2),
            datetime.now().isoformat(timespec="seconds"),
            f"g_{int(datetime.now().timestamp())}",
        ])
        load_goals.clear()
        return True
    except Exception as e:
        print(f"[save_goal] {e}")
        st.toast("⚠️ Save failed", icon="⚠️")
        return False

def delete_all_goals(user_id: str):
    ws = _open_goals_ws()
    if ws is None:
        return
    try:
        all_rows = ws.get_all_values()
        # Keep header row
        keep = [all_rows[0]] if all_rows else []
        for row in all_rows[1:]:
            if row and row[0] != user_id:
                keep.append(row)
        ws.clear()
        if keep:
            ws.update("A1", keep)
        load_goals.clear()
    except Exception as e:
        print(f"[delete_all_goals] {e}")

# ==========================================
# Gemini
# ==========================================
SYSTEM_PROMPT = """You are GoalPe, a friendly AI wealth coach for first-time
Indian retail investors. Speak simply (8th-grade English, sprinkle Hindi if natural).
Focus on goal-based saving, SIPs, behavioural nudges (skip impulse buys, automate
savings). Never recommend specific stocks. Always remind users you are not a SEBI
advisor when they ask for trading advice. Keep replies under 120 words unless asked."""

@st.cache_resource(show_spinner=False)
def get_chat_model():
    return genai.GenerativeModel("gemini-2.5-flash", system_instruction=SYSTEM_PROMPT)

@st.cache_resource(show_spinner=False)
def get_json_model():
    return genai.GenerativeModel(
        "gemini-2.5-flash",
        generation_config={"response_mime_type": "application/json"},
    )

def detect_goal(user_text: str):
    """Ask Gemini to extract a goal from a user message. Returns dict or None."""
    prompt = f"""Extract a savings goal from this user message if one exists.
Return JSON with keys: name (string), amount (number in INR), months (integer).
If no clear goal, return {{"name": null}}.

Message: "{user_text}"
"""
    try:
        resp = get_json_model().generate_content(prompt)
        data = json.loads(resp.text)
        if not data.get("name") or not data.get("amount"):
            return None
        amount = safe_float(data["amount"], default=0)
        months = int(safe_float(data.get("months", 12), default=12, min_v=1, max_v=600))
        if amount <= 0:
            return None
        return {
            "name": str(data["name"])[:80],
            "amount": amount,
            "months": months,
            "saved": 0,
            "monthly_sip": calc_sip(amount, months),
        }
    except Exception as e:
        print(f"[detect_goal] {e}")
        return None

# ==========================================
# Markets
# ==========================================
NIFTY50 = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "LT.NS", "KOTAKBANK.NS",
    "AXISBANK.NS", "HINDUNILVR.NS", "BAJFINANCE.NS", "MARUTI.NS", "WIPRO.NS",
]

@st.cache_data(ttl=300, show_spinner=False)
def fetch_movers():
    rows = []
    for sym in NIFTY50:
        try:
            h = yf.Ticker(sym).history(period="5d")
            if len(h) >= 2:
                last, prev = h["Close"].iloc[-1], h["Close"].iloc[-2]
                pct = (last - prev) / prev * 100
                rows.append((sym.replace(".NS", ""), float(last), float(pct)))
        except Exception as e:
            print(f"[mover {sym}] {e}")
    rows.sort(key=lambda x: x[2], reverse=True)
    return rows[:5], rows[-5:][::-1]

@st.cache_data(ttl=300, show_spinner=False)
def fetch_index(symbol="^NSEI"):
    try:
        h = yf.Ticker(symbol).history(period="5d")
        if len(h) >= 2:
            last, prev = h["Close"].iloc[-1], h["Close"].iloc[-2]
            return float(last), float((last - prev) / prev * 100)
    except Exception as e:
        print(f"[index {symbol}] {e}")
    return None, None

# ==========================================
# Session state
# ==========================================
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant",
         "content": "Namaste! 🙏 I'm GoalPe — your AI money coach. "
                    "Tell me what you're saving for (e.g. *'a bike worth ₹1.2 lakh in 18 months'*) "
                    "and I'll build a plan for you."}
    ]
if "user_goals" not in st.session_state:
    st.session_state.user_goals = load_goals(USER_ID)

# ==========================================
# Navigation
# ==========================================
selected = option_menu(
    menu_title=None,
    options=["Home", "Goals", "Markets", "About"],
    icons=["chat-dots", "bullseye", "graph-up-arrow", "info-circle"],
    orientation="horizontal",
    default_index=0,
    styles={
        "container": {"padding": "6px", "background": "#FFFFFF",
                      "border-radius": "14px", "margin-bottom": "14px",
                      "box-shadow": "0 2px 8px rgba(0,0,0,0.04)"},
        "icon": {"font-size": "16px"},
        "nav-link": {"font-size": "13px", "font-weight": "500",
                     "color": "#64748B", "padding": "8px 12px",
                     "border-radius": "10px", "margin": "0 2px"},
        "nav-link-selected": {"background-color": "#0F766E", "color": "#fff"},
    },
)

# ==========================================
# HOME — Chat
# ==========================================
if selected == "Home":
    st.markdown("""
    <div class="gp-hero">
        <h1>🎯 GoalPe</h1>
        <p>Your friendly AI coach for goal-based saving & investing.</p>
    </div>
    """, unsafe_allow_html=True)

    # Render history
    for msg in st.session_state.messages:
        avatar = "🧑" if msg["role"] == "user" else "🎯"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

    # Input
    if prompt := st.chat_input("Ask GoalPe anything about money..."):
        prompt = prompt.strip()
        if not prompt:
            st.stop()
        if len(prompt) > 1000:
            st.toast("Message too long — keep it under 1000 chars", icon="⚠️")
            st.stop()

        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="🧑"):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar="🎯"):
            with st.spinner("Thinking..."):
                try:
                    chat = get_chat_model().start_chat(
                        history=[{"role": m["role"] if m["role"] == "user" else "model",
                                  "parts": [m["content"]]}
                                 for m in st.session_state.messages[:-1]]
                    )
                    reply = chat.send_message(prompt).text
                except Exception as e:
                    print(f"[chat] {e}")
                    reply = "Sorry, I couldn't reach my brain right now. Please try again."
                st.markdown(reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})

        # Try to extract a goal in the background
        goal = detect_goal(prompt)
        if goal:
            if save_goal(USER_ID, goal):
                st.session_state.user_goals = load_goals(USER_ID)
                st.toast(f"🎯 Goal added: {goal['name']}", icon="✅")
                st.rerun()

# ==========================================
# GOALS
# ==========================================
elif selected == "Goals":
    st.markdown('<div class="gp-h">Your Goals</div>'
                '<p class="gp-sub">Track what you\'re saving for.</p>',
                unsafe_allow_html=True)
    st.write("")

    goals = st.session_state.user_goals
    if not goals:
        st.info("🎯 No goals yet. Head to **Home** and tell GoalPe what you want to save for "
                "— like *'I want a bike worth ₹1.2 lakh in 18 months'* — and it'll appear here.")
    else:
        total_target = sum(safe_float(g.get("amount")) for g in goals)
        total_saved = sum(safe_float(g.get("saved")) for g in goals)
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f'<div class="gp-card"><p class="gp-sub">Total target</p>'
                        f'<div class="gp-stat-num">{fmt_inr(total_target)}</div></div>',
                        unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="gp-card"><p class="gp-sub">Saved so far</p>'
                        f'<div class="gp-stat-num">{fmt_inr(total_saved)}</div></div>',
                        unsafe_allow_html=True)
        with c3:
            pct = (total_saved / total_target * 100) if total_target else 0
            st.markdown(f'<div class="gp-card"><p class="gp-sub">Progress</p>'
                        f'<div class="gp-stat-num">{pct:.0f}%</div></div>',
                        unsafe_allow_html=True)

        st.write("")
        for g in goals:
            amount = safe_float(g.get("amount"))
            saved = safe_float(g.get("saved"))
            months = int(safe_float(g.get("months", 12), default=12))
            sip = safe_float(g.get("monthly_sip", calc_sip(amount, months)))
            progress = min(saved / amount, 1.0) if amount else 0

            st.markdown(f"""
            <div class="gp-card">
                <span class="gp-pill">Goal</span>
                <div class="gp-h">{g.get('name', 'Untitled')}</div>
                <p class="gp-sub">{fmt_inr(amount)} target • {months} months</p>
                <div style="margin-top:8px"></div>
            </div>
            """, unsafe_allow_html=True)
            st.progress(progress)
            st.caption(f"💡 Suggested SIP: **{fmt_inr(sip)}/month** "
                       f"(assuming 12% annual return)")
            st.write("")

# ==========================================
# MARKETS
# ==========================================
elif selected == "Markets":
    st.markdown('<div class="gp-h">Markets</div>'
                '<p class="gp-sub">Live snapshot from Yahoo Finance.</p>',
                unsafe_allow_html=True)
    st.write("")

    with st.spinner("Loading markets..."):
        nifty, nifty_chg = fetch_index("^NSEI")
        sensex, sensex_chg = fetch_index("^BSESN")
        gainers, losers = fetch_movers()

    c1, c2 = st.columns(2)
    for col, name, val, chg in [
        (c1, "NIFTY 50", nifty, nifty_chg),
        (c2, "SENSEX", sensex, sensex_chg),
    ]:
        with col:
            if val is None:
                st.markdown(f'<div class="gp-card"><p class="gp-sub">{name}</p>'
                            f'<div class="gp-stat-num">—</div></div>',
                            unsafe_allow_html=True)
            else:
                cls = "gp-up" if chg >= 0 else "gp-down"
                arrow = "▲" if chg >= 0 else "▼"
                st.markdown(f"""
                <div class="gp-card">
                    <p class="gp-sub">{name}</p>
                    <div class="gp-stat-num">{val:,.2f}</div>
                    <div class="{cls}">{arrow} {chg:+.2f}%</div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("### 📈 Top gainers")
    if not gainers:
        st.caption("Couldn't fetch live data. Please retry in a minute.")
    for sym, price, pct in gainers:
        st.markdown(f"""
        <div class="gp-card">
            <div class="gp-row">
                <div><b>{sym}</b><br><span class="gp-sub">₹{price:,.2f}</span></div>
                <div class="gp-up">▲ {pct:+.2f}%</div>
            </div>
        </div>""", unsafe_allow_html=True)

    st.markdown("### 📉 Top losers")
    for sym, price, pct in losers:
        st.markdown(f"""
        <div class="gp-card">
            <div class="gp-row">
                <div><b>{sym}</b><br><span class="gp-sub">₹{price:,.2f}</span></div>
                <div class="gp-down">▼ {pct:+.2f}%</div>
            </div>
        </div>""", unsafe_allow_html=True)

# ==========================================
# ABOUT
# ==========================================
elif selected == "About":
    st.markdown("""
    <div class="gp-card">
        <span class="gp-pill-accent">Prototype</span>
        <div class="gp-h">About GoalPe</div>
        <p>GoalPe is an AI-powered wealth coach designed for the next 100M Indian
        retail investors. Chat naturally about your money goals — buying a bike,
        a phone, a wedding, retirement — and GoalPe builds a SIP plan for you.</p>
        <p class="gp-sub">Built with Streamlit, Google Gemini, yfinance, and Google Sheets.</p>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("ℹ️ Disclaimer"):
        st.caption("GoalPe is an AI prototype for educational purposes only. "
                   "It is **not** a SEBI-registered investment advisor. "
                   "Do not use it for actual trading or investment decisions. "
                   "Always consult a qualified financial advisor.")

    with st.expander("⚠️ Danger zone"):
        confirm = st.checkbox("Yes, I want to delete all my data")
        if st.button("🗑️ Clear All Data", disabled=not confirm):
            st.session_state.messages = []
            st.session_state.user_goals = []
            delete_all_goals(USER_ID)
            st.toast("All data cleared", icon="✅")
            st.rerun()
