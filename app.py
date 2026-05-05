import streamlit as st
import google.generativeai as genai
import json
import re
import yfinance as yf
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from streamlit_option_menu import option_menu
import random

# ==========================================
# Page Config (must be first)
# ==========================================
st.set_page_config(page_title="GoalPe", page_icon="🎯", layout="centered", initial_sidebar_state="collapsed")

# ==========================================
# Session State Initialization
# ==========================================
if "goals_set" not in st.session_state: st.session_state.goals_set = 0
if "impulses_skipped" not in st.session_state: st.session_state.impulses_skipped = 0
if "messages" not in st.session_state: st.session_state.messages = []
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "user_goals" not in st.session_state: st.session_state.user_goals = []
if "dark_mode" not in st.session_state: st.session_state.dark_mode = True

# ==========================================
# Dynamic CSS Injection (Light/Dark Mode & App UI)
# ==========================================
bg_color = "#0d0f14" if st.session_state.dark_mode else "#f4f6f8"
surface_color = "#151820" if st.session_state.dark_mode else "#ffffff"
text_color = "#e8eaf0" if st.session_state.dark_mode else "#151820"
muted_color = "#6b7280"
border_color = "#252a38" if st.session_state.dark_mode else "#e5e7eb"

st.markdown(f"""
<link href="https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700&family=DM+Mono:wght@300;400;500&display=swap" rel="stylesheet">
<style>
    :root {{
        --bg: {bg_color};
        --surface: {surface_color};
        --text: {text_color};
        --muted: {muted_color};
        --border: {border_color};
        --accent: #6c5ce7; 
        --success: #00b894;
        --danger: #ff7675;
        --font: 'Sora', sans-serif;
    }}

    html, body, [data-testid="stAppViewContainer"] {{
        background-color: var(--bg) !important;
        color: var(--text) !important;
        font-family: var(--font) !important;
    }}
    
    /* Hide default Streamlit elements */
    #MainMenu, footer, header {{ visibility: hidden !important; }}
    
    /* Massive bottom padding so you can scroll to the very last message */
    .block-container {{ padding-top: 1rem !important; padding-bottom: 160px !important; max-width: 600px; }}

    /* ==========================================
       FIX 1: Force Metrics to respect Light/Dark Mode
       ========================================== */
    [data-testid="stMetricValue"] > div {{ color: var(--text) !important; }}
    [data-testid="stMetricLabel"] p {{ color: var(--muted) !important; }}

    /* ==========================================
       FIX 2: Force IFRAME Height so menu isn't cut off
       ========================================== */
    iframe[title="streamlit_option_menu.option_menu"] {{
        position: fixed !important;
        bottom: 0px !important;
        left: 50% !important;
        transform: translateX(-50%) !important;
        width: 100% !important;
        max-width: 600px !important; 
        height: 80px !important; /* <--- This gives the menu room to breathe */
        z-index: 999999 !important; 
        background-color: var(--bg) !important;
        border-top: 1px solid var(--border);
    }}

    /* ==========================================
       FIX 3: Float the entire Streamlit Bottom Container UP
       ========================================== */
    [data-testid="stBottom"] {{
        bottom: 80px !important; /* Pushes chat box perfectly above nav bar */
        z-index: 99999 !important;
        background-color: var(--bg) !important;
    }}
    [data-testid="stChatInput"] {{
        bottom: 80px !important; /* Fallback for older Streamlit versions */
    }}

    /* Ticker Animation */
    .ticker-wrap {{
        width: 100%; overflow: hidden; background-color: var(--surface);
        border-bottom: 1px solid var(--border); padding: 8px 0; margin-bottom: 15px;
        border-radius: 8px;
    }}
    .ticker {{
        display: inline-block; white-space: nowrap; padding-right: 100%;
        animation: ticker 25s linear infinite;
    }}
    .ticker__item {{ display: inline-block; padding: 0 2rem; font-size: 0.8rem; font-weight: 600; color: var(--text); }}
    @keyframes ticker {{ 0% {{ transform: translate3d(0, 0, 0); }} 100% {{ transform: translate3d(-100%, 0, 0); }} }}

    /* App Cards & Buttons */
    .app-card {{
        background: var(--surface); border: 1px solid var(--border);
        border-radius: 16px; padding: 1.2rem; margin-bottom: 1rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }}
    .progress-bg {{ background: var(--border); height: 8px; border-radius: 4px; width: 100%; margin: 10px 0; overflow: hidden; }}
    .progress-fill {{ background: var(--success); height: 100%; border-radius: 4px; }}
    .stButton>button {{
        border-radius: 12px !important; background-color: var(--surface) !important;
        color: var(--accent) !important; border: 1px solid var(--accent) !important;
        font-weight: 600 !important; width: 100% !important;
    }}
    .stButton>button:hover {{ background-color: var(--accent) !important; color: white !important; }}
</style>
""", unsafe_allow_html=True)

