import streamlit as st
import google.generativeai as genai
import re
import yfinance as yf
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ==========================================
# Page Config
# ==========================================
st.set_page_config(page_title="GoalPe", page_icon="🎯", layout="centered")

# ==========================================
# Global CSS
# ==========================================
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700&family=DM+Mono:wght@300;400;500&display=swap" rel="stylesheet">
<style>
    :root {
        --bg:        #0d0f14;
        --surface:   #151820;
        --surface2:  #1c2030;
        --border:    #252a38;
        --accent:    #00c896;
        --accent2:   #0090ff;
        --danger:    #ff4f5e;
        --warning:   #f5a623;
        --text:      #e8eaf0;
        --muted:     #6b7280;
        --font:      'Sora', sans-serif;
        --mono:      'DM Mono', monospace;
        --nav-h:     64px;
    }

    html, body, [data-testid="stAppViewContainer"] {
        background-color: var(--bg) !important;
        color: var(--text) !important;
        font-family: var(--font) !important;
    }

    #MainMenu, footer, header { visibility: hidden !important; }
    [data-testid="stToolbar"] { display: none !important; }
    [data-testid="stSidebar"] { display: none !important; }

    .block-container {
        padding-top: 1rem !important;
        padding-bottom: calc(var(--nav-h) + 1rem) !important;
        max-width: 480px !important;
    }

    ::-webkit-scrollbar { width: 3px; }
    ::-webkit-scrollbar-track { background: var(--bg); }
    ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }

    /* ---- Bottom Nav ---- */
    .bottom-nav {
        position: fixed;
        bottom: 0; left: 0; right: 0;
        height: var(--nav-h);
        background: var(--surface);
        border-top: 1px solid var(--border);
        display: flex;
        align-items: center;
        justify-content: space-around;
        z-index: 9999;
        padding-bottom: env(safe-area-inset-bottom);
        backdrop-filter: blur(12px);
    }
    .nav-item {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 3px;
        cursor: pointer;
        padding: 8px 16px;
        border-radius: 12px;
        transition: background 0.2s;
        text-decoration: none;
        border: none;
        background: none;
    }
    .nav-icon { font-size: 20px; line-height: 1; }
    .nav-label {
        font-size: 10px;
        font-weight: 500;
        letter-spacing: 0.03em;
        font-family: var(--font);
    }
    .nav-item.active .nav-label { color: var(--accent); }
    .nav-item.active .nav-icon { filter: drop-shadow(0 0 6px var(--accent)); }
    .nav-item:not(.active) .nav-label { color: var(--muted); }
    .nav-item:not(.active) .nav-icon { opacity: 0.5; }

    /* ---- Brand header ---- */
    .brand-bar {
        display: flex; align-items: center;
        gap: 0.6rem; margin-bottom: 0.2rem;
    }
    .brand-logo {
        width: 32px; height: 32px;
        background: linear-gradient(135deg, var(--accent), var(--accent2));
        border-radius: 9px;
        display: flex; align-items: center; justify-content: center;
        font-size: 16px;
        box-shadow: 0 0 14px rgba(0,200,150,0.35);
    }
    .brand-name {
        font-size: 1.35rem; font-weight: 700;
        letter-spacing: -0.03em;
        background: linear-gradient(90deg, var(--accent), var(--accent2));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .brand-sub {
        font-size: 0.78rem; color: var(--muted);
        font-weight: 300; margin-bottom: 1rem;
    }

    /* ---- Ticker ---- */
    .ticker-wrap {
        overflow: hidden;
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 0.45rem 1rem;
        margin-bottom: 1rem;
        white-space: nowrap;
    }
    .ticker-inner {
        display: inline-flex; gap: 2rem;
        animation: ticker 25s linear infinite;
    }
    .ticker-item {
        display: inline-flex; align-items: center; gap: 0.4rem;
        font-family: var(--mono); font-size: 0.78rem;
    }
    .ticker-name { color: var(--muted); }
    .ticker-price { color: var(--text); font-weight: 500; }
    .ticker-up { color: var(--accent); }
    .ticker-down { color: var(--danger); }
    @keyframes ticker {
        0% { transform: translateX(0); }
        100% { transform: translateX(-50%); }
    }

    /* ---- Market cards ---- */
    .market-card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.75rem;
        display: flex; align-items: center;
        justify-content: space-between;
        box-shadow: 0 2px 10px rgba(0,0,0,0.3);
    }
    .market-card-left { display: flex; flex-direction: column; gap: 2px; }
    .market-card-name { font-size: 0.82rem; color: var(--muted); font-weight: 500; }
    .market-card-price { font-family: var(--mono); font-size: 1.15rem; font-weight: 500; }
    .market-card-right { display: flex; flex-direction: column; align-items: flex-end; gap: 2px; }
    .badge-up {
        background: rgba(0,200,150,0.12);
        color: var(--accent);
        border: 1px solid rgba(0,200,150,0.25);
        border-radius: 6px; padding: 2px 8px;
        font-family: var(--mono); font-size: 0.78rem; font-weight: 500;
    }
    .badge-down {
        background: rgba(255,79,94,0.12);
        color: var(--danger);
        border: 1px solid rgba(255,79,94,0.25);
        border-radius: 6px; padding: 2px 8px;
        font-family: var(--mono); font-size: 0.78rem; font-weight: 500;
    }
    .market-vol { font-size: 0.7rem; color: var(--muted); }

    /* ---- Section heading ---- */
    .section-head {
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: var(--muted);
        margin: 1.2rem 0 0.6rem;
        font-weight: 600;
    }

    /* ---- Sector chips ---- */
    .chip-row { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 1rem; }
    .chip {
        background: var(--surface2);
        border: 1px solid var(--border);
        border-radius: 20px;
        padding: 4px 12px;
        font-size: 0.75rem;
        color: var(--muted);
        font-family: var(--font);
    }
    .chip.up { border-color: rgba(0,200,150,0.3); color: var(--accent); background: rgba(0,200,150,0.07); }
    .chip.down { border-color: rgba(255,79,94,0.3); color: var(--danger); background: rgba(255,79,94,0.07); }

    /* ---- Goal cards ---- */
    .goal-card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 1.1rem 1.2rem;
        margin-bottom: 0.75rem;
        box-shadow: 0 2px 10px rgba(0,0,0,0.3);
    }
    .goal-card-top {
        display: flex; justify-content: space-between;
        align-items: flex-start; margin-bottom: 0.7rem;
    }
    .goal-name { font-size: 0.95rem; font-weight: 600; }
    .goal-amount { font-family: var(--mono); font-size: 0.82rem; color: var(--accent); }
    .goal-meta { font-size: 0.75rem; color: var(--muted); margin-top: 2px; }
    .progress-bar-bg {
        background: var(--surface2);
        border-radius: 99px; height: 6px;
        margin: 0.6rem 0 0.4rem; overflow: hidden;
    }
    .progress-bar-fill {
        height: 100%; border-radius: 99px;
        background: linear-gradient(90deg, var(--accent), var(--accent2));
        transition: width 0.5s ease;
    }
    .goal-footer {
        display: flex; justify-content: space-between;
        font-size: 0.72rem; color: var(--muted);
    }

    /* ---- Empty state ---- */
    .empty-state {
        text-align: center;
        padding: 3rem 1rem;
        color: var(--muted);
    }
    .empty-icon { font-size: 2.5rem; margin-bottom: 0.5rem; }
    .empty-title { font-size: 0.95rem; font-weight: 600; color: var(--text); margin-bottom: 0.3rem; }
    .empty-sub { font-size: 0.8rem; line-height: 1.5; }

    /* ---- Profile ---- */
    .profile-avatar {
        width: 64px; height: 64px;
        background: linear-gradient(135deg, var(--accent), var(--accent2));
        border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-size: 28px; margin: 0 auto 0.6rem;
        box-shadow: 0 0 20px rgba(0,200,150,0.3);
    }
    .profile-name {
        text-align: center; font-size: 1.1rem;
        font-weight: 600; margin-bottom: 0.2rem;
    }
    .profile-tag {
        text-align: center; font-size: 0.78rem;
        color: var(--muted); margin-bottom: 1.4rem;
    }
    .profile-stat-row {
        display: flex; gap: 0.75rem; margin-bottom: 1.2rem;
    }
    .profile-stat {
        flex: 1; background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 12px; padding: 0.8rem;
        text-align: center;
    }
    .profile-stat-val {
        font-family: var(--mono); font-size: 1.3rem;
        font-weight: 500; color: var(--accent);
    }
    .profile-stat-label {
        font-size: 0.68rem; color: var(--muted);
        text-transform: uppercase; letter-spacing: 0.06em;
        margin-top: 2px;
    }
    .settings-card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 14px;
        overflow: hidden;
        margin-bottom: 0.75rem;
    }
    .settings-row {
        display: flex; align-items: center;
        justify-content: space-between;
        padding: 0.9rem 1.1rem;
        border-bottom: 1px solid var(--border);
        font-size: 0.88rem;
    }
    .settings-row:last-child { border-bottom: none; }
    .settings-row-left { display: flex; align-items: center; gap: 0.7rem; }
    .settings-icon {
        width: 30px; height: 30px;
        background: var(--surface2);
        border-radius: 8px;
        display: flex; align-items: center; justify-content: center;
        font-size: 14px;
    }
    .chevron { color: var(--muted); font-size: 0.8rem; }

    /* ---- Chat ---- */
    [data-testid="stChatMessage"] {
        background: transparent !important;
        border: none !important; padding: 0.1rem 0 !important;
    }
    [data-testid="stChatMessage"][data-role="assistant"] .stMarkdown {
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: 0 16px 16px 16px !important;
        padding: 0.85rem 1rem !important;
        font-size: 0.88rem !important;
        line-height: 1.65 !important;
        box-shadow: 0 2px 10px rgba(0,0,0,0.3) !important;
    }
    [data-testid="stChatMessage"][data-role="user"] .stMarkdown {
        background: linear-gradient(135deg, #0a2a20, #0a1f35) !important;
        border: 1px solid rgba(0,200,150,0.2) !important;
        border-radius: 16px 0 16px 16px !important;
        padding: 0.85rem 1rem !important;
        font-size: 0.88rem !important;
        line-height: 1.65 !important;
    }
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

    /* ---- Quick action buttons ---- */
    .quick-actions { display: flex; gap: 0.5rem; margin-bottom: 1rem; flex-wrap: wrap; }
    .quick-btn {
        background: var(--surface2);
        border: 1px solid var(--border);
        border-radius: 20px;
        padding: 6px 14px;
        font-size: 0.78rem;
        color: var(--text);
        font-family: var(--font);
        cursor: pointer;
        transition: border-color 0.2s, background 0.2s;
        white-space: nowrap;
    }
    .quick-btn:hover {
        border-color: var(--accent);
        background: rgba(0,200,150,0.08);
        color: var(--accent);
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
    .stButton > button:hover { opacity: 0.88 !important; transform: translateY(-1px) !important; }
    .stButton > button:active { transform: translateY(0) !important; }

    /* ---- Toggle (theme) ---- */
    .toggle-row {
        display: flex; align-items: center;
        justify-content: space-between;
        padding: 0.9rem 1.1rem;
        font-size: 0.88rem;
    }
    .toggle-left { display: flex; align-items: center; gap: 0.7rem; }

    /* ---- Alerts ---- */
    [data-testid="stAlert"] {
        background: var(--surface2) !important;
        border-radius: 10px !important;
        border-left: 3px solid var(--accent) !important;
        font-size: 0.85rem !important;
    }

    [data-testid="stSpinner"] { color: var(--accent) !important; }

    /* ---- Selectbox (nav workaround) ---- */
    [data-testid="stSelectbox"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# Load API Key from Streamlit Secrets
# ==========================================
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except KeyError:
    st.error("⚠️ Gemini API key not found. Please add GEMINI_API_KEY to your Streamlit secrets.")
    st.stop()

genai.configure(api_key=GEMINI_API_KEY)

# ==========================================
# Session State
# ==========================================
defaults = {
    "tab": "home",
    "goals_set": 0,
    "impulses_skipped": 0,
    "messages": [],
    "chat_history": [],
    "goals_list": [],       # [{name, target, sip, months, created}]
    "dark_mode": True,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ==========================================
# System Prompt
# ==========================================
SYSTEM_PROMPT = """
You are GoalPe, a friendly and knowledgeable AI wealth coach designed specifically for retail users in India. You are warm, conversational, and intelligent — like a trusted friend who happens to be a SEBI-registered financial advisor.

## YOUR PERSONALITY
- Respond naturally to ALL messages. If someone says "Hi" or "Hello", greet them warmly and ask how you can help. Do NOT jump into financial analysis for casual messages.
- Be concise but thorough. Use simple language, not financial jargon.
- Use Indian context: rupees (₹), Indian mutual fund categories, SIP terminology.
- Use light emoji where appropriate.

## WHAT YOU CAN HELP WITH
1. Savings Goals — Help users figure out monthly SIP to reach a target amount in a given time.
2. Impulse Control — When users mention impulsive purchases, show the opportunity cost vs their goals.
3. Mutual Fund Guidance — Recommend Indian mutual fund categories (never specific fund houses).
4. General Financial Literacy — SIPs, compounding, budgeting, mutual funds.
5. Casual Conversation — Respond naturally. You have a personality.

## WHAT YOU MUST NEVER DO
- Never recommend direct stocks, F&O, or crypto. Redirect to mutual funds.
- Never name specific fund houses (no "HDFC Top 100").
- Never guarantee returns. Always say "expected" or "historically".

## SIP CALCULATION FORMULA
Monthly SIP = (Target × monthly_rate) / ((1 + monthly_rate)^months - 1)
monthly_rate = annual_rate / 12

Annual rates by fund type:
- Liquid / Ultra Short: 6.5%
- Short Duration Debt: 7.5%
- Large Cap: 11%
- Flexi Cap / Multi Cap: 12%
- Mid Cap: 13%
- Small Cap: 14%
- ELSS: 12%

Round monthly SIP to nearest ₹100. Show brief working.

## PORTFOLIO LOGIC
- < 6 months → Liquid Fund
- 6–12 months → Short Duration Debt
- 1–3 years → Large Cap + Short Duration Debt mix
- 3–5 years → Flexi Cap or Large Cap
- 5+ years → Flexi Cap + Mid Cap (+ Small Cap optional)

## IMPULSE HANDLING
If user mentions an impulsive buy and has an active goal in conversation history:
- Acknowledge warmly (don't be preachy)
- Calculate days saved toward goal if they invested instead
- Let them decide

## LOGGING TAGS — ALWAYS APPEND ONE AT END OF EVERY RESPONSE
[LOG:chat]        — casual conversation
[LOG:new_goal]    — savings goal calculated (also append [GOAL:name|target|sip|months])
[LOG:impulse]     — impulse purchase discussed
[LOG:refusal]     — stocks/crypto refused
[LOG:education]   — financial education

When logging a new goal, append BOTH tags on separate lines:
[LOG:new_goal]
[GOAL:Laptop Fund|50000|4200|12]

Do NOT explain these tags. Just append silently.
"""

# ==========================================
# Database
# ==========================================
def connect_to_db():
    try:
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds_dict = dict(st.secrets["google_credentials"])
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        return client.open("GoalPe_Database").sheet1
    except:
        return None

def log_to_database(log_type):
    sheet = connect_to_db()
    if sheet:
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sheet.append_row([timestamp, log_type])
        except:
            pass

# ==========================================
# Market Data
# ==========================================
@st.cache_data(ttl=300)
def get_market_data():
    tickers = {
        "Nifty 50":   "^NSEI",
        "Sensex":     "^BSESN",
        "Bank Nifty": "^NSEBANK",
        "Gold":       "GC=F",
        "USD/INR":    "USDINR=X",
    }
    results = {}
    for name, symbol in tickers.items():
        try:
            t = yf.Ticker(symbol)
            hist = t.history(period="2d")
            if len(hist) >= 2:
                cur = hist['Close'].iloc[-1]
                prev = hist['Close'].iloc[-2]
                chg = cur - prev
                chg_pct = (chg / prev) * 100
                results[name] = {"price": cur, "change": chg, "pct": chg_pct}
        except:
            pass
    return results

@st.cache_data(ttl=600)
def get_sector_data():
    sectors = {
        "IT":       "^CNXIT",
        "Pharma":   "^CNXPHARMA",
        "Auto":     "^CNXAUTO",
        "FMCG":     "^CNXFMCG",
        "Realty":   "^CNXREALTY",
        "Metal":    "^CNXMETAL",
        "Energy":   "^CNXENERGY",
        "Infra":    "^CNXINFRA",
    }
    results = {}
    for name, symbol in sectors.items():
        try:
            t = yf.Ticker(symbol)
            hist = t.history(period="2d")
            if len(hist) >= 2:
                cur = hist['Close'].iloc[-1]
                prev = hist['Close'].iloc[-2]
                pct = ((cur - prev) / prev) * 100
                results[name] = pct
        except:
            pass
    return results

# ==========================================
# AI Chat
# ==========================================
def chat_with_goalpe(user_message):
    try:
        model = genai.GenerativeModel(
            model_name='gemini-2.5-flash',
            system_instruction=SYSTEM_PROMPT
        )
        chat = model.start_chat(history=st.session_state.chat_history)
        response = chat.send_message(user_message)
        raw_reply = response.text.strip()

        log_tag = "chat"
        tag_match = re.search(r'\[LOG:(\w+)\]', raw_reply)
        if tag_match:
            log_tag = tag_match.group(1)

        # Parse goal data if present
        goal_match = re.search(r'\[GOAL:([^\]]+)\]', raw_reply)
        if goal_match:
            try:
                parts = goal_match.group(1).split("|")
                if len(parts) == 4:
                    st.session_state.goals_list.append({
                        "name":    parts[0].strip(),
                        "target":  int(parts[1].strip()),
                        "sip":     int(parts[2].strip()),
                        "months":  int(parts[3].strip()),
                        "created": datetime.now().strftime("%b %Y"),
                        "progress": 0,
                    })
            except:
                pass

        # Strip all tags from displayed reply
        clean_reply = re.sub(r'\s*\[LOG:\w+\]\s*', '', raw_reply)
        clean_reply = re.sub(r'\s*\[GOAL:[^\]]+\]\s*', '', clean_reply).strip()

        st.session_state.chat_history = chat.history
        return clean_reply, log_tag

    except Exception as e:
        error_str = str(e).lower()
        if "429" in str(e) or "quota" in error_str or "rate" in error_str:
            return "⏳ Rate limit hit. Please wait a moment and try again.", "chat"
        return "Something went wrong. Please try again.", "chat"

# ==========================================
# Bottom Navigation HTML
# ==========================================
def render_nav(active_tab):
    tabs = [
        ("home",    "🏠", "Home"),
        ("markets", "📈", "Markets"),
        ("goals",   "🎯", "Goals"),
        ("profile", "👤", "Profile"),
    ]
    items = ""
    for key, icon, label in tabs:
        cls = "nav-item active" if active_tab == key else "nav-item"
        items += f"""
        <form method="get" style="display:inline;">
            <button class="{cls}" onclick="window.parent.document.querySelector('[data-testid=stSelectbox] select').value='{key}'; window.parent.document.querySelector('[data-testid=stSelectbox] select').dispatchEvent(new Event('change', {{bubbles:true}}));" type="button">
                <span class="nav-icon">{icon}</span>
                <span class="nav-label">{label}</span>
            </button>
        </form>
        """
    st.markdown(f'<div class="bottom-nav">{items}</div>', unsafe_allow_html=True)

# ==========================================
# Tab: HOME
# ==========================================
def render_home(market_data):
    st.markdown("""
    <div class="brand-bar">
        <div class="brand-logo">🎯</div>
        <span class="brand-name">GoalPe</span>
    </div>
    <div class="brand-sub">Your AI Wealth Coach</div>
    """, unsafe_allow_html=True)

    # Ticker
    if market_data:
        ticker_items = ""
        for name, d in market_data.items():
            arrow = "▲" if d["change"] >= 0 else "▼"
            cls = "ticker-up" if d["change"] >= 0 else "ticker-down"
            price_str = f"₹{d['price']:,.0f}" if name not in ["USD/INR"] else f"₹{d['price']:.2f}"
            ticker_items += f"""
            <span class="ticker-item">
                <span class="ticker-name">{name}</span>
                <span class="ticker-price">{price_str}</span>
                <span class="{cls}">{arrow}{abs(d['pct']):.2f}%</span>
            </span>
            """
        # Duplicate for seamless loop
        st.markdown(f"""
        <div class="ticker-wrap">
            <div class="ticker-inner">
                {ticker_items}{ticker_items}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Quick actions
    st.markdown("""
    <div class="quick-actions">
        <span class="quick-btn">💰 Set a Goal</span>
        <span class="quick-btn">📊 SIP Calculator</span>
        <span class="quick-btn">🧠 What is SIP?</span>
        <span class="quick-btn">⚡ Market Today</span>
    </div>
    """, unsafe_allow_html=True)

    # Chat
    if not st.session_state.messages:
        opening = "Hey! 👋 I'm GoalPe, your personal AI wealth coach. I can help you plan savings goals, calculate SIPs, talk through investments, or just answer finance questions.\n\nWhat's on your mind today?"
        st.session_state.messages.append({"role": "assistant", "content": opening})

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask me anything — goals, SIPs, or just say hi!"):
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.spinner("Thinking..."):
            reply, log_tag = chat_with_goalpe(prompt)
            if log_tag == "new_goal":
                st.session_state.goals_set += 1
            elif log_tag == "impulse":
                st.session_state.impulses_skipped += 1
            try:
                log_to_database(log_tag)
            except:
                pass

        with st.chat_message("assistant"):
            st.markdown(reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})

# ==========================================
# Tab: MARKETS
# ==========================================
def render_markets(market_data, sector_data):
    st.markdown("""
    <div class="brand-bar">
        <div class="brand-logo">📈</div>
        <span class="brand-name">Markets</span>
    </div>
    <div class="brand-sub">Live Indian market snapshot</div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-head">Indices & Commodities</div>', unsafe_allow_html=True)

    if market_data:
        for name, d in market_data.items():
            arrow = "▲" if d["change"] >= 0 else "▼"
            badge_cls = "badge-up" if d["change"] >= 0 else "badge-down"
            if name == "USD/INR":
                price_str = f"₹{d['price']:.4f}"
            elif name == "Gold":
                price_str = f"${d['price']:,.2f}"
            else:
                price_str = f"₹{d['price']:,.2f}"
            st.markdown(f"""
            <div class="market-card">
                <div class="market-card-left">
                    <div class="market-card-name">{name}</div>
                    <div class="market-card-price">{price_str}</div>
                </div>
                <div class="market-card-right">
                    <span class="{badge_cls}">{arrow} {abs(d['pct']):.2f}%</span>
                    <div class="market-vol">{arrow} {abs(d['change']):,.2f} pts</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Market data unavailable. Try refreshing.")

    # Sector heatmap
    st.markdown('<div class="section-head">Sector Performance</div>', unsafe_allow_html=True)

    if sector_data:
        sorted_sectors = sorted(sector_data.items(), key=lambda x: x[1], reverse=True)
        chips = ""
        for name, pct in sorted_sectors:
            arrow = "▲" if pct >= 0 else "▼"
            cls = "chip up" if pct >= 0 else "chip down"
            chips += f'<span class="{cls}">{name} {arrow}{abs(pct):.1f}%</span>'
        st.markdown(f'<div class="chip-row">{chips}</div>', unsafe_allow_html=True)

        # Best and worst
        best = sorted_sectors[:3]
        worst = sorted_sectors[-3:][::-1]

        st.markdown('<div class="section-head">🔥 Top Gainers</div>', unsafe_allow_html=True)
        for name, pct in best:
            st.markdown(f"""
            <div class="market-card">
                <div class="market-card-left">
                    <div class="market-card-name">NSE {name} Index</div>
                </div>
                <span class="badge-up">▲ {abs(pct):.2f}%</span>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('<div class="section-head">🔻 Top Losers</div>', unsafe_allow_html=True)
        for name, pct in worst:
            st.markdown(f"""
            <div class="market-card">
                <div class="market-card-left">
                    <div class="market-card-name">NSE {name} Index</div>
                </div>
                <span class="badge-down">▼ {abs(pct):.2f}%</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Sector data unavailable.")

    st.markdown("""
    <div style="text-align:center; font-size:0.7rem; color:#6b7280; margin-top:1rem;">
        Data refreshes every 5 minutes · Prices from Yahoo Finance
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# Tab: GOALS
# ==========================================
def render_goals():
    st.markdown("""
    <div class="brand-bar">
        <div class="brand-logo">🎯</div>
        <span class="brand-name">My Goals</span>
    </div>
    <div class="brand-sub">Track your savings quests</div>
    """, unsafe_allow_html=True)

    goals = st.session_state.goals_list

    if not goals:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-icon">🎯</div>
            <div class="empty-title">No goals yet</div>
            <div class="empty-sub">Head to the Home tab and tell GoalPe what you're saving for. Your goals will appear here automatically.</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="section-head">{len(goals)} Active Goal{"s" if len(goals) != 1 else ""}</div>', unsafe_allow_html=True)

        for i, g in enumerate(goals):
            months_done = min(
                int((datetime.now() - datetime.strptime(g["created"], "%b %Y")).days / 30)
                if datetime.strptime(g["created"], "%b %Y") <= datetime.now() else 0,
                g["months"]
            )
            pct_done = min(int((months_done / g["months"]) * 100), 100) if g["months"] > 0 else 0
            months_left = max(g["months"] - months_done, 0)
            projected = g["sip"] * months_done

            st.markdown(f"""
            <div class="goal-card">
                <div class="goal-card-top">
                    <div>
                        <div class="goal-name">{g['name']}</div>
                        <div class="goal-meta">Started {g['created']} · {months_left} months left</div>
                    </div>
                    <div class="goal-amount">₹{g['target']:,}</div>
                </div>
                <div class="progress-bar-bg">
                    <div class="progress-bar-fill" style="width:{pct_done}%"></div>
                </div>
                <div class="goal-footer">
                    <span>₹{projected:,} projected saved</span>
                    <span>₹{g['sip']:,}/mo SIP</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Summary
        total_target = sum(g["target"] for g in goals)
        total_sip = sum(g["sip"] for g in goals)
        st.markdown(f"""
        <div class="market-card" style="margin-top:0.5rem;">
            <div class="market-card-left">
                <div class="market-card-name">Total Monthly Commitment</div>
                <div class="market-card-price">₹{total_sip:,}</div>
            </div>
            <div class="market-card-right">
                <div class="market-card-name">Total Target</div>
                <div style="font-family:var(--mono); font-size:1rem; color:var(--accent);">₹{total_target:,}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Clear goals button
    if goals:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🗑️ Clear All Goals", use_container_width=True):
            st.session_state.goals_list = []
            st.session_state.goals_set = 0
            st.rerun()

# ==========================================
# Tab: PROFILE
# ==========================================
def render_profile():
    st.markdown("""
    <div class="brand-bar">
        <div class="brand-logo">👤</div>
        <span class="brand-name">Profile</span>
    </div>
    <div class="brand-sub">Session overview & settings</div>
    """, unsafe_allow_html=True)

    # Avatar
    st.markdown("""
    <div class="profile-avatar">🧑</div>
    <div class="profile-name">GoalPe User</div>
    <div class="profile-tag">Demo Session · Active</div>
    """, unsafe_allow_html=True)

    # Stats
    st.markdown(f"""
    <div class="profile-stat-row">
        <div class="profile-stat">
            <div class="profile-stat-val">{st.session_state.goals_set}</div>
            <div class="profile-stat-label">Goals Set</div>
        </div>
        <div class="profile-stat">
            <div class="profile-stat-val">{st.session_state.impulses_skipped}</div>
            <div class="profile-stat-label">Impulses Caught</div>
        </div>
        <div class="profile-stat">
            <div class="profile-stat-val">{len(st.session_state.messages) // 2}</div>
            <div class="profile-stat-label">Chats</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Settings
    st.markdown('<div class="section-head">Settings</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="settings-card">
        <div class="settings-row">
            <div class="settings-row-left">
                <div class="settings-icon">🌙</div>
                <span>Dark Theme</span>
            </div>
            <span style="font-size:0.75rem; color:var(--accent);">Active</span>
        </div>
        <div class="settings-row">
            <div class="settings-row-left">
                <div class="settings-icon">🔔</div>
                <span>Notifications</span>
            </div>
            <span class="chevron">›</span>
        </div>
        <div class="settings-row">
            <div class="settings-row-left">
                <div class="settings-icon">🔒</div>
                <span>Privacy & Security</span>
            </div>
            <span class="chevron">›</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-head">About</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="settings-card">
        <div class="settings-row">
            <div class="settings-row-left">
                <div class="settings-icon">📋</div>
                <span>Terms & Policy</span>
            </div>
            <span class="chevron">›</span>
        </div>
        <div class="settings-row">
            <div class="settings-row-left">
                <div class="settings-icon">❓</div>
                <span>Help & Support</span>
            </div>
            <span class="chevron">›</span>
        </div>
        <div class="settings-row">
            <div class="settings-row-left">
                <div class="settings-icon">ℹ️</div>
                <span>App Version</span>
            </div>
            <span style="font-size:0.78rem; color:var(--muted);">v2.0.0</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-head">Session</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 New Chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.chat_history = []
            st.session_state.tab = "home"
            st.rerun()
    with col2:
        if st.button("🗑️ Clear All Data", use_container_width=True):
            for k in ["messages", "chat_history", "goals_list"]:
                st.session_state[k] = [] if k != "chat_history" else []
            st.session_state.goals_set = 0
            st.session_state.impulses_skipped = 0
            st.session_state.tab = "home"
            st.rerun()

    st.markdown("""
    <div style="text-align:center; font-size:0.7rem; color:#6b7280; margin-top:1.5rem; line-height:1.6;">
        GoalPe is an AI assistant and does not provide certified financial advice.<br>
        Always consult a SEBI-registered advisor for major financial decisions.<br><br>
        Your data stays in this browser session only.
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# Navigation — hidden selectbox as state driver
# ==========================================
tab_options = ["home", "markets", "goals", "profile"]

selected = st.selectbox(
    "nav",
    tab_options,
    index=tab_options.index(st.session_state.tab),
    key="nav_select",
    label_visibility="collapsed"
)

if selected != st.session_state.tab:
    st.session_state.tab = selected
    st.rerun()

# Streamlit button nav (visible, styled as bottom nav via JS injection)
nav_cols = st.columns(4)
nav_labels = [("🏠", "Home"), ("📈", "Markets"), ("🎯", "Goals"), ("👤", "Profile")]
nav_keys   = ["home", "markets", "goals", "profile"]

# Render actual clickable nav using st.columns + buttons with custom CSS
st.markdown("""
<style>
div[data-testid="stHorizontalBlock"] > div:nth-child(1) button,
div[data-testid="stHorizontalBlock"] > div:nth-child(2) button,
div[data-testid="stHorizontalBlock"] > div:nth-child(3) button,
div[data-testid="stHorizontalBlock"] > div:nth-child(4) button {
    position: fixed !important;
    bottom: 0 !important;
    height: 64px !important;
    border-radius: 0 !important;
    border: none !important;
    background: #151820 !important;
    border-top: 1px solid #252a38 !important;
    box-shadow: none !important;
    font-size: 0.65rem !important;
    color: #6b7280 !important;
    padding: 4px 0 8px !important;
    flex-direction: column !important;
    gap: 2px !important;
    z-index: 9999 !important;
    width: 25vw !important;
}
div[data-testid="stHorizontalBlock"] > div:nth-child(1) { position: fixed !important; bottom: 0 !important; left: 0 !important; width: 25vw !important; z-index: 9999 !important; }
div[data-testid="stHorizontalBlock"] > div:nth-child(2) { position: fixed !important; bottom: 0 !important; left: 25vw !important; width: 25vw !important; z-index: 9999 !important; }
div[data-testid="stHorizontalBlock"] > div:nth-child(3) { position: fixed !important; bottom: 0 !important; left: 50vw !important; width: 25vw !important; z-index: 9999 !important; }
div[data-testid="stHorizontalBlock"] > div:nth-child(4) { position: fixed !important; bottom: 0 !important; left: 75vw !important; width: 25vw !important; z-index: 9999 !important; }
</style>
""", unsafe_allow_html=True)

for i, (col, (icon, label), key) in enumerate(zip(nav_cols, nav_labels, nav_keys)):
    with col:
        active_color = "#00c896" if st.session_state.tab == key else "#6b7280"
        st.markdown(f"""
        <style>
        div[data-testid="stHorizontalBlock"] > div:nth-child({i+1}) button {{
            color: {active_color} !important;
        }}
        </style>
        """, unsafe_allow_html=True)
        if st.button(f"{icon}\n{label}", key=f"nav_{key}", use_container_width=True):
            st.session_state.tab = key
            st.rerun()

# ==========================================
# Fetch data (cached)
# ==========================================
market_data = get_market_data()
sector_data = get_sector_data()

# ==========================================
# Render Active Tab
# ==========================================
active = st.session_state.tab

if active == "home":
    render_home(market_data)
elif active == "markets":
    render_markets(market_data, sector_data)
elif active == "goals":
    render_goals()
elif active == "profile":
    render_profile()
