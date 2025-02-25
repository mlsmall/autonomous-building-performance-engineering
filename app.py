from dotenv import load_dotenv
load_dotenv()

import os, base64, subprocess

print("Starting git-crypt unlock process...")
git_crypt_key = os.getenv("GIT_CRYPT_KEY")
print(f"Key type: {type(git_crypt_key)}")
print(f"Key value: {git_crypt_key}")

# Stash any changes before unlock
subprocess.run(["git", "stash"], check=True)

print("Decoding git-crypt key...")
key = base64.b64decode(git_crypt_key)
with open("temp.key", "wb") as f:
    f.write(key)

subprocess.run(["./bin/git-crypt", "unlock", "temp.key"], check=True)
os.remove("temp.key")
import streamlit as st
from graph import graph, USE_DATABASE, get_user_history
from report_generator import generate_performance_report
import json

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
    st.markdown("<div style='margin: 0.5rem 0 0 0;'><hr style='margin: 8px 0;'></div>", unsafe_allow_html=True)
    st.markdown("<p style='margin: 0.5rem 0 0.5rem 0; font-size: 0.9em;'>Made with ❤️ by Kalevi Productions</p>", unsafe_allow_html=True)
    st.markdown("<div style='margin: 0 0 0.5rem 0;'><hr style='margin: 8px 0;'></div>", unsafe_allow_html=True)
    
    # Negative margin brings expander closer
    st.markdown("<div style='margin-top: -0.5rem;'>", unsafe_allow_html=True)
    with st.expander("📐 Calculation Methodology"):
        st.markdown("""
        **Standards Referenced:**
        - ASHRAE 90.1 Energy Standard for Buildings
        - ASHRAE Fundamentals Handbook
        - International Energy Conservation Code (IECC)
        
        **Data Sources:**
        - NASA Surface Solar Radiation Database (SSE)
        - ASHRAE Climate Design Data
        - Local Utility Rate Structures
        """)
    
    # Disclaimer
    with st.expander("ℹ️ Disclaimer"):
        st.markdown("<div style='font-size: 0.85em; color: #6c757d;'>This building performance assistant performs comprehensive engineering calculations but should not be used for compliance verification or detailed engineering specifications.</div>", unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)

# # In app.py sidebar
# with st.sidebar:
#     st.markdown("---")
#     with st.expander("📐 Calculation Methodology"):
#         st.markdown("""
#         **Standards Referenced:**
#         - ASHRAE 90.1 Building Energy Standard
#         - ASHRAE Fundamentals Handbook
#         - International Energy Conservation Code (IECC)
        
#         **Data Sources:**
#         - NASA Surface Solar Radiation Database (SSE)
#         - ASHRAE Climate Design Data
#         - Local Utility Rate Structures
#         """)
    
    

with st.sidebar:
    if USE_DATABASE and st.session_state.user_id:
        st.markdown("---")
        with st.expander("📊 Previous Analyses"):
            # Get user's history from MongoDB
            user_history = get_user_history(st.session_state.user_id)
            if user_history:
                for calc in user_history:
                    if 'timestamp' in calc:
                        st.markdown(f"""
                            **{calc['timestamp'].strftime('%Y-%m-%d %H:%M')}**
                            - Area: {calc['window_area']:,.0f} ft²
                            - SHGC: {calc['shgc']}
                            - Location: {calc['city']}
                            """)
                        if st.button(f"Load Analysis", key=f"load_{calc['timestamp']}"):
                            # Populate current session with this data
                            for key in ['window_area', 'shgc', 'u_value', 'city']:
                                if key in calc:
                                    st.session_state[key] = calc[key]
                            st.rerun()


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
                    print("FULL STATE:", state)
                    st.write(state)
                    
                    # Store input validation values
                    if 'input_validation' in state:
                        st.session_state.last_state = {
                            'city': state['input_validation'].get('city'),
                            'window_area': state['input_validation'].get('window_area'),
                            'shgc': state['input_validation'].get('shgc'),
                            'u_value': state['input_validation'].get('u_value')
                        }
                    
                    # Store ASHRAE values
                    if 'ashrae_lookup' in state:
                        st.session_state.last_state.update({
                            'ashrae_climate_zone': state['ashrae_lookup'].get('ashrae_climate_zone'),
                            'ashrae_shgc': state['ashrae_lookup'].get('ashrae_shgc'),
                            'ashrae_u_factor': state['ashrae_lookup'].get('ashrae_u_factor')
                        })
                    
                    # Store calculation values
                    if 'calculation' in state:
                        if 'proposed_heat_gain' in state['calculation']:
                            st.session_state.last_state.update({
                                'proposed_heat_gain': state['calculation'].get('proposed_heat_gain'),
                                'proposed_cooling_energy': state['calculation'].get('proposed_cooling_energy'),
                                'proposed_cost': state['calculation'].get('proposed_cost')
                            })
                        if 'baseline_heat_gain' in state['calculation']:
                            st.session_state.last_state.update({
                                'baseline_heat_gain': state['calculation'].get('baseline_heat_gain'),
                                'baseline_cooling_energy': state['calculation'].get('baseline_cooling_energy'),
                                'baseline_cost': state['calculation'].get('baseline_cost')
                            })
                    
                    if 'recommendation' in state:
                        try:
                            recs = json.loads(state['recommendation']['messages'][0].content)
                            recommendations = "\n".join(recs['recommendations'])
                            st.session_state.messages.append({"role": "assistant", "content": recommendations})
                            st.rerun()
                        except Exception as e:
                            print(f"Failed to process recommendations: {e}")

        # After the chat message block but before st.rerun():

    if 'last_state' in st.session_state:  # Only shows button after calculations
        st.markdown("""
            <style>
            div[data-testid="stButton"] button {
                background-color: #1a237e;
                color: white;
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: 500;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                border: none;
            }
            div[data-testid="stButton"] button:hover {
                color: #e8eaf6 !important; 
                background-color: #1a237e !important;  # Keep same background on click
            }
            </style>
        """, unsafe_allow_html=True)
        
        if st.button("Generate Report", key="generate_report"):
            with st.spinner("Generating report..."):  
                try:
                    pdf_data = generate_performance_report(st.session_state.last_state)
                    st.download_button(
                        "Download PDF",
                        pdf_data,
                        "BPA_Analysis_Report.pdf",
                        "application/pdf"
                    )
                except Exception as e:
                    st.error(f"Error generating PDF: {str(e)}")   

    