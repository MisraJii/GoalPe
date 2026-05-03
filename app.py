import streamlit as st
import google.generativeai as genai
import json
import yfinance as yf
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ==========================================
# 1. Configuration & Setup
# ==========================================

st.set_page_config(page_title="GoalPe", page_icon="🎯", layout="centered")

# --- API Key Gate ---
if "gemini_api_key" not in st.session_state:
    st.session_state.gemini_api_key = ""

if not st.session_state.gemini_api_key:
    st.title("🎯 GoalPe")
    st.markdown("**Your AI Wealth Coach.** Set a goal, or tell us what you're tempted to buy today.")
    st.markdown("---")
    api_key_input = st.text_input("Enter your Gemini API Key", type="password", placeholder="AIza...")
    if st.button("Continue"):
        if not api_key_input.strip():
            st.warning("Please enter your Gemini API key to continue.")
        else:
            st.session_state.gemini_api_key = api_key_input.strip()
            st.rerun()
    else:
        st.info("Please enter your Gemini API key to continue.")
    st.stop()

# Configure Gemini with the session key
genai.configure(api_key=st.session_state.gemini_api_key)
model = genai.GenerativeModel('gemini-2.5-flash')

# ==========================================
# 2. Database Connection (Google Sheets)
# ==========================================
def connect_to_db():
    try:
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        
        # Access the secrets directly as a dictionary
        creds_dict = dict(st.secrets["google_credentials"])
        
        # Fix the newline issue that often breaks the private key
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        return client.open("GoalPe_Database").sheet1
    except Exception as e:
        # This will help us debug if there's still a tiny typo
        st.error(f"Database Error: {e}")
        return None

def log_to_database(intent, item, amount, months):
    sheet = connect_to_db()
    if sheet:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Appends a new row to your Google Sheet instantly
        sheet.append_row([timestamp, intent, item, amount, months])

# ==========================================
# 3. Live Market Data
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
# 4. Math & Logic Engine
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
    
    Return ONLY valid JSON.
    """
    try:
        response = model.generate_content(prompt)
        cleaned_response = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned_response)
    except Exception as e:
        error_str = str(e).lower()
        if "api_key" in error_str or "invalid" in error_str or "401" in error_str or "403" in error_str:
            st.error("❌ Invalid API key. Please refresh the page and enter a valid Gemini API key.")
            st.session_state.gemini_api_key = ""
            st.stop()
        return {"error": "I couldn't quite catch that. Could you rephrase it?"}

# ==========================================
# 5. Streamlit User Interface
# ==========================================

st.title("🎯 GoalPe")
st.markdown("**Your AI Wealth Coach.** Set a goal, or tell us what you're tempted to buy today.")

# --- Display Live Market Pulse ---
current_price, change, change_pct = get_nifty_data()
if current_price:
    st.caption("Live Market Pulse")
    col1, col2, col3 = st.columns(3)
    col1.metric("Nifty 50", f"₹{current_price:,.2f}", f"{change:,.2f} ({change_pct:.2f}%)")
st.markdown("---")

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hi! What are you saving for today? Or, are you tempted to buy something right now?"}]
if "active_goal" not in st.session_state:
    st.session_state.active_goal = None
if "active_sip" not in st.session_state:
    st.session_state.active_sip = 0

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("E.g., I need ₹50k for a laptop in 14 months"):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.spinner("Analyzing your finances..."):
        data = extract_intent(prompt)
        
        if "error" in data:
            bot_reply = data["error"]
            
        elif data.get("intent") == "refusal":
            bot_reply = f"**🛡️ Compliance Guardrail Triggered:**\n\n{data.get('message')}"
            log_to_database("Guardrail Block", "Illegal Advice Attempt", 0, 0)
            
        elif data.get("intent") == "new_goal":
            target = data.get("amount", 0)
            months = data.get("months", 6)
            item = data.get("item", "Goal")
            portfolio = data.get("portfolio", {"Liquid Fund": 100})
            blended_rate = data.get("blended_return", 0.065)
            explanation = data.get("explanation", "Keeping it safe in a liquid fund.")
            
            if target > 0:
                sip = calculate_sip(target, months, blended_rate)
                st.session_state.active_goal = item
                st.session_state.active_sip = sip
                
                # --- FIRE TO DATABASE ---
                log_to_database("New Goal", item, target, months)
                
                portfolio_text = "\n".join([f"- **{k}**: {v}%" for k, v in portfolio.items()])
                bot_reply = f"Awesome! A **{item}** sounds great.\n\nTo hit **₹{target:,}** in **{months} months**, you need to save **₹{sip:,} / month**.\n\n### 📊 Your Custom AI Portfolio (Expected Return: {blended_rate*100:.1f}%)\n{portfolio_text}\n\n💡 *Why this mix?* {explanation}\n\n**Should I set up this automated split for you?**"
            else:
                bot_reply = f"I'd love to help you build a portfolio for that {item}! Roughly how much will it cost?"

        elif data.get("intent") == "skip_expense":
            expense_amt = data.get("amount", 0)
            expense_item = data.get("item", "purchase")
            
            if st.session_state.active_goal and st.session_state.active_sip > 0:
                daily_sip_rate = st.session_state.active_sip / 30
                days_saved = max(1, int(expense_amt / daily_sip_rate))
                
                # --- FIRE TO DATABASE ---
                log_to_database("Impulse Skipped", expense_item, expense_amt, 0)
                
                bot_reply = f"**Hold up! 🛑** \n\nIf you skip that **{expense_item}** and invest that ₹{expense_amt} into your custom portfolio right now, you will reach your **{st.session_state.active_goal}** goal **{days_saved} days earlier!** \n\nShould we transfer ₹{expense_amt} to your goal instead?"
            else:
                bot_reply = f"Skipping that **{expense_item}** is a great idea to save ₹{expense_amt}. You should set a major savings goal first!"

    with st.chat_message("assistant"):
        st.markdown(bot_reply)
        if data.get("intent") == "new_goal" and data.get("amount", 0) > 0:
             st.button("✅ Yes, Start Saving")
        elif data.get("intent") == "skip_expense" and st.session_state.active_goal:
            st.button(f"🚀 Skip & Invest ₹{data.get('amount')}")
            
    st.session_state.messages.append({"role": "assistant", "content": bot_reply})
