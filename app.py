"""
Streamlit interface for Building Performance Assistant (BPA).
Handles UI, user input collection, and integration with multi-agent system.
"""
import json
import uuid
from dotenv import load_dotenv
load_dotenv()

import streamlit as st


# # Decrypt and load core engine files
# from cryptography.fernet import Fernet
# from pathlib import Path
# key = st.secrets["DECRYPT_KEY"].encode()
# cipher = Fernet(key)

# # Collect all encrypted content
# decrypted_files = {}
# for file in Path('core_engine').glob('*.py'):
#     with open(file, 'rb') as f:
#         content = f.read()
#     # Check if content looks encrypted (starts with 'gAAAAA')
#     if content.startswith(b'gAAAAA'):
#         decrypted = cipher.decrypt(content).decode()
#     else:
#         decrypted = content.decode()
        
#     first_line = decrypted.split('\n')[0]
#     # print(f"First line: {first_line}")
#     decrypted_files[file] = decrypted

# for file, content in decrypted_files.items():
#     with open(file, 'w') as f:
#         f.write(content)


from graph import graph, USE_DATABASE, get_user_history
from report_generator import generate_performance_report


def format_recommendation(data: dict) -> str:
    """Convert raw data to styled HTML without leading whitespace"""
    # Extract metrics from recommendations list (first 3 items)
    heat_gain_line = data["recommendations"][0]
    energy_line = data["recommendations"][1] 
    cost_line = data["recommendations"][2]
    
    # Parse numerical values from recommendation strings
    heat_gain_diff = float(heat_gain_line.split(":")[1].split()[0])
    energy_diff = float(energy_line.split(":")[1].split()[0])
    cost_diff = float(cost_line.split(":")[1].split()[0])
    
    return (
        '<div style="font-family:\'Inter\',sans-serif;border-left:3px solid #1a237e;padding:1rem;margin:1rem 0;background:#faffff;">'
        '<div style="color:#1a237e;font-weight:600;font-size:1.1em;margin-bottom:1rem;">PERFORMANCE ANALYSIS</div>'
        f'<div style="margin:0.5rem 0;"><span style="display:inline-block;width:140px;">Peak Heat Gain</span>'
        f'<span style="color:{"#43a047" if heat_gain_diff < 0 else "#d32f2f"};">'
        f'{"✓" if heat_gain_diff < 0 else "↓"}</span> '
        f'&nbsp; The peak energy use is {abs(heat_gain_diff):,.0f} {"less" if heat_gain_diff < 0 else "more"} BTU/hr</div>'
        f'<div style="margin:0.5rem 0;"><span style="display:inline-block;width:140px;">Energy Usage</span>'
        f'<span style="color:{"#43a047" if energy_diff < 0 else "#d32f2f"};">'
        f'{"✓" if energy_diff < 0 else "↓"}</span> '
        f'&nbsp; The building uses {abs(energy_diff):,.0f} {"less" if energy_diff < 0 else "more"} kWh/year</div>'
        f'<div style="margin:0.5rem 0;"><span style="display:inline-block;width:140px;">Cooling Costs</span>'
        f'<span style="color:{"#43a047" if cost_diff < 0 else "#d32f2f"};">'
        f'{"✓" if cost_diff < 0 else "↓"}</span> '
        f'&nbsp;The yearly energy costs are ${abs(cost_diff):,.2f} {"less" if cost_diff < 0 else "more"}</div>'
        '<div style="margin-top:1rem;padding-top:0.5rem;border-top:1px solid #eee;">'
        f'The proposed building is <span style="color:{"#43a047" if data["performance_delta"] < 0 else "#d32f2f"};">'
        f'{abs(data["performance_delta"]):.1f}% {"better" if data["performance_delta"] < 0 else "worse"} </span> than the Baseline building.'
        '</div>'
        '</div>'
    )

# UI Configuration
st.set_page_config(
    layout="wide", 
    page_title="Building Performance Assistant",
    page_icon="🏢"
)

