import streamlit as st
import google.generativeai as genai
import json
import yfinance as yf

# ==========================================
# 1. Configuration & Setup
# ==========================================
# Using Streamlit Secrets for the live app (Secure)
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# Using the latest fast model
model = genai.GenerativeModel('gemini-2.5-flash')

# ==========================================
# 2. Live Market Data (Phase 1)
# ==========================================
@st.cache_data(ttl=300) # Caches data for 5 mins so it doesn't slow down the app
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
# 3. Math & Logic Engine
# ==========================================
def calculate_sip(target_amount, months, annual_rate):
    """Calculates the monthly SIP required to hit a target amount."""
    if months <= 0: return target_amount
    monthly_rate = annual_rate / 12
    sip_amount = (target_amount * monthly_rate) / (((1 + monthly_rate)**months) - 1)
    return round(sip_amount)

def extract_intent(user_input):
    """Uses Gemini to act as a Robo-Advisor, Coach, or Compliance Guard."""
    prompt = f"""
    You are an expert AI wealth manager and behavioral finance coach for retail users in India. 
    Analyze the user's input.

    If the user asks for DIRECT STOCK, CRYPTO, or TRADING ADVICE (e.g., "Should I buy Dogecoin?", "Is Reliance a good stock?"):
    Return a JSON object with:
    {{"intent": "refusal", "message": "I am designed for goal-based wealth building via diversified mutual funds, not direct stock or crypto trading. Let's focus on your long-term goals instead!"}}
    
    If the user wants to SAVE for a big goal, return a JSON object with:
    1. "intent": "new_goal"
    2. "amount": The target amount (integer). Return 0 if not specified.
    3. "months": Time horizon (integer). Assume 6 if not specified.
    4. "item": 2-3 word name for the goal.
    5. "portfolio": A dictionary of 2-3 specific Indian mutual fund categories (e.g., "Liquid Fund", "Arbitrage Fund", "Money Market", "Conservative Hybrid") and their percentage allocation adding up to 100.
        - Rules: If months < 6, use 100% Liquid/Overnight. If 6-12 months, mix Liquid and Arbitrage. If 12-24 months, introduce Conservative Hybrid.
    6. "blended_return": Expected annual return rate as a decimal (e.g., 0.068 for 6.8%) based on the mix.
    7. "explanation": A 1-sentence simple explanation of WHY you chose this specific mix for their timeframe.
    
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
        return {"error": "I couldn't quite catch that. Could you rephrase it?"}

# ==========================================
# 4. Streamlit User Interface
# ==========================================
st.set_page_config(page_title="GoalPe", page_icon="🎯", layout="centered")

st.title("🎯 GoalPe")
st.markdown("**Your AI Wealth Coach.** Set a goal, or tell us what you're tempted to buy today.")

# --- Display Live Market Pulse ---
current_price, change, change_pct = get_nifty_data()
if current_price:
    st.caption("Live Market Pulse")
    col1, col2, col3 = st.columns(3)
    col1.metric("Nifty 50", f"₹{current_price:,.2f}", f"{change:,.2f} ({change_pct:.2f}%)")
st.markdown("---")

# Initialize chat history and active goals in session state
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hi! What are you saving for today? Or, are you tempted to buy something right now?"}
    ]
if "active_goal" not in st.session_state:
    st.session_state.active_goal = None
if "active_sip" not in st.session_state:
    st.session_state.active_sip = 0

# Display chat messages from history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# React to user input
if prompt := st.chat_input("E.g., I need ₹50k for a laptop in 14 months, OR I'm about to spend ₹400"):
    # Display user prompt
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.spinner("Analyzing your finances..."):
        data = extract_intent(prompt)
        
        if "error" in data:
            bot_reply = data["error"]
            
        # --- LOGIC FLOW 1: REFUSAL (Guardrails) ---
        elif data.get("intent") == "refusal":
            bot_reply = f"**🛡️ Compliance Guardrail Triggered:**\n\n{data.get('message')}"
            
        # --- LOGIC FLOW 2: NEW GOAL (Robo-Advisor) ---
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
                
                portfolio_text = "\n".join([f"- **{k}**: {v}%" for k, v in portfolio.items()])
                
                bot_reply = f"Awesome! A **{item}** sounds great.\n\n"
                bot_reply += f"To hit **₹{target:,}** in **{months} months**, you need to save **₹{sip:,} / month**.\n\n"
                bot_reply += f"### 📊 Your Custom AI Portfolio (Expected Return: {blended_rate*100:.1f}%)\n"
                bot_reply += f"{portfolio_text}\n\n"
                bot_reply += f"💡 *Why this mix?* {explanation}\n\n"
                bot_reply += "**Should I set up this automated split for you?**"
            else:
                bot_reply = f"I'd love to help you build a portfolio for that {item}! Roughly how much will it cost?"

        # --- LOGIC FLOW 3: IMPULSE SKIP (Behavioral Engine) ---
        elif data.get("intent") == "skip_expense":
            expense_amt = data.get("amount", 0)
            expense_item = data.get("item", "purchase")
            
            if st.session_state.active_goal and st.session_state.active_sip > 0:
                daily_sip_rate = st.session_state.active_sip / 30
                days_saved = int(expense_amt / daily_sip_rate)
                if days_saved < 1: days_saved = 1 
                
                bot_reply = f"**Hold up! 🛑** \n\nIf you skip that **{expense_item}** and invest that ₹{expense_amt} into your custom portfolio right now, you will reach your **{st.session_state.active_goal}** goal **{days_saved} days earlier!** \n\nShould we transfer ₹{expense_amt} to your goal instead?"
            else:
                bot_reply = f"Skipping that **{expense_item}** is a great idea to save ₹{expense_amt}. You should set a major savings goal first (like a trip or a gadget) so we can track how fast you hit it!"

    # Display assistant response
    with st.chat_message("assistant"):
        st.markdown(bot_reply)
        
        # Add dynamic buttons
        if data.get("intent") == "new_goal" and data.get("amount", 0) > 0:
             st.button("✅ Yes, Start Saving")
        elif data.get("intent") == "skip_expense" and st.session_state.active_goal:
            st.button(f"🚀 Skip & Invest ₹{data.get('amount')}")
            
    st.session_state.messages.append({"role": "assistant", "content": bot_reply})
