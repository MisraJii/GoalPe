import streamlit as st
import google.generativeai as genai
import json
import re
import yfinance as yf
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ==========================================
# Page Config (must be first Streamlit call)
# ==========================================
st.set_page_config(page_title="GoalPe", page_icon="🎯", layout="centered")

# ==========================================
# Global CSS Injection
# ==========================================
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700&family=DM+Mono:wght@300;400;500&display=swap" rel="stylesheet">
<style>
    /* ---- Base & Reset ---- */
    :root {
        --bg:        #0d0f14;
        --surface:   #151820;
        --surface2:  #1c2030;
        --border:    #252a38;
        --accent:    #00c896;
        --accent2:   #0090ff;
        --danger:    #ff4f5e;
        --text:      #e8eaf0;
        --muted:     #6b7280;
        --font:      'Sora', sans-serif;
        --mono:      'DM Mono', monospace;
    }

    html, body, [data-testid="stAppViewContainer"] {
        background-color: var(--bg) !important;
        color: var(--text) !important;
        font-family: var(--font) !important;
    }

    /* Hide Streamlit chrome */
    #MainMenu, footer, header { visibility: hidden !important; }
    [data-testid="stToolbar"] { display: none !important; }
    .block-container { padding-top: 2rem !important; padding-bottom: 2rem !important; }

    /* ---- Scrollbar ---- */
    ::-webkit-scrollbar { width: 4px; }
    ::-webkit-scrollbar-track { background: var(--bg); }
    ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }

    /* ---- Top brand bar ---- */
    .brand-bar {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        margin-bottom: 0.25rem;
    }
    .brand-logo {
        width: 36px; height: 36px;
        background: linear-gradient(135deg, var(--accent), var(--accent2));
        border-radius: 10px;
        display: flex; align-items: center; justify-content: center;
        font-size: 18px; line-height: 1;
        box-shadow: 0 0 16px rgba(0,200,150,0.35);
    }
    .brand-name {
        font-size: 1.55rem;
        font-weight: 700;
        letter-spacing: -0.03em;
        background: linear-gradient(90deg, var(--accent), var(--accent2));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .brand-sub {
        font-size: 0.82rem;
        color: var(--muted);
        font-weight: 300;
        margin-bottom: 1.2rem;
    }

    /* ---- Market pulse card ---- */
    .pulse-card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 1rem 1.4rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 1.4rem;
        box-shadow: 0 2px 12px rgba(0,0,0,0.4);
    }
    .pulse-label {
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: var(--muted);
        margin-bottom: 0.2rem;
    }
    .pulse-price {
        font-family: var(--mono);
        font-size: 1.3rem;
        font-weight: 500;
        color: var(--text);
    }
    .pulse-change-up   { font-family: var(--mono); font-size: 0.85rem; color: var(--accent); }
    .pulse-change-down { font-family: var(--mono); font-size: 0.85rem; color: var(--danger); }
    .pulse-dot {
        width: 8px; height: 8px;
        border-radius: 50%;
        background: var(--accent);
        box-shadow: 0 0 8px var(--accent);
        animation: blink 1.4s infinite;
    }
    @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.3} }

    /* ---- Chat messages ---- */
    [data-testid="stChatMessage"] {
        background: transparent !important;
        border: none !important;
        padding: 0.1rem 0 !important;
    }
    [data-testid="stChatMessage"][data-role="assistant"] .stMarkdown {
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: 0 16px 16px 16px !important;
        padding: 0.9rem 1.1rem !important;
        font-size: 0.9rem !important;
        line-height: 1.65 !important;
        box-shadow: 0 2px 10px rgba(0,0,0,0.3) !important;
    }
    [data-testid="stChatMessage"][data-role="user"] .stMarkdown {
        background: linear-gradient(135deg, #0a2a20, #0a1f35) !important;
        border: 1px solid rgba(0,200,150,0.2) !important;
        border-radius: 16px 0 16px 16px !important;
        padding: 0.9rem 1.1rem !important;
        font-size: 0.9rem !important;
        line-height: 1.65 !important;
    }

    /* ---- Chat input ---- */
    [data-testid="stChatInput"] textarea {
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: 12px !important;
        color: var(--text) !important;
        font-family: var(--font) !important;
        font-size: 0.88rem !important;
    }
    [data-testid="stChatInput"] textarea:focus {
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 2px rgba(0,200,150,0.15) !important;
    }

    /* ---- Buttons ---- */
    .stButton > button {
        background: linear-gradient(135deg, var(--accent), #00a87a) !important;
        color: #0d0f14 !important;
        font-family: var(--font) !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.5rem 1.2rem !important;
        transition: opacity 0.2s, transform 0.15s !important;
        box-shadow: 0 3px 12px rgba(0,200,150,0.3) !important;
    }
    .stButton > button:hover {
        opacity: 0.88 !important;
        transform: translateY(-1px) !important;
    }
    .stButton > button:active { transform: translateY(0) !important; }

    /* ---- Sidebar ---- */
    [data-testid="stSidebar"] {
        background: var(--surface) !important;
        border-right: 1px solid var(--border) !important;
    }
    [data-testid="stSidebar"] * { color: var(--text) !important; font-family: var(--font) !important; }
    .sidebar-stat-label {
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--muted);
        margin-bottom: 0.15rem;
    }
    .sidebar-stat-value {
        font-family: var(--mono);
        font-size: 1.2rem;
        font-weight: 500;
        color: var(--accent);
        margin-bottom: 1rem;
    }

    /* ---- Spinner ---- */
    [data-testid="stSpinner"] { color: var(--accent) !important; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# Session State Initialization
# ==========================================
if "goals_set" not in st.session_state:
    st.session_state.goals_set = 0
if "impulses_skipped" not in st.session_state:
    st.session_state.impulses_skipped = 0
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hi! What are you saving for today? Or, are you tempted to buy something right now?"}
    ]
if "active_goal" not in st.session_state:
    st.session_state.active_goal = None
if "active_sip" not in st.session_state:
    st.session_state.active_sip = 0

# ==========================================
# Gemini Configuration (Server-Side Secrets & Safety Filters)
# ==========================================
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except KeyError:
    st.error("Server Configuration Error: Gemini API Key is missing from Streamlit Secrets.")
    st.stop()

# Bypass safety filters so it allows "financial" terminology
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

# Using 1.5-flash for maximum production stability
model = genai.GenerativeModel(model_name='gemini-1.5-flash', safety_settings=safety_settings)

# ==========================================
# Sidebar
# ==========================================
with st.sidebar:
    st.markdown("""
    <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:1.4rem; margin-top:0.5rem;">
        <div class="brand-logo" style="width:28px;height:28px;font-size:14px;">🎯</div>
        <span style="font-weight:700; font-size:1.1rem; letter-spacing:-0.02em;">GoalPe</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sidebar-stat-label">Goals Set</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sidebar-stat-value">{st.session_state.goals_set}</div>', unsafe_allow_html=True)

    st.markdown('<div class="sidebar-stat-label">Impulses Skipped</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sidebar-stat-value">{st.session_state.impulses_skipped}</div>', unsafe_allow_html=True)

# ==========================================
# Database Connection (Protected)
# ==========================================
def connect_to_db():
    try:
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds_dict = dict(st.secrets["google_credentials"])
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        return client.open("GoalPe_Database").sheet1
    except Exception as e:
        return None

def log_to_database(intent, item, amount, months):
    try:
        sheet = connect_to_db()
        if sheet:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sheet.append_row([timestamp, intent, item, amount, months])
    except Exception as e:
        # Fails silently so the UI doesn't crash for the user
        pass

# ==========================================
# Live Market Data
# ==========================================
@st.cache_data(ttl=300)
def get_nifty_data():
    try:
        nifty = yf.Ticker("^NSEI")
        hist = nifty.history(period="2d")
        current_price = hist['Close'].iloc[-1]
        prev_price = hist['Close'].iloc[-2]
        change = current_price - prev_price
        change_pct = (change / prev_price) * 100
        return current_price, change, change_pct
    except:
        return None, None, None

# ==========================================
# Math & Logic Engine
# ==========================================
def calculate_sip(target_amount, months, annual_rate):
    if months <= 0: return target_amount
    monthly_rate = annual_rate / 12
    sip_amount = (target_amount * monthly_rate) / (((1 + monthly_rate)**months) - 1)
    return round(sip_amount)

def extract_intent(user_input):
    prompt = f"""
    You are an expert AI wealth manager and behavioral finance coach for retail users in India. 
    Analyze the user's input.

    If the user asks for DIRECT STOCK, CRYPTO, or TRADING ADVICE:
    Return: {{"intent": "refusal", "message": "I am designed for goal-based wealth building via diversified mutual funds, not direct stock or crypto trading."}}
    
    If the user wants to SAVE for a big goal, return:
    1. "intent": "new_goal"
    2. "amount": The target amount (integer). Return 0 if not specified.
    3. "months": Time horizon (integer). Assume 6 if not specified.
    4. "item": 2-3 word name for the goal.
    5. "portfolio": A dictionary of 2-3 specific Indian mutual fund categories and their percentage allocation adding up to 100.
    6. "blended_return": Expected annual return rate as a decimal.
    7. "explanation": A 1-sentence simple explanation of WHY you chose this mix.
    
    If the user is talking about a DAILY EXPENSE to skip or an impulse purchase, return:
    {{"intent": "skip_expense", "amount": 500, "item": "movie ticket"}}
    
    User Input: "{user_input}"
    
    Return ONLY valid JSON. No markdown, no backticks, no explanation. Just the raw JSON object.
    """
    try:
        response = model.generate_content(prompt)
        raw = response.text.strip()

        # Robustly extract JSON
        raw = re.sub(r"
http://googleusercontent.com/immersive_entry_chip/0
