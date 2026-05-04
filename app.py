import streamlit as st
import google.generativeai as genai
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

    /* ---- API key card ---- */
    .key-card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 18px;
        padding: 2.2rem 2rem 0.5rem;
        max-width: 440px;
        margin: 3rem auto 0;
        box-shadow: 0 8px 40px rgba(0,0,0,0.5);
    }
    .key-card-title {
        font-size: 1.1rem;
        font-weight: 600;
        margin-bottom: 0.3rem;
        color: var(--text);
    }
    .key-card-sub {
        font-size: 0.8rem;
        color: var(--muted);
        margin-bottom: 1.4rem;
    }

    /* ---- Text inputs ---- */
    [data-testid="stTextInput"] input {
        background: var(--surface2) !important;
        border: 1px solid var(--border) !important;
        border-radius: 10px !important;
        color: var(--text) !important;
        font-family: var(--font) !important;
        font-size: 0.88rem !important;
    }
    [data-testid="stTextInput"] input:focus {
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 2px rgba(0,200,150,0.12) !important;
    }
    [data-testid="stTextInput"] label {
        color: var(--muted) !important;
        font-size: 0.8rem !important;
        font-weight: 500 !important;
        letter-spacing: 0.04em !important;
    }

    /* ---- Alerts ---- */
    [data-testid="stAlert"] {
        background: var(--surface2) !important;
        border-radius: 10px !important;
        border-left: 3px solid var(--accent) !important;
        font-size: 0.85rem !important;
    }

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
    .sidebar-reset-note {
        font-size: 0.75rem;
        color: var(--muted);
        margin-top: 1.5rem;
        line-height: 1.5;
    }

    /* ---- Spinner ---- */
    [data-testid="stSpinner"] { color: var(--accent) !important; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# Session State Initialization
# ==========================================
if "gemini_api_key" not in st.session_state:
    st.session_state.gemini_api_key = ""
if "goals_set" not in st.session_state:
    st.session_state.goals_set = 0
if "impulses_skipped" not in st.session_state:
    st.session_state.impulses_skipped = 0
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_history" not in st.session_state:
    # Gemini-format multi-turn history (role: user/model)
    st.session_state.chat_history = []

# ==========================================
# API Key Gate
# ==========================================
if not st.session_state.gemini_api_key:
    st.markdown("""
    <div style="text-align:center; margin-top:2rem;">
        <div style="display:inline-flex; align-items:center; gap:0.6rem; margin-bottom:0.4rem;">
            <div class="brand-logo">🎯</div>
            <span class="brand-name" style="font-size:2rem;">GoalPe</span>
        </div>
        <div class="brand-sub" style="font-size:0.9rem; margin-bottom:0;">Your AI Wealth Coach</div>
    </div>
    <div class="key-card">
        <div class="key-card-title">Connect your AI engine</div>
        <div class="key-card-sub">Enter your Gemini API key to unlock the full experience. Your key stays in-session only.</div>
    </div>
    """, unsafe_allow_html=True)

    col_l, col_c, col_r = st.columns([1, 2.5, 1])
    with col_c:
        api_key_input = st.text_input(
            "GEMINI API KEY",
            type="password",
            placeholder="AIza••••••••••••••••••••••••••••••••••••",
        )
        if st.button("Continue →", use_container_width=True):
            if not api_key_input.strip():
                st.warning("Please enter your Gemini API key to continue.")
            else:
                st.session_state.gemini_api_key = api_key_input.strip()
                st.rerun()
        st.markdown(
            '<p style="text-align:center; font-size:0.75rem; color:#6b7280; margin-top:0.6rem;">'
            'Get your key at <a href="https://aistudio.google.com/app/apikey" target="_blank" '
            'style="color:#00c896; text-decoration:none;">aistudio.google.com</a></p>',
            unsafe_allow_html=True
        )
    st.stop()

# ==========================================
# Gemini Configuration
# ==========================================
genai.configure(api_key=st.session_state.gemini_api_key)

# ==========================================
# System Prompt — GoalPe's AI Brain
# ==========================================
SYSTEM_PROMPT = """
You are GoalPe, a friendly and knowledgeable AI wealth coach designed specifically for retail users in India. You are warm, conversational, and intelligent — like a trusted friend who happens to be a SEBI-registered financial advisor.

## YOUR PERSONALITY
- Respond naturally to ALL messages. If someone says "Hi" or "Hello", greet them warmly and ask how you can help with their financial goals. Do NOT jump into financial analysis for casual messages.
- Be concise but thorough. Use simple language, not financial jargon.
- Use Indian context: rupees (₹), Indian mutual fund categories, SIP terminology, Indian financial products.
- You can use light emoji where appropriate to keep the tone friendly.

## WHAT YOU CAN HELP WITH
1. **Savings Goals** — Help users figure out how much to save monthly (SIP) to reach a target amount in a given time.
2. **Impulse Control** — When users mention they want to buy something impulsively, help them see the opportunity cost in terms of their savings goals.
3. **Mutual Fund Guidance** — Recommend appropriate Indian mutual fund categories based on risk and time horizon. Never recommend specific fund houses by name, only categories (e.g., Large Cap Fund, ELSS, Liquid Fund, Flexi Cap Fund).
4. **General Financial Literacy** — Answer questions about SIPs, mutual funds, compounding, budgeting, etc.
5. **Casual Conversation** — Respond naturally. You are a chatbot with a personality, not a form.

## WHAT YOU MUST NEVER DO
- Never recommend direct stocks, F&O trading, or cryptocurrencies. Politely decline and redirect to mutual funds.
- Never give specific fund house recommendations (no "Invest in HDFC Top 100").
- Never guarantee returns. Always say "expected" or "historically".

## HOW TO DO SIP CALCULATIONS
When a user wants to save for a goal, use this formula yourself and show your working clearly:

Monthly SIP = (Target × monthly_rate) / ((1 + monthly_rate)^months - 1)

Where monthly_rate = annual_rate / 12

Choose the annual_rate based on the recommended portfolio:
- Liquid / Ultra Short Fund: 6.5% p.a.
- Short Duration / Debt Fund: 7.5% p.a.
- Large Cap Fund: 11% p.a.
- Flexi Cap / Multi Cap Fund: 12% p.a.
- Mid Cap Fund: 13% p.a.
- Small Cap Fund: 14% p.a.
- ELSS Fund: 12% p.a.

Blend rates proportionally if recommending a mixed portfolio.
Always round the monthly SIP to the nearest ₹100 for practicality.
Show the calculation steps briefly so the user understands.

## PORTFOLIO RECOMMENDATION LOGIC
- Time horizon < 6 months → Liquid Fund or Ultra Short Duration Fund (capital safety)
- Time horizon 6–12 months → Short Duration Debt Fund (stability)
- Time horizon 1–3 years → Mix of Large Cap + Short Duration Debt
- Time horizon 3–5 years → Flexi Cap or Large Cap Fund
- Time horizon 5+ years → Flexi Cap + Mid Cap, optionally small allocation to Small Cap

## IMPULSE PURCHASE HANDLING
If a user mentions wanting to buy something impulsively (e.g., "I want to buy AirPods", "I'm tempted to splurge on a jacket"), and they have an active savings goal in the conversation history:
- Acknowledge their desire warmly (don't be preachy)
- Calculate how many days earlier they could reach their goal if they invested that amount instead
- Let them make the choice — you're a coach, not a parent

If they don't have an active goal, gently suggest setting one first.

## LOGGING TAGS (IMPORTANT — ALWAYS INCLUDE AT END OF RESPONSE)
At the very end of EVERY response, silently append one of these tags on its own line. This is for internal tracking only and will be hidden from the user. Always include exactly one tag:

For casual/general conversation:    [LOG:chat]
For a new savings goal created:     [LOG:new_goal]
For an impulse purchase discussed:  [LOG:impulse]
For a refusal (stocks/crypto):      [LOG:refusal]
For general financial education:    [LOG:education]

Do NOT explain these tags to the user. Just append them silently at the end.
"""

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

    st.markdown('<div class="sidebar-stat-label">Impulses Discussed</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sidebar-stat-value">{st.session_state.impulses_skipped}</div>', unsafe_allow_html=True)

    st.markdown("---")

    if st.button("🔄 New Conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.chat_history = []
        st.rerun()

    if st.button("🔑 Change API Key", use_container_width=True):
        st.session_state.gemini_api_key = ""
        st.session_state.messages = []
        st.session_state.chat_history = []
        st.rerun()

    st.markdown(
        '<p class="sidebar-reset-note">Your API key is stored only in this browser session and is never saved to any server.</p>',
        unsafe_allow_html=True
    )

# ==========================================
# Database Connection (Google Sheets)
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
        st.error(f"Database Error: {e}")
        return None

def log_to_database(log_type):
    sheet = connect_to_db()
    if sheet:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([timestamp, log_type])

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
# Core AI Chat Function
# ==========================================
def chat_with_goalpe(user_message):
    """
    Send user message to Gemini with full conversation history.
    Returns (clean_reply, log_tag).
    """
    try:
        model = genai.GenerativeModel(
            model_name='gemini-2.5-flash',
            system_instruction=SYSTEM_PROMPT
        )

        # Start chat with existing history
        chat = model.start_chat(history=st.session_state.chat_history)

        # Send the new message
        response = chat.send_message(user_message)
        raw_reply = response.text.strip()

        # Extract the log tag silently
        log_tag = "chat"
        tag_match = re.search(r'\[LOG:(\w+)\]', raw_reply)
        if tag_match:
            log_tag = tag_match.group(1)

        # Strip the log tag from the displayed reply
        clean_reply = re.sub(r'\s*\[LOG:\w+\]\s*$', '', raw_reply).strip()

        # Update the conversation history for next turn
        st.session_state.chat_history = chat.history

        return clean_reply, log_tag

    except Exception as e:
        error_str = str(e).lower()
        if "api_key" in error_str or "invalid" in error_str or "401" in error_str or "403" in error_str:
            st.error("❌ Invalid API key. Use the sidebar to re-enter a valid key.")
            st.session_state.gemini_api_key = ""
            st.stop()
        if "429" in str(e) or "quota" in error_str or "rate" in error_str:
            return "⏳ You've hit the Gemini rate limit. Please wait a moment and try again.", "chat"
        return f"Something went wrong. Please try again.", "chat"

# ==========================================
# Main UI — Brand Header
# ==========================================
st.markdown("""
<div class="brand-bar">
    <div class="brand-logo">🎯</div>
    <span class="brand-name">GoalPe</span>
</div>
<div class="brand-sub">Your AI Wealth Coach — set a goal, or tell us what you're tempted to buy.</div>
""", unsafe_allow_html=True)

# Market Pulse Card
current_price, change, change_pct = get_nifty_data()
if current_price:
    change_class = "pulse-change-up" if change >= 0 else "pulse-change-down"
    change_arrow = "▲" if change >= 0 else "▼"
    st.markdown(f"""
    <div class="pulse-card">
        <div>
            <div class="pulse-label">Live Market Pulse</div>
            <div class="pulse-price">₹{current_price:,.2f}</div>
            <div class="{change_class}">{change_arrow} {abs(change):,.2f} ({change_pct:+.2f}%) &nbsp;·&nbsp; Nifty 50</div>
        </div>
        <div class="pulse-dot"></div>
    </div>
    """, unsafe_allow_html=True)

# Opening message if fresh session
if not st.session_state.messages:
    opening = "Hey! 👋 I'm GoalPe, your personal AI wealth coach. I can help you plan savings goals, figure out your monthly SIP, talk through investment options, or just answer any finance questions you have.\n\nWhat's on your mind today?"
    st.session_state.messages.append({"role": "assistant", "content": opening})

# Render chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ==========================================
# Chat Input & Response
# ==========================================
if prompt := st.chat_input("Ask me anything — goals, SIPs, investments, or just say hi!"):
    # Show user message immediately
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.spinner("Thinking..."):
        reply, log_tag = chat_with_goalpe(prompt)

        # Update sidebar counters based on log tag
        if log_tag == "new_goal":
            st.session_state.goals_set += 1
        elif log_tag == "impulse":
            st.session_state.impulses_skipped += 1

        # Fire to database (non-blocking — errors are silent)
        try:
            log_to_database(log_tag)
        except:
            pass

    # Display assistant reply
    with st.chat_message("assistant"):
        st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})