# Set up custom UI styles and fonts -> f0f7ff light blue chat background
st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
    <style>
    /* Main container styling */
    .main {
        background-color: #f8f9fa;
        padding: 2rem;
    }
    /* Hide chat avatars */
    [data-testid="stChatMessageAvatarAssistant"],
    [data-testid="stChatMessageAvatarUser"] {
        display: none !important;
    }
    /* User chat message background */
    .stChatMessage.st-emotion-cache-1c7y2kd {
        background-color: #f0f7ff !important;
        width: 82% !important;
        max-width: 82% !important;
    }
    
    /* Raise Input Box */     
    [data-testid="stBottom"] {
        height: 300px !important;
    }
    
    /* Chat input text area height */
    .stChatInput textarea {
        height: 40px !important; 
    }       
    /* Input width adjustments */
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
    [data-testid="stChatInputContainer"] {
        width: 100% !important;
        max-width: 100% !important;
    }
            
    /* Remove input focus outline */
    .st-c5, .st-c4, .st-c3, .st-c2 {
        border-color: transparent !important;
    }
            
    /* Chat input background, border, shadow */
    [data-testid="stChatInput"] {
        background-color: #ffffff !important;
        border: 1px solid #c0c0c0 !important;
        box-shadow: 6px 6px 6px rgba(0,0,0,0.03) !important;
            
    /* Form input styling */
    .input-header {
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        color: #1a237e;
        margin-bottom: -0.5rem;
    }

    div[data-baseweb="input"] {
        margin-bottom: 1.2rem;
    }

    div[data-baseweb="input"] > div {
        border-radius: 8px !important;
        border: 1px solid #c0c0c0 !important;
        padding: 8px 12px !important;
    }

    div[data-baseweb="input"]:has(> div:hover) {
        border-color: #1a237e !important;
    }

    .invalid-input div[data-baseweb="input"] > div {
        border-color: #d32f2f !important;
        background: #fff5f5 !important;
    }

    button[kind="formSubmit"] {
        background: #1a237e !important;
        color: white !important;
        font-weight: 500 !important;
        border: none !important;
        margin-top: 1rem !important;
    }

   
</style>
""", unsafe_allow_html=True)

# Top heading
st.markdown("""
    <div style='margin: -2rem 0 3rem 0'>
        <h2 style='color: #1a237e; font-size: 34px; font-weight: 600; margin: 0; letter-spacing: -1px;'>
            BPA <span style='color: #2c2c2c; font-weight: 500; font-size: 32px;'>| Building Performance Assistant</span>
        </h2>
    </div>
""", unsafe_allow_html=True)

# Sidebar content
with st.sidebar:
    st.title("Energy Analysis")
    st.markdown("---")
    st.markdown("### Quick Guide")
    st.markdown("Enter each building detail.\nTry these sample values:")
    st.code("window area = 10000 ft2\nshgc = 0.40\nu-value = 0.9\ncity = Montreal")
    # st.markdown("<div style='margin: 0.5rem 0 0 0;'><hr style='margin: 8px 0;'></div>", unsafe_allow_html=True)
    # st.markdown("<p style='margin: 0.5rem 0 0.5rem 0; font-size: 0.9em;'>Made with ❤️ by Kalevi Productions</p>", unsafe_allow_html=True)
    # st.markdown("<div style='margin: 0 0 0.5rem 0;'><hr style='margin: 8px 0;'></div>", unsafe_allow_html=True)
    st.markdown("<div style='margin-top: -0.5rem;'>", unsafe_allow_html=True)
    
    # Methodology expander
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
    
    # Disclaimer expander
    with st.expander("ℹ️ Disclaimer"):
        st.markdown("<div style='font-size: 0.85em; color: #6c757d;'>This building performance assistant performs comprehensive engineering calculations but should not be used for compliance verification or detailed engineering specifications.</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # If database usage is enabled and a user session is present
    if USE_DATABASE and st.session_state.user_id:
        st.markdown("---")
        with st.expander("📊 Previous Analyses"):
            # Retrieve prior user building data from the database
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
                        # Load that historical analysis data if user clicks
                        if st.button(f"Load Analysis", key=f"load_{calc['timestamp']}"):
                            for key in ['window_area', 'shgc', 'u_value', 'city']:
                                if key in calc:
                                    st.session_state[key] = calc[key]
                            st.rerun()

# Initialize building data in session_state
if 'building_data' not in st.session_state:
    st.session_state.building_data = {
        'window_area': None,
        'shgc': None,
        'u_value': None,
        'city': None
    }
    st.session_state.current_input = 'window_area'

# Initialize messages with a welcome message and track conversation state
if 'messages' not in st.session_state:
    st.session_state.messages = []
    # For example, use a test user if no database is in use.
    st.session_state.user_id = None if USE_DATABASE else "test_user"
    
    premium_intro = """
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
        <div style="
            max-width: 600px;
            background: #FFFFFF;
            padding: 1rem 1rem;  
            font-family: 'Inter', sans-serif;
            border-radius: 8px;
            margin: 0 0 2rem 0;
            box-shadow: 0 4px 20px rgba(26, 35, 126, 0.06);
            border: 1px solid rgba(26, 35, 126, 0.05);
            border-left: 3px solid #1a237e; 
            ">
            <p style="
                color: #1a237e;
                font-size: 1.28rem;
                font-weight: 500;
                margin: 0 0 1.4rem 0;
                letter-spacing: -0.4px;
                padding-left: 0.3rem; 
            ">
                Energy Performance & Cost Modeling
            </p>
            <p style="
                font-size: 0.93rem;
                color: #444;
                margin: 0;
                line-height: 1.7;
                padding-left: 0.3rem; 
            ">
                ▸ Compare your building against industry benchmarks, energy use, and costs.<br>  
                ▸ Enter your building details below. <span style='color: #1a237e; font-size: 1.1em;'>↓</span></div>
            </p>
        </div>
        """
    st.session_state.messages.append({
        "role": "assistant", 
        "content": premium_intro
    })

# Displays the chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"], unsafe_allow_html=True)

# Initialize form visibility
if 'show_form' not in st.session_state:
    st.session_state.show_form = True

# Chat input box 
# Three columns with the form in the first column (left side). The other two are empty.
#cols = st.columns(3)
col1, col2, col3 = st.columns([0.03, .5, 1]) 
if st.session_state.show_form:
    with col2:
        with st.form("building_form"):
            st.markdown("""
            <style>
                /* Remove number input spin buttons */
                div[data-testid="stNumberInput"] button {
                    display: none !important;
                }
                   
                /* Remove 'Press enter to submit' text */
                div[data-testid="InputInstructions"] {
                    display: none !important;
                }   
            </style>
            """, unsafe_allow_html=True)
                    
            st.markdown("""<h4 style='color: #1a237e;'>Building Details</h4>""", unsafe_allow_html=True)
            window_area = st.number_input("Window Area (ft²)", min_value=1, step=1, value=None, help="Total glazing area of the building envelope")
            shgc = st.number_input("Solar Heat Gain Coefficient (0-1)", min_value=0.0, max_value=1.0, step=0.01, value=None, help="Fraction of solar radiation admitted")
            u_value = st.number_input("U-Value (0-10)", min_value=0.0, max_value=10.0, step=0.1, value=None, help="Overall heat transfer coefficient of the window")
            wall_area = st.number_input("Wall Area (ft²)", min_value=1, step=1, value=None, help="Total wall area of the building envelope")
            wall_u_value = st.number_input("Wall U-Value (0-10)", min_value=0.0, max_value=10.0, step=0.1, value=None, help="Overall heat transfer coefficient of the wall")
            city = st.text_input("City", value=None, help="Used to determine your climate zone and local energy requirements")
            submit_button = st.form_submit_button("Submit")

        if submit_button:     
            # st.session_state.building_data = {'window_area': window_area, 'shgc': shgc, 'u_value': u_value, 'city': city.strip()}
            st.session_state.building_data['window_area'] = window_area
            st.session_state.building_data['shgc'] = shgc
            st.session_state.building_data['u_value'] = u_value
            st.session_state.building_data['wall_area'] = wall_area
            st.session_state.building_data['wall_u_value'] = wall_u_value
            st.session_state.building_data['city'] = city
        

            # Format the input for graph processing
            formatted_input = (
                f"window area = {int(st.session_state.building_data['window_area'])} ft2 "
                f"shgc = {st.session_state.building_data['shgc']} "
                f"u-value = {st.session_state.building_data['u_value']} "
                f"wall area = {int(st.session_state.building_data['wall_area'])} ft2 "
                f"city = {st.session_state.building_data['city']} "
+               f"wall u-value = {st.session_state.building_data['wall_u_value']} "
            )

            with st.chat_message("assistant"):
            # Process the input via the multi-agent graph stream.
                with st.spinner("Calculating building performance..."):
                    for state in graph.stream({
                        "messages": [("user", formatted_input)],
                        "next": "",
                        "user_id": st.session_state.user_id,
                        "existing_data": None
                    }, config={"configurable": {"thread_id": str(uuid.uuid4())}}):
                        st.write(state)

                        # Validate input
                        if 'input_validation' in state:
                            if "Valid input" in state['input_validation']['messages'][0].content:
                                st.session_state.building_data['city'] = city
                                
                                # Display building inputs in formatted box
                                formatted_list = """
                                <div style='background-color: #faffff; padding: 1.1rem; border-radius: 8px; border-left: 2.5px solid #1a237e; margin: 1rem 0; width: 52%; max-width: 52%;'>
                                    <div style='font-size: 1.1em; font-weight: 500; color: #1a237e; margin-bottom: 0.8rem;'>
                                        Your Proposed Building Inputs
                                    </div>
                                    <div style='font-family: "Inter", sans-serif; font-size: 0.9em;'>
                                        • Glass area = <span style='font-weight: normal'>{} ft²</span><br>
                                        • SHGC = <span style='font-weight: normal'>{}</span><br>
                                        • U-value = <span style='font-weight: normal'>{}</span><br>
                                        • Wall area = <span style='font-weight: normal'>{} ft²</span><br>
                                        • City = <span style='font-weight: normal'>{}</span>
+                                       • Wall U-value = <span style='font-weight: normal'>{}</span>
                                    </div>
                                </div>
                                """.format(
                                    f"{int(st.session_state.building_data['window_area']):,}",
                                    st.session_state.building_data['shgc'],
                                    st.session_state.building_data['u_value'],
                                    st.session_state.building_data['city'],
                                    st.session_state.building_data['wall_area'],
+                                   st.session_state.building_data['wall_u_value']
                                )

                                # Then modify how you append it to messages:
                                st.session_state.messages.append({
                                    "role": "assistant",
                                    "content": formatted_list
                                })
                                
                                # Store validated data in last_state for final reporting
                                st.session_state.last_state = {
                                    'city': state['input_validation'].get('city'),
                                    'window_area': state['input_validation'].get('window_area'),
                                    'shgc': state['input_validation'].get('shgc'),
                                    'u_value': state['input_validation'].get('u_value')
                                }
                            else:
                                # Handle invalid city
                                st.session_state.building_data['city'] = None
                                st.session_state.current_input = 'city'
                                st.session_state.messages.append({
                                    "role": "assistant",
                                    "content": state['input_validation']['messages'][0].content
                                })
                                st.rerun()

                        # Collect ASHRAE lookup data if present
                        if 'ashrae_lookup' in state:
                            st.session_state.last_state.update({
                                'ashrae_climate_zone': state['ashrae_lookup'].get('ashrae_climate_zone'),
                                'ashrae_shgc': state['ashrae_lookup'].get('ashrae_shgc'),
                                'ashrae_u_factor': state['ashrae_lookup'].get('ashrae_u_factor')
                            })

                        # Store calculation results for report generation
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

                        # Handle agent recommendations and update UI
                        if 'recommendation' in state:
                            try:
                                rec_data = json.loads(state['recommendation']['messages'][0].content)
                                styled_html = format_recommendation(rec_data)
                                st.session_state.messages.append({
                                    "role": "assistant", 
                                    "content": styled_html
                                }) 
                                st.session_state.show_form = False # Hide form after recommendation
                                
                                st.rerun()
                                
                            except Exception as e:
                                st.error(f"Error formatting recommendation: {str(e)}")
                # # Reset state data for the new analysis
                # st.session_state.building_data = {
                #     'window_area': None,
                #     'shgc': None,
                #     'u_value': None,
                #     'city': None
                # }
                # st.session_state.current_input = 'window_area'
                # st.session_state.messages.append({
                #     "role": "assistant",
                #     "content": "Enter your window area (ft²) for a new analysis:"
                # })


# If the last_state with validated values is present, show button for generating final PDF report
# =============================================================================
# FINAL ELEMENT IN SCRIPT
# =============================================================================
if 'last_state' in st.session_state:  # Custom styling for report download button
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
            background-color: #1a237e !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # Generate performance report (PDF)
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
