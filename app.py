from dotenv import load_dotenv
load_dotenv()

import streamlit as st
from cryptography.fernet import Fernet
from pathlib import Path

key = st.secrets["DECRYPT_KEY"].encode()
cipher = Fernet(key)


# First collect all decrypted content
decrypted_files = {}
for file in Path('core_engine').glob('*.py'):
    with open(file, 'rb') as f:
        content = f.read()
    # Check if content looks encrypted (starts with 'gAAAAA')
    if content.startswith(b'gAAAAA'):
        decrypted = cipher.decrypt(content).decode()
    else:
        decrypted = content.decode()
        
    first_line = decrypted.split('\n')[0]
    print(f"First line: {first_line}")
    decrypted_files[file] = decrypted

for file, content in decrypted_files.items():
    with open(file, 'w') as f:
        f.write(content)

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
    st.markdown("Enter each building details in this form:")
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


# Initialize session states
if 'building_data' not in st.session_state:
    st.session_state.building_data = {
        'window_area': None,
        'shgc': None,
        'u_value': None,
        'city': None
    }
    st.session_state.current_input = 'window_area'

# Initialize messages with welcome
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

    st.session_state.messages.append({
        "role": "assistant",
        "content": """<div style='font-weight: 500;'>Enter the building total window area (ft²) in the input box below. &nbsp; <span style='color: #1a237e; font-size: 1.4em;'>↓</span></div>"""
    })

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["role"] == "assistant" and "%" in message["content"]:
            formatted_content = message["content"].replace("* ", "\n* ").replace("\n", "\n\n")
        else:
            formatted_content = message["content"]
        st.markdown(formatted_content, unsafe_allow_html=True)  # Always use unsafe_allow_html

# Handle chat input
if prompt := st.chat_input("Enter value:"):
    # Show user input
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Handle each input type
    if st.session_state.current_input == 'window_area':
        try:
            area = float(prompt)
            if area > 0:
                st.session_state.building_data['window_area'] = area
                st.session_state.current_input = 'shgc'
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": "Enter the SHGC for the glass (0-1):"
                })
            else:
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "Window area must be greater than 0. Try again:"
                })
        except ValueError:
            st.session_state.messages.append({
                "role": "assistant",
                "content": "Please enter a valid number for window area:"
            })
    
    elif st.session_state.current_input == 'shgc':
        try:
            shgc = float(prompt)
            if 0 <= shgc <= 1:
                st.session_state.building_data['shgc'] = shgc
                st.session_state.current_input = 'u_value'
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "Enter the U-value for the window:"
                })
            else:
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "SHGC must be between 0 and 1. Try again:"
                })
        except ValueError:
            st.session_state.messages.append({
                "role": "assistant",
                "content": "Please enter a valid SHGC value:"
            })
    
    elif st.session_state.current_input == 'u_value':
        try:
            u_value = float(prompt)
            if  0 <= u_value <= 10:
                st.session_state.building_data['u_value'] = u_value
                st.session_state.current_input = 'city'
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "Enter the name of your city:"
                })
            else:
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "U-value must be between 0 and 10. Try again:"
                })
        except ValueError:
            st.session_state.messages.append({
                "role": "assistant",
                "content": "Please enter a valid U-value:"
            })
    
    
    elif st.session_state.current_input == 'city':
        if prompt.strip():
            formatted_input = (
                f"window area = {int(st.session_state.building_data['window_area'])} ft2 "
                f"shgc = {st.session_state.building_data['shgc']} "
                f"u-value = {st.session_state.building_data['u_value']} "
                f"city = {prompt.strip()}"
            )

            # Process with graph
            with st.chat_message("assistant"):
                with st.spinner("Calculating building performance..."):
                    print("DEBUG - formatted_input being sent:", formatted_input)
                    for state in graph.stream({
                        "messages": [("user", formatted_input)],
                        "next": "",
                        "user_id": st.session_state.user_id,
                        "existing_data": None
                    }, config={"configurable": {"thread_id": "1"}}):
                        st.write(state)
                        
                        if 'input_validation' in state:
                            print("STATE CONTENT:", state['input_validation']['messages'][0].content)
                            if "Valid input" in state['input_validation']['messages'][0].content:
                                # If valid, update state and show formatted list
                                st.session_state.building_data['city'] = prompt.strip()
                                
                                inputs = formatted_input.split()
                                formatted_list = "Your Proposed Building Inputs:\n\n"

                                i = 0
                                while i < len(inputs):
                                    if inputs[i] in ['area', 'shgc', 'u-value', 'city']:
                                        value = inputs[i+2] 
                                        unit = ' ft2' if inputs[i] == 'area' else ''  
                                        formatted_list += f"* {inputs[i]} = {value}{unit}\n"
                                    i += 1

                                st.session_state.messages.append({
                                    "role": "assistant",
                                    "content": f"```\n{formatted_list}\n```"
                                })
                                
                                # Store input validation values
                                st.session_state.last_state = {
                                    'city': state['input_validation'].get('city'),
                                    'window_area': state['input_validation'].get('window_area'),
                                    'shgc': state['input_validation'].get('shgc'),
                                    'u_value': state['input_validation'].get('u_value')
                                }
                            else:
                                # Handle invalid city
                                if state['input_validation'].get('next') == '__start__':
                                    st.session_state.building_data = {
                                        'window_area': st.session_state.building_data['window_area'],
                                        'shgc': st.session_state.building_data['shgc'],
                                        'u_value': st.session_state.building_data['u_value'],
                                        'city': None
                                    }
                                    st.session_state.current_input = 'city'
                                    st.session_state.messages.append({
                                        "role": "assistant",
                                        "content": state['input_validation']['messages'][0].content
                                    })
                                    st.rerun()
                                    break
                                
                        # Store ASHRAE values if validation passed
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
                        
                        # Handle recommendations
                        if 'recommendation' in state:
                            try:
                                recs = json.loads(state['recommendation']['messages'][0].content)
                                recommendations = "\n".join(recs['recommendations'])
                                st.session_state.messages.append({"role": "assistant", "content": recommendations})
                                st.rerun()
                            except Exception as e:
                                print(f"Failed to process recommendations: {e}")
                                                            
            # Reset for next input session
            st.session_state.building_data = {
                'window_area': None,
                'shgc': None,
                'u_value': None,
                'city': None
            }
            st.session_state.current_input = 'window_area'
            
            # Add prompt for next session
            st.session_state.messages.append({
                "role": "assistant",
                "content": "Enter your window area (ft²) for a new analysis:"
            })
        else:
            st.session_state.messages.append({
                "role": "assistant",
                "content": "Please enter a valid city name:"
            })
 
    st.rerun()

if 'last_state' in st.session_state: 
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
