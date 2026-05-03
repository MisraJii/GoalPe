import streamlit as st
import google.generativeai as genai
import json

# ==========================================
# 1. Configuration & Setup
# ==========================================
# Replace 'YOUR_API_KEY' with your actual Gemini API Key from Google AI Studio
genai.configure(api_key="AIzaSyB1Ze3vW9J1wEv8jgM7PYqhlAlGGlRrpmo")

# Set up the model. We use gemini-1.5-flash as it's fast and perfect for quick extraction
model = genai.GenerativeModel('gemini-2.5-flash')

# Set safe assumptions for "Bharat" (Tier 2/3) short-term debt funds
ANNUAL_RETURN_RATE = 0.065 # 6.5% safe liquid fund return

# ==========================================
# 2. Math & Logic Engine
# ==========================================
def calculate_sip(target_amount, months, annual_rate):
    """Calculates the monthly SIP required to hit a target amount."""
    if months <= 0:
        return target_amount
    
    monthly_rate = annual_rate / 12
    # Formula for SIP based on Future Value of Ordinary Annuity
    sip_amount = (target_amount * monthly_rate) / (((1 + monthly_rate)**months) - 1)
    return round(sip_amount)

def extract_goal_data(user_input):
    """Uses Gemini to extract financial variables from natural language."""
    prompt = f"""
    You are a financial extraction AI. Read the user's input and extract:
    1. 'amount': The target money they want to save (as an integer).
    2. 'months': The time horizon in months (as an integer).
    3. 'goal': A short 2-3 word name for their goal (e.g., 'Kochi Trip', 'New Phone').
    
    If the user doesn't specify an exact timeframe, assume 6 months.
    If the user doesn't specify an amount, return 0 for amount.
    
    User Input: "{user_input}"
    
    Return ONLY a valid JSON object in this format: {{"amount": 10000, "months": 6, "goal": "New Bike"}}
    """
    
    response = model.generate_content(prompt)
    
    try:
        # Clean the response to ensure it's pure JSON
        cleaned_response = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(cleaned_response)
        return data
    except Exception as e:
        return {"error": "Could not understand the goal. Please specify the amount and timeframe."}

# ==========================================
# 3. Streamlit User Interface
# ==========================================
st.set_page_config(page_title="GoalPe", page_icon="🎯", layout="centered")

st.title("🎯 GoalPe")
st.markdown("**Your conversational savings assistant.** Just tell us what you want to achieve.")
st.markdown("---")

# Initialize chat history in session state
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hi! What are you saving for today? (e.g., 'I want to save ₹20,000 for a trip to Kochi in 6 months')"}
    ]

# Display chat messages from history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# React to user input
if prompt := st.chat_input("E.g., I need ₹15,000 for a phone next May"):
    # 1. Display user message in chat message container
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 2. Process with AI
    with st.spinner("Calculating the best path to your goal..."):
        extracted_data = extract_goal_data(prompt)
        
        if "error" in extracted_data:
            bot_reply = extracted_data["error"]
        elif extracted_data.get("amount") == 0:
            bot_reply = f"I'd love to help you save for your {extracted_data['goal']}! Roughly how much do you think it will cost?"
        else:
            target = extracted_data["amount"]
            months = extracted_data["months"]
            goal_name = extracted_data["goal"]
            
            # Calculate the math
            sip = calculate_sip(target, months, ANNUAL_RETURN_RATE)
            
            # Formulate the conversational response
            bot_reply = f"Awesome! A **{goal_name}** sounds great. \n\nTo hit your goal of **₹{target:,}** in **{months} months**, you just need to save **₹{sip:,} per month**. \n\nI'll place this in a secure Liquid Fund earning ~6.5% so it grows safely. You can withdraw it to your bank anytime in 24 hours. \n\n**Should I set up this automated savings plan for you?**"

    # 3. Display assistant response in chat message container
    with st.chat_message("assistant"):
        st.markdown(bot_reply)
        if "error" not in extracted_data and extracted_data.get("amount", 0) > 0:
            st.button("✅ Yes, Start Saving")
            
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": bot_reply})