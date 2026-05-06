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
# Tracks the active tab to fix the navigation visual bug
if "menu_index" not in st.session_state: st.session_state.menu_index = 0

# ==========================================
# Dynamic CSS Injection (Premium UI Upgrades)
# ==========================================
bg_color = "#0d0f14" if st.session_state.dark_mode else "#f4f6f8"
surface_color = "#151820" if st.session_state.dark_mode else "#ffffff"
text_color = "#e8eaf0" if st.session_state.dark_mode else "#111827"
muted_color = "#9ca3af" if st.session_state.dark_mode else "#6b7280"
border_color = "#2d3748" if st.session_state.dark_mode else "#e5e7eb"
accent_color = "#6c5ce7"
# Transparent background for the frosted glass effect
glass_bg = "rgba(21, 24, 32, 0.85)" if st.session_state.dark_mode else "rgba(255, 255, 255, 0.85)"

st.markdown(f"""
<link href="https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700&family=DM+Mono:wght@300;400;500&display=swap" rel="stylesheet">
<style>
    /* KEYFRAME ANIMATIONS (The "Juice") */
    @keyframes slideUpFade {{
        from {{ opacity: 0; transform: translateY(20px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}
    @keyframes pulseSoft {{
        0% {{ transform: scale(1); }}
        50% {{ transform: scale(1.02); }}
        100% {{ transform: scale(1); }}
    }}

    /* 1. CORE BACKGROUNDS */
    html, body, #root, .stApp, [data-testid="stAppViewContainer"] {{
        background-color: {bg_color} !important;
        color: {text_color} !important;
        font-family: 'Sora', sans-serif !important;
        overscroll-behavior-y: none !important; 
    }}
    
    header[data-testid="stHeader"], #MainMenu, footer {{ display: none !important; }}
    
    .block-container {{ 
        padding-top: 1rem !important; 
        padding-bottom: 140px !important; 
        max-width: 600px; 
    }}

    /* Apply animations to core UI elements */
    [data-testid="stChatMessage"], .app-card, [data-testid="stMetricValue"], h2, h3, h4 {{
        animation: slideUpFade 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    }}

    [data-testid="stMetricValue"] > div {{ color: {text_color} !important; font-weight: 700 !important; }}
    [data-testid="stMetricLabel"] p {{ color: {muted_color} !important; }}

    /* 2. PREMIUM FROSTED GLASS NAVIGATION MENU */
    iframe[title="streamlit_option_menu.option_menu"] {{
        position: fixed !important;
        bottom: 0px !important;
        left: 50% !important;
        transform: translateX(-50%) !important;
        width: 100% !important;
        max-width: 600px !important; 
        height: 75px !important; 
        z-index: 999999 !important; 
        background-color: {glass_bg} !important;
        backdrop-filter: blur(12px) !important; /* iOS Style Glass Effect */
        -webkit-backdrop-filter: blur(12px) !important;
        border-top: 1px solid {border_color} !important;
        box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.05) !important;
    }}
    
    div[data-testid="stVerticalBlock"] > div:has(iframe) {{
        background-color: transparent !important;
        padding: 0 !important;
    }}

    /* 3. CHAT INPUT UPGRADES */
    [data-testid="stBottom"] {{
        background-color: transparent !important; /* Let the page background show */
        padding-bottom: 75px !important; 
        z-index: 99990 !important;
    }}
    [data-testid="stBottom"] > div {{
        background-color: {bg_color} !important;
        background-image: linear-gradient(to top, {bg_color} 80%, transparent) !important; /* Smooth fade into background */
    }}

    [data-testid="stChatInput"] {{
        background-color: transparent !important;
    }}
    [data-testid="stChatInput"] > div,
    div[data-baseweb="input"], 
    div[data-baseweb="base-input"],
    [data-testid="stChatInput"] textarea {{
        background-color: {surface_color} !important;
        color: {text_color} !important;
        -webkit-text-fill-color: {text_color} !important;
        border-color: {border_color} !important;
        border-radius: 16px !important; /* Rounder, modern input */
        transition: border-color 0.3s ease, box-shadow 0.3s ease !important;
    }}
    /* Glow effect on chat focus */
    [data-testid="stChatInput"] > div:focus-within {{
        border-color: {accent_color} !important;
        box-shadow: 0 0 0 2px rgba(108, 92, 231, 0.2) !important;
    }}
    
    [data-testid="stChatInput"] textarea::placeholder {{
        color: {muted_color} !important;
        -webkit-text-fill-color: {muted_color} !important;
    }}
    
    [data-testid="stChatInputSubmitButton"] {{
        color: {accent_color} !important;
    }}
    [data-testid="stChatInputSubmitButton"] svg {{
        fill: {accent_color} !important;
    }}

    /* 4. CHAT MESSAGES */
    [data-testid="stChatMessage"] {{
        background-color: transparent !important;
    }}
    [data-testid="stChatMessage"] * {{
        color: {text_color} !important;
    }}

    /* 5. TICKER & CARDS WITH HOVER EFFECTS */
    .ticker-wrap {{
        width: 100%; overflow: hidden; 
        background-color: {surface_color} !important;
        border: 1px solid {border_color}; 
        padding: 10px 0; margin-bottom: 20px; border-radius: 12px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.02);
    }}
    .ticker {{
        display: inline-block; white-space: nowrap; padding-right: 100%;
        animation: ticker 25s linear infinite;
    }}
    .ticker__item {{ 
        display: inline-block; padding: 0 2rem; font-size: 0.85rem; 
        font-weight: 600; color: {text_color} !important; 
    }}

    .app-card {{
        background: {surface_color}; border: 1px solid {border_color};
        border-radius: 20px; padding: 1.5rem; margin-bottom: 1.2rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.03);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }}
    /* Make cards pop out slightly when touched/hovered */
    .app-card:hover {{
        transform: translateY(-3px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.06);
    }}
    
    .progress-bg {{ background: {border_color}; height: 10px; border-radius: 5px; width: 100%; margin: 12px 0; overflow: hidden; }}
    .progress-fill {{ background: {accent_color}; height: 100%; border-radius: 5px; transition: width 1s ease-in-out; }}
    
    /* Premium Buttons */
    .stButton>button {{
        border-radius: 14px !important; background-color: {surface_color} !important;
        color: {accent_color} !important; border: 1px solid {border_color} !important;
        font-weight: 600 !important; width: 100% !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.02) !important;
    }}
    .stButton>button:hover {{ 
        background-color: {accent_color} !important; 
        color: white !important; 
        border-color: {accent_color} !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 15px rgba(108, 92, 231, 0.2) !important;
    }}
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
menu_options = ["Home", "Markets", "Goals", "Profile"]

selected = option_menu(
    menu_title=None,
    options=menu_options,
    icons=["house", "graph-up", "bullseye", "person"],
    menu_icon="cast",
    default_index=st.session_state.menu_index, # <--- BUG FIX: Uses Session State to remember active tab
    orientation="horizontal",
    styles={
        "container": {
            "padding": "0!important", 
            "background-color": "transparent", 
            "border-radius": "0px", 
            "margin-bottom": "0px",
            "height": "100vh" 
        },
        "icon": {"color": accent_color, "font-size": "20px"}, 
        "nav-link": {"font-size": "13px", "text-align": "center", "margin":"0px", "--hover-color": border_color, "color": text_color, "font-weight": "500"},
        "nav-link-selected": {"background-color": accent_color, "color": "white"},
    }
)

# Update the session state immediately if the user clicked a new tab
if selected in menu_options:
    st.session_state.menu_index = menu_options.index(selected)

# ==========================================
# VIEWS
# ==========================================
if selected == "Home":
    st.markdown(f"""<div style="display:flex; align-items:center; gap:12px; margin-bottom: 20px;">
        <div style="background: linear-gradient(135deg, {accent_color}, #a29bfe); padding:10px; border-radius:12px; font-size:22px; box-shadow: 0 4px 10px rgba(108, 92, 231, 0.3);">🎯</div>
        <h2 style="margin:0; padding:0; color:{text_color}; font-weight: 700; letter-spacing: -0.5px;">GoalPe</h2>
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
    st.markdown(f"<h3 style='color:{text_color}; margin-bottom: 20px; font-weight:700;'>Live Markets</h3>", unsafe_allow_html=True)
    market_data = get_market_data()
    for name, data in market_data.items():
        color = "green" if data['change'] >= 0 else "red"
        st.metric(name, f"₹{data['price']:,.2f}", f"{data['change']:.2f}%")
    
    st.markdown(f"<h4 style='color:{text_color}; margin-top:30px; font-weight:600;'>Top Categories (Simulated)</h4>", unsafe_allow_html=True)
    st.markdown(f"""
    <div class="app-card">
        <h5 style="color:#00b894; margin:0 0 12px 0; font-size: 16px;">🔥 Top Gainers</h5>
        <div style="display:flex; justify-content:space-between; color:{text_color}; margin-bottom:8px; font-size:14px;"><span>IT Sector Funds</span> <span style="font-weight:600;">+2.4%</span></div>
        <div style="display:flex; justify-content:space-between; color:{text_color}; font-size:14px;"><span>Small Cap Funds</span> <span style="font-weight:600;">+1.8%</span></div>
    </div>
    <div class="app-card">
        <h5 style="color:#ff7675; margin:0 0 12px 0; font-size: 16px;">🔻 Top Losers</h5>
        <div style="display:flex; justify-content:space-between; color:{text_color}; margin-bottom:8px; font-size:14px;"><span>FMCG Sector Funds</span> <span style="font-weight:600;">-0.9%</span></div>
        <div style="display:flex; justify-content:space-between; color:{text_color}; font-size:14px;"><span>Debt Ultra Short</span> <span style="font-weight:600;">-0.1%</span></div>
    </div>
    """, unsafe_allow_html=True)


elif selected == "Goals":
    st.markdown(f"<h3 style='color:{text_color}; margin-bottom: 20px; font-weight:700;'>Your Active Quests</h3>", unsafe_allow_html=True)
    if len(st.session_state.user_goals) == 0:
        st.info("No active goals yet. Go to Home to set one up!")
    else:
        for g in st.session_state.user_goals:
            progress = random.randint(10, 80) 
            st.markdown(f"""
            <div class="app-card">
                <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom: 8px;">
                    <h4 style="margin:0; color:{text_color}; font-weight: 600;">{g.get('goal_name', 'Savings Goal')}</h4>
                    <span style="background: rgba(108, 92, 231, 0.1); color: {accent_color}; padding: 4px 8px; border-radius: 8px; font-size: 11px; font-weight: 700;">ON TRACK</span>
                </div>
                <p style="color:{muted_color}; font-size:13px; margin-bottom:12px;">Target: <strong style="color:{text_color}">₹{g.get('amount', 0):,}</strong></p>
                <div class="progress-bg"><div class="progress-fill" style="width: {progress}%;"></div></div>
                <div style="display:flex; justify-content:space-between; font-size:13px; margin-top: 12px;">
                    <span style="color:{text_color};">SIP: <strong style="color:{accent_color};">₹{g.get('sip', 0):,}/mo</strong></span>
                    <span style="color:{muted_color};"><strong>{g.get('months', 0)}</strong> months left</span>
                </div>
            </div>
            """, unsafe_allow_html=True)


elif selected == "Profile":
    st.markdown(f"""
    <div style="text-align:center; padding: 30px 0 10px 0;">
        <div style="width: 90px; height: 90px; margin: 0 auto; border-radius: 50%; background: linear-gradient(135deg, {accent_color}, #a29bfe); padding: 3px; box-shadow: 0 8px 20px rgba(108, 92, 231, 0.3);">
            <img src="https://api.dicebear.com/7.x/avataaars/svg?seed=Sulakshya" width="100%" style="border-radius:50%; background:{surface_color};">
        </div>
        <h3 style="margin:15px 0 5px 0; color:{text_color}; font-weight: 700;">User (DEMO)</h3>
        <p style="color:{muted_color}; font-size:14px; margin:0; font-weight: 500;">Beta Tester</p>
    </div>
    
    <div style="display: flex; gap: 10px; margin-bottom: 20px;">
        <div class="app-card" style="flex: 1; text-align: center; padding: 1rem;">
            <h3 style="color:{accent_color}; margin: 0; font-size: 24px;">{st.session_state.goals_set}</h3>
            <p style="color:{muted_color}; font-size: 11px; margin: 0; text-transform: uppercase; letter-spacing: 0.5px;">Goals Set</p>
        </div>
        <div class="app-card" style="flex: 1; text-align: center; padding: 1rem;">
            <h3 style="color:{accent_color}; margin: 0; font-size: 24px;">{st.session_state.impulses_skipped}</h3>
            <p style="color:{muted_color}; font-size: 11px; margin: 0; text-transform: uppercase; letter-spacing: 0.5px;">Impulses Skipped</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🌓 Toggle Light/Dark Mode"):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()
        
    st.markdown(f"""
    <div class="app-card" style="margin-top: 10px;">
        <h4 style="color:{text_color}; font-weight: 600; margin-bottom: 8px;">About GoalPe</h4>
        <p style="font-size:13px; color:{muted_color}; line-height: 1.5;">GoalPe is an AI-driven behavioral finance prototype designed for the next 100M Indian retail investors.</p>
        <div style="background: rgba(255, 118, 117, 0.1); border-left: 3px solid #ff7675; padding: 10px; border-radius: 0 8px 8px 0; margin-top: 15px;">
            <p style="font-size:11px; color:{text_color}; margin: 0;"><b>Disclaimer:</b> GoalPe is an AI prototype. It is not a SEBI registered advisor. Do not use for actual trading decisions.</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🗑️ Clear All Data"):
        st.session_state.messages = []
        st.session_state.chat_history = []
        st.session_state.user_goals = []
        st.rerun()
