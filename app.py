import streamlit as st
import google.generativeai as genai
import json

# ==========================================
# 1. Configuration & Setup
# ==========================================
# Using Streamlit Secrets for the live app
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash')

ANNUAL_RETURN_RATE = 0.065 # 6.5% safe liquid fund return

# ==========================================
# 2. Math & Logic Engine
# ==========================================
def calculate_sip(target_amount, months, annual_rate):
    """Calculates the monthly SIP required to hit a target amount."""
    if months <= 0: return target_amount
    monthly_rate = annual_rate / 12
    sip_amount = (target_amount * monthly_rate) / (((1 + monthly_rate)**months) - 1)
    return round(sip_amount)

def extract_intent(user_input):
    """Uses Gemini to classify the input as a goal or a daily expense."""
    prompt = f"""
    You are an AI financial behavioral engine. Classify the user's input.
    
    If the user wants to SAVE for something big (a trip, phone, etc.), return:
    {{"intent": "new_goal", "amount": 10000, "months": 6, "item": "Kochi Trip"}}
    (Assume 6 months if not specified. Amount is integer).
    
    If the user is tempted to SPEND money right now on a daily impulse (like a burger, movie ticket, coffee, shoes), return:
    {{"intent": "skip_expense", "amount": 400, "months": 0, "item": "movie ticket"}}
    (Amount is integer).

    User Input: "{user_input}"
    
    Return ONLY a valid JSON object.
    """
    try:
        response = model.generate_content(prompt)
        cleaned_response = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned_response)
    except Exception as e:
        return {"error": "Could not process that. Try rephrasing!"}

# ==========================================
# 3. Streamlit User Interface
# ==========================================
st.set_page_config(page_title="GoalPe", page_icon="🎯", layout="centered")

st.title("🎯 GoalPe")
st.markdown("**Your conversational savings assistant.** Set a goal, or tell us what you're tempted to buy today.")
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
if prompt := st.chat_input("E.g., I need ₹15k for a phone, OR I'm about to spend ₹400 on a burger"):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.spinner("Analyzing your finances..."):
        data = extract_intent(prompt)
        
        if "error" in data:
            bot_reply = data["error"]
            
        elif data.get("intent") == "new_goal":
            target = data.get("amount", 0)
            months = data.get("months", 6)
            item = data.get("item", "Goal")
            
            if target > 0:
                sip = calculate_sip(target, months, ANNUAL_RETURN_RATE)
                # Save as active goal in memory
                st.session_state.active_goal = item
                st.session_state.active_sip = sip
                
                bot_reply = f"Awesome! A **{item}** sounds great. \n\nTo hit **₹{target:,}** in **{months} months**, you need to save **₹{sip:,} / month**. \n\nI'll lock this in as your active goal! 🚀"
            else:
                bot_reply = "I'd love to help! Roughly how much will that cost?"

        elif data.get("intent") == "skip_expense":
            expense_amt = data.get("amount", 0)
            expense_item = data.get("item", "purchase")
            
            if st.session_state.active_goal and st.session_state.active_sip > 0:
                # Math: Calculate how many days of SIP this expense equals
                daily_sip_rate = st.session_state.active_sip / 30
                days_saved = int(expense_amt / daily_sip_rate)
                
                if days_saved < 1: days_saved = 1 # Minimum 1 day for psychological win
                
                bot_reply = f"**Hold up! 🛑** \n\nIf you skip that **{expense_item}** and invest that ₹{expense_amt} into your fund right now, you will reach your **{st.session_state.active_goal}** goal **{days_saved} days earlier!** \n\nShould we transfer ₹{expense_amt} to your goal instead?"
            else:
                bot_reply = f"Skipping that **{expense_item}** is a great idea to save ₹{expense_amt}. You should set a major savings goal first so we can track how fast you hit it!"

    with st.chat_message("assistant"):
        st.markdown(bot_reply)
        if data.get("intent") == "skip_expense" and st.session_state.active_goal:
            st.button(f"🚀 Skip & Invest ₹{data.get('amount')}")
            
    st.session_state.messages.append({"role": "assistant", "content": bot_reply})
