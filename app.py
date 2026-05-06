import streamlit as st
import google.generativeai as genai
import re
import yfinance as yf
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date
import json

# ==========================================
# Page Config (must be first Streamlit call)
# ==========================================
st.set_page_config(page_title="GoalPe", page_icon="🎯", layout="centered")

# ==========================================
# Global CSS Injection (UPDATED — added dark/light theme + nav + new components)
# ==========================================
def get_theme_css(dark_mode=True):
    if dark_mode:
        return """
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
        }
        """
    else:
        return """
        :root {
            --bg:        #f5f7fa;
            --surface:   #ffffff;
            --surface2:  #eef1f7;
            --border:    #dde1eb;
            --accent:    #00a87a;
            --accent2:   #0070cc;
            --danger:    #e03040;
            --text:      #1a1d27;
            --muted:     #7a8395;
            --font:      'Sora', sans-serif;
            --mono:      'DM Mono', monospace;
        }
        html, body, [data-testid="stAppViewContainer"] {
            background-color: var(--bg) !important;
            color: var(--text) !important;
        }
        """

def inject_css(dark_mode=True):
    theme = get_theme_css(dark_mode)
    st.markdown(f"""
<link href="https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700&family=DM+Mono:wght@300;400;500&display=swap" rel="stylesheet">
<style>
    {theme}

    html, body, [data-testid="stAppViewContainer"] {{
        font-family: var(--font) !important;
    }}

    /* Hide Streamlit chrome */
    #MainMenu, footer, header {{ visibility: hidden !important; }}
    [data-testid="stToolbar"] {{ display: none !important; }}
    .block-container {{
        padding-top: 1rem !important;
        padding-bottom: 5rem !important;  /* space for bottom nav */
        max-width: 720px !important;
    }}

    /* ---- Scrollbar ---- */
    ::-webkit-scrollbar {{ width: 4px; }}
    ::-webkit-scrollbar-track {{ background: var(--bg); }}
    ::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 2px; }}

    /* ---- Bottom Navigation Bar ---- */
    .bottom-nav {{
        position: fixed;
        bottom: 0; left: 0; right: 0;
        z-index: 9999;
        background: var(--surface);
        border-top: 1px solid var(--border);
        display: flex;
        justify-content: space-around;
        align-items: center;
        height: 62px;
        padding: 0 1rem;
        backdrop-filter: blur(12px);
        box-shadow: 0 -4px 20px rgba(0,0,0,0.3);
    }}
    .nav-btn {{
        display: flex; flex-direction: column;
        align-items: center; justify-content: center;
        gap: 3px; cursor: pointer;
        padding: 6px 18px;
        border-radius: 12px;
        border: none; background: transparent;
        color: var(--muted);
        font-family: var(--font);
        font-size: 0.65rem; font-weight: 500;
        transition: all 0.2s;
        letter-spacing: 0.03em;
    }}
    .nav-btn:hover {{ color: var(--accent); background: var(--surface2); }}
    .nav-btn.active {{ color: var(--accent); background: var(--surface2); }}
    .nav-btn .nav-icon {{ font-size: 1.25rem; }}

    /* ---- Brand bar ---- */
    .brand-bar {{
        display: flex; align-items: center;
        gap: 0.6rem; margin-bottom: 0.25rem;
    }}
    .brand-logo {{
        width: 36px; height: 36px;
        background: linear-gradient(135deg, var(--accent), var(--accent2));
        border-radius: 10px;
        display: flex; align-items: center; justify-content: center;
        font-size: 18px; line-height: 1;
        box-shadow: 0 0 16px rgba(0,200,150,0.35);
    }}
    .brand-name {{
        font-size: 1.55rem; font-weight: 700;
        letter-spacing: -0.03em;
        background: linear-gradient(90deg, var(--accent), var(--accent2));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }}
    .brand-sub {{
        font-size: 0.82rem; color: var(--muted);
        font-weight: 300; margin-bottom: 0.8rem;
    }}

    /* ---- Ticker Banner ---- */
    .ticker-wrap {{
        overflow: hidden; white-space: nowrap;
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 0.5rem 1rem;
        margin-bottom: 0.8rem;
    }}
    .ticker-inner {{
        display: inline-flex; gap: 2.5rem;
        animation: ticker-scroll 20s linear infinite;
    }}
    .ticker-wrap:hover .ticker-inner {{ animation-play-state: paused; }}
    @keyframes ticker-scroll {{
        0% {{ transform: translateX(0); }}
        100% {{ transform: translateX(-50%); }}
    }}
    .ticker-item {{
        display: inline-flex; align-items: center; gap: 0.5rem;
        font-family: var(--mono); font-size: 0.8rem;
    }}
    .ticker-label {{ color: var(--muted); font-size: 0.72rem; }}
    .ticker-price {{ color: var(--text); font-weight: 500; }}
    .ticker-up {{ color: var(--accent); }}
    .ticker-down {{ color: var(--danger); }}

    /* ---- Quick Action Buttons ---- */
    .quick-actions {{
        display: flex; gap: 0.6rem;
        flex-wrap: wrap; margin-bottom: 1rem;
    }}
    .quick-btn {{
        background: var(--surface2) !important;
        border: 1px solid var(--border) !important;
        color: var(--text) !important;
        font-family: var(--font) !important;
        font-size: 0.78rem !important;
        font-weight: 500 !important;
        border-radius: 20px !important;
        padding: 0.35rem 0.9rem !important;
        cursor: pointer; transition: all 0.2s;
    }}
    .quick-btn:hover {{ border-color: var(--accent) !important; color: var(--accent) !important; }}

    /* ---- Market pulse card ---- */
    .pulse-card {{
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 1rem 1.4rem;
        margin-bottom: 0.7rem;
        box-shadow: 0 2px 12px rgba(0,0,0,0.15);
    }}
    .pulse-label {{
        font-size: 0.68rem; text-transform: uppercase;
        letter-spacing: 0.1em; color: var(--muted); margin-bottom: 0.2rem;
    }}
    .pulse-price {{
        font-family: var(--mono); font-size: 1.3rem;
        font-weight: 500; color: var(--text);
    }}
    .pulse-change-up {{ font-family: var(--mono); font-size: 0.85rem; color: var(--accent); }}
    .pulse-change-down {{ font-family: var(--mono); font-size: 0.85rem; color: var(--danger); }}
    .pulse-dot {{
        width: 8px; height: 8px; border-radius: 50%;
        background: var(--accent); box-shadow: 0 0 8px var(--accent);
        animation: blink 1.4s infinite;
    }}
    @keyframes blink {{ 0%,100%{{opacity:1}} 50%{{opacity:0.3}} }}

    /* ---- Index Card (Markets tab) ---- */
    .index-card {{
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 1.1rem 1.4rem;
        margin-bottom: 0.8rem;
        position: relative; overflow: hidden;
        box-shadow: 0 2px 12px rgba(0,0,0,0.12);
    }}
    .index-card.up {{ border-left: 3px solid var(--accent); }}
    .index-card.down {{ border-left: 3px solid var(--danger); }}
    .index-name {{ font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.1em; color: var(--muted); }}
    .index-price {{ font-family: var(--mono); font-size: 1.45rem; font-weight: 600; color: var(--text); margin: 0.15rem 0; }}
    .index-change-up {{ font-family: var(--mono); font-size: 0.9rem; color: var(--accent); }}
    .index-change-down {{ font-family: var(--mono); font-size: 0.9rem; color: var(--danger); }}

    /* ---- MF Insight rows ---- */
    .mf-row {{
        display: flex; justify-content: space-between; align-items: center;
        padding: 0.6rem 0.9rem;
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 10px;
        margin-bottom: 0.4rem;
        font-size: 0.85rem;
    }}
    .mf-name {{ color: var(--text); font-weight: 500; }}
    .mf-up {{ font-family: var(--mono); color: var(--accent); font-size: 0.82rem; }}
    .mf-down {{ font-family: var(--mono); color: var(--danger); font-size: 0.82rem; }}

    /* ---- Section header ---- */
    .section-header {{
        font-size: 0.72rem; text-transform: uppercase;
        letter-spacing: 0.1em; color: var(--muted);
        margin: 1.2rem 0 0.6rem 0; font-weight: 600;
    }}

    /* ---- Goal Card ---- */
    .goal-card {{
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 12px rgba(0,0,0,0.12);
    }}
    .goal-title {{ font-size: 1rem; font-weight: 600; color: var(--text); margin-bottom: 0.2rem; }}
    .goal-meta {{ font-size: 0.78rem; color: var(--muted); margin-bottom: 0.7rem; }}
    .goal-sip {{ font-family: var(--mono); font-size: 1.05rem; color: var(--accent); font-weight: 500; }}
    .progress-track {{
        background: var(--surface2); border-radius: 999px;
        height: 7px; margin: 0.7rem 0 0.3rem 0; overflow: hidden;
    }}
    .progress-fill {{
        height: 100%; border-radius: 999px;
        background: linear-gradient(90deg, var(--accent), var(--accent2));
        transition: width 0.6s ease;
    }}
    .progress-label {{ font-size: 0.72rem; color: var(--muted); }}

    /* ---- Profile / Settings ---- */
    .settings-row {{
        display: flex; justify-content: space-between; align-items: center;
        padding: 0.9rem 1.1rem;
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 12px;
        margin-bottom: 0.5rem;
    }}
    .settings-label {{ font-size: 0.88rem; color: var(--text); font-weight: 500; }}
    .settings-sub {{ font-size: 0.72rem; color: var(--muted); margin-top: 0.1rem; }}
    .disclaimer-box {{
        background: var(--surface2);
        border: 1px solid var(--border);
        border-left: 3px solid var(--danger);
        border-radius: 10px;
        padding: 0.9rem 1.1rem;
        font-size: 0.8rem;
        color: var(--muted);
        line-height: 1.55;
        margin: 0.8rem 0;
    }}
    .about-box {{
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 1.1rem 1.4rem;
        margin-bottom: 0.8rem;
    }}
    .about-title {{ font-size: 1.05rem; font-weight: 700; color: var(--text); margin-bottom: 0.3rem; }}
    .about-desc {{ font-size: 0.82rem; color: var(--muted); line-height: 1.6; }}
    .version-badge {{
        display: inline-block;
        background: var(--surface2);
        border: 1px solid var(--border);
        border-radius: 20px;
        padding: 0.2rem 0.8rem;
        font-family: var(--mono);
        font-size: 0.72rem;
        color: var(--muted);
        margin-top: 0.4rem;
    }}

    /* ---- Chat ---- */
    [data-testid="stChatMessage"] {{
        background: transparent !important;
        border: none !important; padding: 0.1rem 0 !important;
    }}
    [data-testid="stChatMessage"][data-role="assistant"] .stMarkdown {{
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: 0 16px 16px 16px !important;
        padding: 0.9rem 1.1rem !important;
        font-size: 0.9rem !important; line-height: 1.65 !important;
        box-shadow: 0 2px 10px rgba(0,0,0,0.15) !important;
    }}
    [data-testid="stChatMessage"][data-role="user"] .stMarkdown {{
        background: linear-gradient(135deg, #0a2a20, #0a1f35) !important;
        border: 1px solid rgba(0,200,150,0.2) !important;
        border-radius: 16px 0 16px 16px !important;
        padding: 0.9rem 1.1rem !important;
        font-size: 0.9rem !important; line-height: 1.65 !important;
    }}
    [data-testid="stChatInput"] textarea {{
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: 12px !important;
        color: var(--text) !important;
        font-family: var(--font) !important;
        font-size: 0.88rem !important;
    }}
    [data-testid="stChatInput"] textarea:focus {{
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 2px rgba(0,200,150,0.15) !important;
    }}

    /* ---- Streamlit Buttons (global) ---- */
    .stButton > button {{
        background: linear-gradient(135deg, var(--accent), #00a87a) !important;
        color: #0d0f14 !important;
        font-family: var(--font) !important;
        font-weight: 600 !important; font-size: 0.85rem !important;
        border: none !important; border-radius: 10px !important;
        padding: 0.5rem 1.2rem !important;
        transition: opacity 0.2s, transform 0.15s !important;
        box-shadow: 0 3px 12px rgba(0,200,150,0.25) !important;
    }}
    .stButton > button:hover {{ opacity: 0.88 !important; transform: translateY(-1px) !important; }}
    .stButton > button:active {{ transform: translateY(0) !important; }}

    /* Danger button variant */
    .danger-btn > button {{
        background: linear-gradient(135deg, var(--danger), #cc2030) !important;
        box-shadow: 0 3px 12px rgba(255,79,94,0.25) !important;
    }}

    /* ---- Alerts ---- */
    [data-testid="stAlert"] {{
        background: var(--surface2) !important;
        border-radius: 10px !important;
        border-left: 3px solid var(--accent) !important;
        font-size: 0.85rem !important;
    }}

    /* ---- Sidebar ---- */
    [data-testid="stSidebar"] {{
        background: var(--surface) !important;
        border-right: 1px solid var(--border) !important;
    }}
    [data-testid="stSidebar"] * {{ color: var(--text) !important; font-family: var(--font) !important; }}
    .sidebar-stat-label {{
        font-size: 0.7rem; text-transform: uppercase;
        letter-spacing: 0.08em; color: var(--muted); margin-bottom: 0.15rem;
    }}
    .sidebar-stat-value {{
        font-family: var(--mono); font-size: 1.2rem;
        font-weight: 500; color: var(--accent); margin-bottom: 1rem;
    }}
    .sidebar-reset-note {{
        font-size: 0.75rem; color: var(--muted); margin-top: 1.5rem; line-height: 1.5;
    }}

    /* ---- Spinner ---- */
    [data-testid="stSpinner"] {{ color: var(--accent) !important; }}

    /* ---- Toggle ---- */
    [data-testid="stToggle"] span {{ background-color: var(--accent) !important; }}
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
# Session State Initialization (UPDATED — added new state keys)
# ==========================================
defaults = {
    "goals_set": 0,
    "impulses_skipped": 0,
    "messages": [],
    "chat_history": [],
    "active_tab": "Home",          # NEW: active bottom-nav tab
    "dark_mode": True,             # NEW: theme preference
    "goals": [],                   # NEW: structured goal objects list
    "pending_prompt": None,        # NEW: prompt injected from quick actions / Goals tab
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ==========================================
# Inject CSS (depends on dark_mode state)
# ==========================================
inject_css(st.session_state.dark_mode)

# ==========================================
# System Prompt — unchanged from original
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
# Database Connection — unchanged
# ==========================================
def connect_to_db():
    try:
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds_dict = dict(st.secrets["google_credentials"])
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        return client.open("GoalPe_Database").sheet1
    except Exception:
        return None

def log_to_database(log_type):
    sheet = connect_to_db()
    if sheet:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([timestamp, log_type])


# ==========================================
# UPDATED: Market Data Fetchers (extended)
# ==========================================
@st.cache_data(ttl=300)
def get_market_data():
    """Fetch Nifty 50, Sensex, Bank Nifty, and Gold price."""
    results = {}

    tickers = {
        "Nifty 50":   "^NSEI",
        "Sensex":     "^BSESN",
        "Bank Nifty": "^NSEBANK",
        "Gold":       "GC=F",   # Gold futures (USD); converted approximately
    }

    for name, symbol in tickers.items():
        try:
            t = yf.Ticker(symbol)
            hist = t.history(period="2d")
            if len(hist) >= 2:
                cur  = hist['Close'].iloc[-1]
                prev = hist['Close'].iloc[-2]
                chg  = cur - prev
                pct  = (chg / prev) * 100
                # Convert Gold from USD to INR approx (rough factor)
                if name == "Gold":
                    cur  *= 83.5
                    chg  *= 83.5
                results[name] = {"price": cur, "change": chg, "pct": pct}
        except Exception:
            results[name] = None

    return results

@st.cache_data(ttl=300)
def get_nifty_data():
    """Legacy wrapper for backward compatibility with original code."""
    data = get_market_data()
    n = data.get("Nifty 50")
    if n:
        return n["price"], n["change"], n["pct"]
    return None, None, None


# NEW: Simulated MF category data (yfinance doesn't have direct MF category feeds)
# In production, replace with an actual MF API (e.g., mfapi.in)
def get_mf_category_data():
    """
    Returns simulated mutual fund category performance.
    Replace with real API (mfapi.in / Morningstar) in production.
    """
    categories = [
        {"name": "Small Cap Fund",        "pct": +2.35},
        {"name": "Mid Cap Fund",          "pct": +1.87},
        {"name": "ELSS (Tax Saver)",      "pct": +1.54},
        {"name": "Flexi Cap Fund",        "pct": +1.22},
        {"name": "Large & Mid Cap Fund",  "pct": +0.98},
        {"name": "Large Cap Fund",        "pct": +0.61},
        {"name": "Multi Cap Fund",        "pct": +0.44},
        {"name": "Balanced Advantage",    "pct": -0.18},
        {"name": "Short Duration Debt",   "pct": -0.32},
        {"name": "Liquid Fund",           "pct": -0.55},
    ]
    sorted_cats = sorted(categories, key=lambda x: x["pct"], reverse=True)
    return sorted_cats[:5], sorted_cats[-5:][::-1]   # gainers, losers


# ==========================================
# Core AI Chat Function — unchanged
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

        clean_reply = re.sub(r'\s*\[LOG:\w+\]\s*$', '', raw_reply).strip()
        st.session_state.chat_history = chat.history
        return clean_reply, log_tag

    except Exception as e:
        error_str = str(e).lower()
        if "429" in str(e) or "quota" in error_str or "rate" in error_str:
            return "⏳ You've hit the Gemini rate limit. Please wait a moment and try again.", "chat"
        return "Something went wrong. Please try again.", "chat"


# ==========================================
# NEW: Goal Extraction Helper
# ==========================================
def extract_goal_from_reply(reply: str, user_msg: str) -> dict | None:
    """
    Very lightweight parser to pull structured goal data out of AI replies.
    Looks for patterns like "₹X", "X months", "SIP of ₹Y".
    Returns a dict or None.
    """
    goal = {}

    # Target amount
    amounts = re.findall(r'₹\s*([\d,]+(?:\.\d+)?)\s*(?:lakh|L|lakhs)?', reply, re.I)
    if amounts:
        raw = amounts[0].replace(",", "")
        val = float(raw)
        # Check if 'lakh' context nearby
        if re.search(r'₹\s*[\d,]+\s*(?:lakh|L|lakhs)', reply, re.I):
            val *= 100_000
        goal["target"] = int(val)

    # Duration in months
    months_match = re.search(r'(\d+)\s*months?', reply, re.I)
    years_match  = re.search(r'(\d+)\s*years?', reply, re.I)
    if months_match:
        goal["months"] = int(months_match.group(1))
    elif years_match:
        goal["months"] = int(years_match.group(1)) * 12

    # Monthly SIP
    sip_match = re.search(r'(?:SIP|monthly|invest)\s*(?:of\s*)?₹\s*([\d,]+)', reply, re.I)
    if sip_match:
        goal["sip"] = int(sip_match.group(1).replace(",", ""))

    # Goal name — try to pull from user's message
    for kw in ["for", "towards", "to save for", "goal for"]:
        nm = re.search(rf'{kw}\s+(?:a\s+|an\s+|my\s+)?([A-Za-z ]+?)(?:\.|,|$)', user_msg, re.I)
        if nm:
            goal["name"] = nm.group(1).strip().title()
            break
    if "name" not in goal:
        goal["name"] = "Savings Goal"

    goal["created"] = date.today().isoformat()
    goal["months_done"] = 0

    # Only return if we captured at least target + months
    if "target" in goal and "months" in goal:
        return goal
    return None


# ==========================================
# NEW: Reusable UI Components
# ==========================================

def render_ticker_banner(market_data: dict):
    """Horizontal scrollable ticker with live market values."""
    items_html = ""
    for name, data in market_data.items():
        if data is None:
            continue
        arrow = "▲" if data["change"] >= 0 else "▼"
        cls   = "ticker-up" if data["change"] >= 0 else "ticker-down"
        price_str = f"₹{data['price']:,.0f}" if name != "Gold" else f"₹{data['price']:,.0f}/10g"
        items_html += f"""
        <span class="ticker-item">
            <span class="ticker-label">{name}</span>
            <span class="ticker-price">{price_str}</span>
            <span class="{cls}">{arrow} {abs(data['pct']):.2f}%</span>
        </span>"""

    # Duplicate for seamless loop
    st.markdown(f"""
    <div class="ticker-wrap">
        <div class="ticker-inner">
            {items_html}
            {items_html}
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_index_card(name: str, data: dict | None):
    """Render a single index card for the Markets tab."""
    if data is None:
        st.markdown(f"""
        <div class="index-card">
            <div class="index-name">{name}</div>
            <div class="index-price" style="color:var(--muted);">Unavailable</div>
        </div>""", unsafe_allow_html=True)
        return
    direction = "up" if data["change"] >= 0 else "down"
    arrow = "▲" if data["change"] >= 0 else "▼"
    change_cls = "index-change-up" if data["change"] >= 0 else "index-change-down"
    st.markdown(f"""
    <div class="index-card {direction}">
        <div class="index-name">{name}</div>
        <div class="index-price">₹{data['price']:,.2f}</div>
        <div class="{change_cls}">
            {arrow} {abs(data['change']):,.2f} &nbsp;({data['pct']:+.2f}%)
        </div>
    </div>""", unsafe_allow_html=True)


def render_goal_card(goal: dict, idx: int):
    """Render a goal progress card."""
    months_done  = goal.get("months_done", 0)
    total_months = goal.get("months", 1)
    pct_done     = min(100, int((months_done / total_months) * 100))
    target_str   = f"₹{goal.get('target', 0):,}"
    sip_str      = f"₹{goal.get('sip', 0):,}/mo" if goal.get("sip") else "Calculating…"
    created      = goal.get("created", "")

    st.markdown(f"""
    <div class="goal-card">
        <div class="goal-title">🎯 {goal['name']}</div>
        <div class="goal-meta">
            Target: {target_str} &nbsp;·&nbsp; {total_months} months &nbsp;·&nbsp; Started {created}
        </div>
        <div class="goal-sip">SIP: {sip_str}</div>
        <div class="progress-track">
            <div class="progress-fill" style="width:{pct_done}%;"></div>
        </div>
        <div class="progress-label">{months_done} of {total_months} months completed ({pct_done}%)</div>
    </div>
    """, unsafe_allow_html=True)


# ==========================================
# NEW: Bottom Navigation Bar
# ==========================================
def render_bottom_nav():
    tabs = [
        ("🏠", "Home"),
        ("📈", "Markets"),
        ("🎯", "Goals"),
        ("👤", "Profile"),
    ]
    cols = st.columns(len(tabs))
    for col, (icon, label) in zip(cols, tabs):
        active_cls = "active" if st.session_state.active_tab == label else ""
        with col:
            if st.button(f"{icon}\n{label}", key=f"nav_{label}", use_container_width=True):
                st.session_state.active_tab = label
                st.rerun()


# ==========================================
# TAB RENDERERS
# ==========================================

# ------------------------------------------
# TAB 1: HOME (enhanced — keeps existing chat)
# ------------------------------------------
def render_home_tab():
    # Brand header
    st.markdown("""
    <div class="brand-bar">
        <div class="brand-logo">🎯</div>
        <span class="brand-name">GoalPe</span>
    </div>
    <div class="brand-sub">Your AI Wealth Coach — set a goal, or ask anything about money.</div>
    """, unsafe_allow_html=True)

    # ---- Market Ticker Banner (NEW) ----
    market_data = get_market_data()
    if market_data:
        render_ticker_banner(market_data)

    # ---- Quick Action Buttons (NEW) ----
    st.markdown('<div class="section-header">Quick Actions</div>', unsafe_allow_html=True)
    qa_cols = st.columns(3)
    quick_actions = {
        "🎯 Set a Goal":      "I want to set a new savings goal.",
        "❓ Ask a Question":   "What is a SIP and how does it work?",
        "📊 Market Today":    "Give me a brief summary of how the Indian market is performing today and what it means for my investments.",
    }
    for col, (label, prompt) in zip(qa_cols, quick_actions.items()):
        with col:
            if st.button(label, key=f"qa_{label}", use_container_width=True):
                st.session_state.pending_prompt = prompt
                st.rerun()

    st.markdown("---")

    # ---- Existing Chat Logic (unchanged) ----
    if not st.session_state.messages:
        opening = "Hey! 👋 I'm GoalPe, your personal AI wealth coach. I can help you plan savings goals, figure out your monthly SIP, talk through investment options, or just answer any finance questions you have.\n\nWhat's on your mind today?"
        st.session_state.messages.append({"role": "assistant", "content": opening})

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Handle pending_prompt injected by quick actions or Goals tab
    injected = st.session_state.get("pending_prompt")
    if injected:
        st.session_state.pending_prompt = None
        st.chat_message("user").markdown(injected)
        st.session_state.messages.append({"role": "user", "content": injected})
        with st.spinner("Thinking..."):
            reply, log_tag = chat_with_goalpe(injected)
            _handle_log(log_tag, injected, reply)
        with st.chat_message("assistant"):
            st.markdown(reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})

    if prompt := st.chat_input("Ask me anything — goals, SIPs, investments, or just say hi!"):
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.spinner("Thinking..."):
            reply, log_tag = chat_with_goalpe(prompt)
            _handle_log(log_tag, prompt, reply)
        with st.chat_message("assistant"):
            st.markdown(reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})


