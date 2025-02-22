import streamlit as st
from streamlit_extras.stylable_container import stylable_container
from graph import graph, USE_DATABASE
import json

import pandas as pd
from fpdf import FPDF
from io import BytesIO
import datetime

# Rest of the code remains the same, and remove the USE_DATABASE = False line since we're importing it
# Premium look settings
st.set_page_config(
    layout="wide", 
    page_title="Building Performance Assistant",
    page_icon="🏢"
)

st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
    <style>
    /* Clean background */
    .main {
        background-color: #f8f9fa;
        padding: 2rem;
    }
    
    /* Hide avatars */
    [data-testid="stChatMessageAvatarAssistant"],
    [data-testid="stChatMessageAvatarUser"] {
        display: none !important;
    }
            
    /* User message background */
    .stChatMessage.st-emotion-cache-1c7y2kd {
        background-color: #f0f7ff !important;
        width: 82% !important;
        max-width: 82% !important;
    }
            
    /* Chat input styling */
    .stChatInput textarea {
        height: 40px !important; 
    }       

    /* Input width */
    [data-baseweb="base-input"],
    .st-ae {
        width: 100% !important;
        max-width: 100% !important;
    }

    .stElementContainer,
    .stChatInput {
        width: 80% !important;
        max-width: 80% !important;
    }

    /* You might also need to adjust the parent container */
    [data-testid="stChatInputContainer"] {
        width: 100% !important;
        max-width: 100% !important;
    }
    
    /* Remove input focus outline */
    .st-c5, .st-c4, .st-c3, .st-c2 {
        border-color: transparent !important;
    }
            
    /* Input background */
    [data-testid="stChatInput"] {
        background-color: #ffffff !important;
        border: 1px solid #c0c0c0 !important;
        box-shadow: 6px 6px 6px rgba(0,0,0,0.03) !important;
    }

    /* Lower Input Box      
    [data-testid="stBottom"] {
        height: 80px !important;
    }
    
    .info-icon {
        color: #ff0000 !important;
        font-style: italic !important;
        font-size: 12px !important;
        opacity: 0.7 !important;
        border: 1px solid #ff0000 !important;
        border-radius: 50% !important;
        padding: 0 4px !important;
        margin-left: 4px !important;
        cursor: help !important;
        display: inline-block !important;
    }

</style>
""", unsafe_allow_html=True)

st.markdown("""
    <div style='margin: -4rem 0 4.5rem 0'>
        <h2 style='color: #1a237e; font-size: 34px; font-weight: 600; margin: 0;'>
            BPA <span style='color: #2c2c2c; font-weight: 500; font-size: 32px;'>| Building Performance Assistant</span>
        </h2>
    </div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("Energy Analysis")
    st.markdown("---")
    st.markdown("### Quick Guide")
    st.markdown("Enter each building detail followed by a space in this form:")
    st.code("window area = 10000 ft2\nshgc = 0.40\nu-value = 0.9\ncity = Montreal")
    st.markdown("---")
    st.markdown("Made with ❤️ by Kalevi Productions")

# Initialize session state for chat
# if 'messages' not in st.session_state:
#     st.session_state.messages = []
#     st.session_state.user_id = None if USE_DATABASE else "test_user"
#     # Add initial message
#     st.session_state.messages.append({
#         "role": "assistant", 
#         "content": """Hello, I'm your building performance engineer assistant. Please enter these inputs:
# * Window area (ft²)
# * SHGC value (0-1)
# * U-value
# * Building location (city)"""
#     })
if 'messages' not in st.session_state:
    st.session_state.messages = []
    st.session_state.user_id = None if USE_DATABASE else "test_user"
    st.session_state.messages.append({
        "role": "assistant", 
        "content": """Hello, I'm your building performance engineer assistant. Please enter these inputs:
* Window area (ft²) <sup><span style='color: #1a237e; font-size: 10px; font-family: "Times New Roman", serif; opacity: 0.8; border: 1px solid #1a237e; border-radius: 50%; padding: 0 3px; margin-left: 2px; cursor: help;' title="Total glazing area of the building envelope">i</span></sup>
* SHGC value (0-1) <sup><span style='color: #1a237e; font-size: 10px; font-family: "Times New Roman", serif; opacity: 0.8; border: 1px solid #1a237e; border-radius: 50%; padding: 0 3px; margin-left: 2px; cursor: help;' title="Solar Heat Gain Coefficient - The fraction of solar radiation admitted through a window">i</span></sup>
* U-value <sup><span style='color: #1a237e; font-size: 10px; font-family: "Times New Roman", serif; opacity: 0.8; border: 1px solid #1a237e; border-radius: 50%; padding: 0 3px; margin-left: 2px; cursor: help;' title="Overall heat transfer coefficient - Measures how well a window conducts heat">i</span></sup>
* Building location (city) <sup><span style='color: #1a237e; font-size: 10px; font-family: "Times New Roman", serif; opacity: 0.8; border: 1px solid #1a237e; border-radius: 50%; padding: 0 3px; margin-left: 2px; cursor: help;' title="Used to determine climate zone and local energy requirements">i</span></sup>"""
    })
# Main content
#st.title("BPA | Building Performance Assistant")

# User ID Input (only if using database)
if USE_DATABASE and not st.session_state.user_id:
    user_id = st.text_input("Please enter your email as user ID:")
    if st.button("Start Analysis"):
        st.session_state.user_id = user_id
        st.rerun()

if st.session_state.user_id:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant" and "%" in message["content"]:
                formatted_content = message["content"].replace("* ", "\n* ").replace("\n", "\n\n")
            else:
                formatted_content = message["content"]
            st.markdown(formatted_content, unsafe_allow_html=True)

    # Chat input
    if prompt := st.chat_input("Enter your building details:"):
        st.session_state.messages.append({"role": "user", "content": prompt}) # Add user message to chat

        with st.chat_message("assistant"):
            with st.spinner("Calculating building performance..."):

                for state in graph.stream({
                    "messages": [("user", prompt)],
                    "next": "",
                    "user_id": st.session_state.user_id,
                    "existing_data": None
                }, config={"configurable": {"thread_id": "1"}}):
                    st.write(state)
                    
                    if 'recommendation' in state:
                        try:
                            recs = json.loads(state['recommendation']['messages'][0].content)
                            recommendations = "\n".join(recs['recommendations'])
                            st.session_state.messages.append({"role": "assistant", "content": recommendations})
                        except Exception as e:
                            print(f"Failed to process recommendations: {e}")          
                    
        st.rerun()