# ==========================================
# Data Fetching
# ==========================================
@st.cache_data(ttl=300)
def get_market_data():
    tickers = {"Nifty 50": "^NSEI", "Sensex": "^BSESN", "Bank Nifty": "^NSEBANK", "Gold": "GC=F"}
    data = {}
    for name, symbol in tickers.items():
        try:
            t = yf.Ticker(symbol)
            hist = t.history(period="2d")
            curr = hist['Close'].iloc[-1]
            prev = hist['Close'].iloc[-2]
            pct = ((curr - prev) / prev) * 100
            data[name] = {"price": curr, "change": pct}
        except:
            data[name] = {"price": 0, "change": 0}
    return data

# ==========================================
# Database & API Setup
# ==========================================
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except:
    st.error("API Key missing.")
    st.stop()

def log_to_database(log_type):
    try:
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds_dict = dict(st.secrets["google_credentials"])
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        sheet = client.open("GoalPe_Database").sheet1
        sheet.append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), log_type])
    except:
        pass

# ==========================================
# AI Logic
# ==========================================
SYSTEM_PROMPT = """
You are GoalPe, an AI wealth coach. 
Extract JSON ONLY if the user sets a new goal.
If the user sets a goal (e.g. "Save 50k for a bike in 10 months"), silently output this exact JSON block at the very end of your response:
[JSON_START]{"goal_name": "Bike", "amount": 50000, "months": 10, "sip": 5000}[JSON_END]

For casual chat, just chat naturally and append [LOG:chat].
For impulse skips, append [LOG:impulse].
"""

def chat_with_goalpe(user_message):
    try:
        model = genai.GenerativeModel(model_name='gemini-2.5-flash', system_instruction=SYSTEM_PROMPT)
        chat = model.start_chat(history=st.session_state.chat_history)
        response = chat.send_message(user_message)
        raw_reply = response.text.strip()

        # Handle Goal Extraction
        if "[JSON_START]" in raw_reply:
            try:
                json_str = raw_reply.split("[JSON_START]")[1].split("[JSON_END]")[0]
                goal_data = json.loads(json_str)
                st.session_state.user_goals.append(goal_data)
                raw_reply = raw_reply.split("[JSON_START]")[0] # Remove JSON from text
                log_to_database("New Goal")
            except:
                pass
        
        log_tag = "chat"
        if "[LOG:impulse]" in raw_reply:
            log_tag = "impulse"
            st.session_state.impulses_skipped += 1
            log_to_database("Impulse")
            raw_reply = raw_reply.replace("[LOG:impulse]", "")

        raw_reply = raw_reply.replace("[LOG:chat]", "").strip()
        st.session_state.chat_history = chat.history
        return raw_reply
    except Exception as e:
        return "I'm having a little trouble connecting. Please try again."

# ==========================================
# Navigation Bar
# ==========================================
selected = option_menu(
    menu_title=None,
    options=["Home", "Markets", "Goals", "Profile"],
    icons=["house", "graph-up", "bullseye", "person"],
    menu_icon="cast",
    default_index=0,
    orientation="horizontal",
    styles={
        "container": {"padding": "0!important", "background-color": surface_color, "border-radius": "0px", "margin-bottom": "0px"},
        "icon": {"color": "#6c5ce7", "font-size": "18px"}, 
        "nav-link": {"font-size": "14px", "text-align": "center", "margin":"0px", "--hover-color": border_color, "color": text_color},
        "nav-link-selected": {"background-color": "#6c5ce7", "color": "white"},
    }
)