def _handle_log(log_tag: str, user_msg: str, reply: str):
    """Update counters, extract goals, log to DB."""
    if log_tag == "new_goal":
        st.session_state.goals_set += 1
        # Try to parse a structured goal from the AI reply
        goal = extract_goal_from_reply(reply, user_msg)
        if goal:
            st.session_state.goals.append(goal)
    elif log_tag == "impulse":
        st.session_state.impulses_skipped += 1
    try:
        log_to_database(log_tag)
    except Exception:
        pass


# ------------------------------------------
# TAB 2: MARKETS (NEW)
# ------------------------------------------
def render_markets_tab():
    st.markdown("""
    <div class="brand-bar">
        <div class="brand-logo">📈</div>
        <span class="brand-name">Markets</span>
    </div>
    <div class="brand-sub">Live indices & mutual fund category insights.</div>
    """, unsafe_allow_html=True)

    market_data = get_market_data()

    # ---- Index Cards ----
    st.markdown('<div class="section-header">📊 Market Indices</div>', unsafe_allow_html=True)
    for name in ["Nifty 50", "Sensex", "Bank Nifty"]:
        render_index_card(name, market_data.get(name))

    # Gold card
    gold = market_data.get("Gold")
    if gold:
        direction = "up" if gold["change"] >= 0 else "down"
        arrow = "▲" if gold["change"] >= 0 else "▼"
        change_cls = "index-change-up" if gold["change"] >= 0 else "index-change-down"
        st.markdown(f"""
        <div class="index-card {direction}">
            <div class="index-name">Gold (MCX approx)</div>
            <div class="index-price">₹{gold['price']:,.0f} <span style="font-size:0.7rem;color:var(--muted);">/10g</span></div>
            <div class="{change_cls}">{arrow} {abs(gold['pct']):.2f}% &nbsp;(approx)</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ---- MF Category Insights ----
    st.markdown('<div class="section-header">🏆 Top Gaining MF Categories Today</div>', unsafe_allow_html=True)
    gainers, losers = get_mf_category_data()
    for cat in gainers:
        st.markdown(f"""
        <div class="mf-row">
            <span class="mf-name">{cat['name']}</span>
            <span class="mf-up">▲ {cat['pct']:+.2f}%</span>
        </div>""", unsafe_allow_html=True)

    st.markdown('<div class="section-header">📉 Top Losing MF Categories Today</div>', unsafe_allow_html=True)
    for cat in losers:
        st.markdown(f"""
        <div class="mf-row">
            <span class="mf-name">{cat['name']}</span>
            <span class="mf-down">▼ {abs(cat['pct']):.2f}%</span>
        </div>""", unsafe_allow_html=True)

    st.markdown("""
    <div style="font-size:0.72rem;color:var(--muted);margin-top:1rem;line-height:1.5;">
        ⚠️ MF category data is illustrative. Real-time data requires a dedicated MF data provider (e.g., mfapi.in).
    </div>""", unsafe_allow_html=True)


# ------------------------------------------
# TAB 3: GOALS (NEW)
# ------------------------------------------
def render_goals_tab():
    st.markdown("""
    <div class="brand-bar">
        <div class="brand-logo">🎯</div>
        <span class="brand-name">My Goals</span>
    </div>
    <div class="brand-sub">Track your investment goals and SIP progress.</div>
    """, unsafe_allow_html=True)

    # New Goal button
    if st.button("➕  New Goal", use_container_width=True):
        st.session_state.pending_prompt = "I want to create a new investment goal"
        st.session_state.active_tab = "Home"
        st.rerun()

    goals = st.session_state.goals

    if not goals:
        st.info("No goals yet! Chat with GoalPe on the Home tab to set your first savings goal. 🎯")
    else:
        st.markdown(f'<div class="section-header">Your {len(goals)} active goal(s)</div>', unsafe_allow_html=True)
        for i, goal in enumerate(goals):
            render_goal_card(goal, i)

            # Controls to manually advance progress
            col_a, col_b = st.columns([1, 1])
            with col_a:
                if st.button("✅ +1 Month Done", key=f"inc_{i}", use_container_width=True):
                    st.session_state.goals[i]["months_done"] = min(
                        goal["months_done"] + 1, goal["months"]
                    )
                    st.rerun()
            with col_b:
                if st.button("🗑 Remove", key=f"del_{i}", use_container_width=True):
                    st.session_state.goals.pop(i)
                    st.rerun()


# ------------------------------------------
# TAB 4: PROFILE (NEW)
# ------------------------------------------
def render_profile_tab():
    st.markdown("""
    <div class="brand-bar">
        <div class="brand-logo">👤</div>
        <span class="brand-name">Profile</span>
    </div>
    <div class="brand-sub">Settings & preferences.</div>
    """, unsafe_allow_html=True)

    # ---- About ----
    st.markdown('<div class="section-header">About</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="about-box">
        <div class="about-title">GoalPe — AI Investment Assistant</div>
        <div class="about-desc">
            GoalPe helps you set savings goals, calculate your monthly SIP, and build disciplined
            investment habits — powered by Google Gemini AI. Designed for retail investors in India.
        </div>
        <div class="version-badge">v2.0.0</div>
    </div>
    """, unsafe_allow_html=True)

    # ---- Disclaimer ----
    st.markdown('<div class="section-header">Disclaimer</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="disclaimer-box">
        ⚠️ <strong>This is not SEBI-registered financial advice.</strong><br>
        GoalPe is an AI assistant for informational and educational purposes only.
        Always consult a SEBI-registered investment advisor before making financial decisions.
        Mutual fund investments are subject to market risks.
    </div>
    """, unsafe_allow_html=True)

    # ---- Settings ----
    st.markdown('<div class="section-header">Preferences</div>', unsafe_allow_html=True)

    # Dark / Light mode toggle
    dark = st.toggle("🌙  Dark Mode", value=st.session_state.dark_mode, key="theme_toggle")
    if dark != st.session_state.dark_mode:
        st.session_state.dark_mode = dark
        st.rerun()

    # ---- Stats ----
    st.markdown('<div class="section-header">Session Stats</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"""
        <div class="about-box" style="text-align:center;">
            <div class="about-desc">Goals Set</div>
            <div style="font-family:var(--mono);font-size:2rem;color:var(--accent);font-weight:600;">
                {st.session_state.goals_set}
            </div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="about-box" style="text-align:center;">
            <div class="about-desc">Impulses Discussed</div>
            <div style="font-family:var(--mono);font-size:2rem;color:var(--accent2);font-weight:600;">
                {st.session_state.impulses_skipped}
            </div>
        </div>""", unsafe_allow_html=True)

    # ---- Clear Data ----
    st.markdown('<div class="section-header">Danger Zone</div>', unsafe_allow_html=True)
    st.markdown('<div class="danger-btn">', unsafe_allow_html=True)
    if st.button("🗑  Clear All Data (Chat + Goals)", use_container_width=True):
        st.session_state.messages      = []
        st.session_state.chat_history  = []
        st.session_state.goals         = []
        st.session_state.goals_set     = 0
        st.session_state.impulses_skipped = 0
        st.session_state.active_tab    = "Home"
        st.success("All data cleared. Starting fresh!")
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


# ==========================================
# Sidebar — kept minimal, shows session stats
# ==========================================
with st.sidebar:
    st.markdown("""
    <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:1.4rem;margin-top:0.5rem;">
        <div class="brand-logo" style="width:28px;height:28px;font-size:14px;">🎯</div>
        <span style="font-weight:700;font-size:1.1rem;letter-spacing:-0.02em;">GoalPe</span>
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

    st.markdown(
        '<p class="sidebar-reset-note">GoalPe is an AI assistant and does not provide certified financial advice. Always consult a SEBI-registered advisor for major decisions.</p>',
        unsafe_allow_html=True
    )


# ==========================================
# MAIN ROUTER — Bottom Nav + Tab Rendering
# ==========================================
active = st.session_state.active_tab

if active == "Home":
    render_home_tab()
elif active == "Markets":
    render_markets_tab()
elif active == "Goals":
    render_goals_tab()
elif active == "Profile":
    render_profile_tab()

# Render bottom nav LAST so it overlays content
render_bottom_nav()