# ==========================================
# VIEWS
# ==========================================
if selected == "Home":
    st.markdown("""<div style="display:flex; align-items:center; gap:10px; margin-bottom: 15px;">
        <div style="background:#6c5ce7; padding:8px; border-radius:10px; font-size:20px;">🎯</div>
        <h2 style="margin:0; padding:0;">GoalPe</h2>
    </div>""", unsafe_allow_html=True)

    # Ticker
    market_data = get_market_data()
    ticker_html = "<div class='ticker-wrap'><div class='ticker'>"
    for name, data in market_data.items():
        color = "#00b894" if data['change'] >= 0 else "#ff7675"
        sign = "+" if data['change'] >= 0 else ""
        ticker_html += f"<div class='ticker__item'>{name}: ₹{data['price']:,.0f} <span style='color:{color}'>({sign}{data['change']:.2f}%)</span></div>"
    ticker_html += "</div></div>"
    st.markdown(ticker_html, unsafe_allow_html=True)

    # Quick Actions
    c1, c2, c3 = st.columns(3)
    if c1.button("🎯 Set a Goal"):
        st.session_state.messages.append({"role": "user", "content": "I want to set a savings goal."})
        reply = chat_with_goalpe("I want to set a savings goal.")
        st.session_state.messages.append({"role": "assistant", "content": reply})
        st.rerun()
    if c2.button("🍔 Skip Expense"):
        st.session_state.messages.append({"role": "user", "content": "I want to skip an impulse purchase today."})
        reply = chat_with_goalpe("I want to skip an impulse purchase today.")
        st.session_state.messages.append({"role": "assistant", "content": reply})
        st.rerun()
    if c3.button("📈 Learn SIPs"):
        st.session_state.messages.append({"role": "user", "content": "Explain how SIPs work simply."})
        reply = chat_with_goalpe("Explain how SIPs work simply.")
        st.session_state.messages.append({"role": "assistant", "content": reply})
        st.rerun()

    st.markdown("---")

    # Chat UI
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if not st.session_state.messages:
        st.chat_message("assistant").markdown("Hi! I'm GoalPe. Tap a quick action above, or type what you want to save for!")

    if prompt := st.chat_input("E.g., I need ₹50k for a laptop in 14 months"):
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.spinner("Analyzing..."):
            reply = chat_with_goalpe(prompt)
        st.chat_message("assistant").markdown(reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})


elif selected == "Markets":
    st.subheader("Live Markets")
    market_data = get_market_data()
    for name, data in market_data.items():
        color = "green" if data['change'] >= 0 else "red"
        st.metric(name, f"₹{data['price']:,.2f}", f"{data['change']:.2f}%")
    
    st.markdown("### Top Mutual Fund Categories (Simulated)")
    st.markdown("""
    <div class="app-card">
        <h5 style="color:#00b894; margin:0 0 10px 0;">🔥 Top Gainers</h5>
        <p style="margin:0; display:flex; justify-content:space-between;"><span>IT Sector Funds</span> <span>+2.4%</span></p>
        <p style="margin:0; display:flex; justify-content:space-between;"><span>Small Cap Funds</span> <span>+1.8%</span></p>
    </div>
    <div class="app-card">
        <h5 style="color:#ff7675; margin:0 0 10px 0;">🔻 Top Losers</h5>
        <p style="margin:0; display:flex; justify-content:space-between;"><span>FMCG Sector Funds</span> <span>-0.9%</span></p>
        <p style="margin:0; display:flex; justify-content:space-between;"><span>Debt Ultra Short</span> <span>-0.1%</span></p>
    </div>
    """, unsafe_allow_html=True)


elif selected == "Goals":
    st.subheader("Your Active Quests")
    if len(st.session_state.user_goals) == 0:
        st.info("No active goals yet. Go to Home to set one up!")
    else:
        for g in st.session_state.user_goals:
            # Randomize progress for prototype visualization
            progress = random.randint(10, 80) 
            st.markdown(f"""
            <div class="app-card">
                <h4 style="margin:0;">{g.get('goal_name', 'Savings Goal')}</h4>
                <p style="color:var(--muted); font-size:12px; margin-bottom:10px;">Target: ₹{g.get('amount', 0):,}</p>
                <div class="progress-bg"><div class="progress-fill" style="width: {progress}%;"></div></div>
                <div style="display:flex; justify-content:space-between; font-size:12px;">
                    <span style="color:#6c5ce7; font-weight:bold;">SIP: ₹{g.get('sip', 0):,}/mo</span>
                    <span>{g.get('months', 0)} months left</span>
                </div>
            </div>
            """, unsafe_allow_html=True)


elif selected == "Profile":
    st.markdown("""
    <div style="text-align:center; padding: 20px 0;">
        <img src="https://api.dicebear.com/7.x/avataaars/svg?seed=Sulakshya" width="80" style="border-radius:50%; background:#e0e0e0;">
        <h3 style="margin:10px 0 0 0;">User (DEMO)</h3>
        <p style="color:#6c5ce7; font-size:14px; margin:0;">Goals Set: {} | Impulses Skipped: {}</p>
    </div>
    """.format(st.session_state.goals_set, st.session_state.impulses_skipped), unsafe_allow_html=True)
    
    st.markdown("---")
    
    if st.button("🌓 Toggle Light/Dark Mode"):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()
        
    st.markdown("""
    <div class="app-card">
        <h4>About GoalPe</h4>
        <p style="font-size:12px; color:var(--muted);">GoalPe is an AI-driven behavioral finance prototype designed for the next 100M Indian retail investors.</p>
        <p style="font-size:11px; color:var(--muted); margin-top:10px;"><b>Disclaimer:</b> GoalPe is an AI prototype. It is not a SEBI registered advisor. Do not use for actual trading decisions.</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🗑️ Clear All Data"):
        st.session_state.messages = []
        st.session_state.chat_history = []
        st.session_state.user_goals = []
        st.rerun()
