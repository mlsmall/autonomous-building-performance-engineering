"""
Streamlit interface for Building Performance Assistant (BPA).
Handles UI, user input collection, and integration with multi-agent system.
"""
import json
import uuid
from dotenv import load_dotenv
load_dotenv()

import streamlit as st
from streamlit.components.v1 import html

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
        '<div style="font-family:\'Inter\',sans-serif;max-width: 600px;border-radius: 8px;box-shadow: 0 4px 20px rgba(26, 35, 126, 0.06);border-left:2.0px solid #1a237e;padding:1rem;margin:1rem 0;background:#ffffff;">'
        '<div style="color:#1a237e;font-weight:600;font-size:1.1em;margin-bottom:1.1rem;">PERFORMANCE ANALYSIS</div>'
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
        f'The Proposed building is <span style="color:{"#43a047" if data["performance_delta"] < 0 else "#d32f2f"};">'
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
        margin-top: 2.0rem !important;
        background-color: #DDEAF5 !important;
        width: 72% !important;
        max-width: 72% !important;
        border-radius: 8px;
        box-shadow: 0 4px 20px rgba(26, 35, 126, 0.06);
    }
             
    /* Raise Input Box */     
    [data-testid="stBottom"] {
        height: 100px !important;
    }
    
     /* Chat input text area height */
    .stChatInput textarea {
        height: 40px !important; 
    }  
            
    /* Chat Input text area width */
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
        
    /* Remove auto-scroll iframe whitespace */
    .stIFrame, [data-testid="stIFrame"] {
        height: 20px !important;
        border: none !important;
    }
            
    /* Chat message text size */
    [data-testid="stChatMessageContent"] p,
    [data-testid="stChatMessageContent"] li {
        font-size: 1.08rem;
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
        st.markdown(
            "<div style='font-size: 0.85em; color: #6c757d;'>This building performance assistant performs comprehensive engineering calculations but should not be used for compliance verification or detailed engineering specifications.</div>",
            unsafe_allow_html=True)
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

# Initialize thread ID at session start
if 'thread_id' not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())  # Single thread per session

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
    # Use a test user if no database is in use.
    st.session_state.user_id = None if USE_DATABASE else "test_user"
    
    premium_intro = """
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
        <div style="
            max-width: 650px;
            background: #FFFFFF;
            padding: 1rem 1rem;  
            font-family: 'Inter', sans-serif;
            border-radius: 8px;
            margin: 0 0 0 0;
            box-shadow: 0 4px 20px rgba(26, 35, 126, 0.06);
            border: 1px solid rgba(26, 35, 126, 0.05);
            border-left: 2.0px solid #1a237e; 
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
                font-size: 1rem;
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

if 'show_chat' not in st.session_state:
    st.session_state.show_chat = False

# Chat input form 
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
            
    /* Remove number input clear X */
    svg[data-baseweb="icon"][title="Clear value"] {
        display: none !important;
    }
    
    /* Move the form border left */
    div[data-testid="stForm"] {
        margin-right: 100px !important;  /* Pulls right side left */ 
        padding: 1rem 0 0.75rem 2rem !important; 
        border-radius: 8px;
        margin-top: -20px !important;
        margin-left: 17px !important;
        box-shadow: 0 4px 20px rgba(26, 35, 126, 0.06);
        border: 1px solid rgba(26, 35, 126, 0.05);
        border-left: 2.0px solid #1a237e; 
    }
                
    /* Input box text - on focus */
    div[data-baseweb="input"]:focus-within {
        border-color: #1a237e !important;
        box-shadow: 0 0 0 1px #1a237e !important;
    }
            
    /* Input box numbers - on focus  */
    div[data-testid="stNumberInputContainer"]:focus-within {
        border-color: #1a237e !important;
        box-shadow: 0 0 0 1px #1a237e !important;
    }

    /* Submit button - on hover */
    button[data-testid="stBaseButton-secondaryFormSubmit"]:hover {
        border-color: #1a237e !important;
    }
    
    /* Submit text - on hover */
    button[data-testid="stBaseButton-secondaryFormSubmit"]:hover div[data-testid="stMarkdownContainer"] {
        color: #1a237e !important;
    }


</style>
""", unsafe_allow_html=True)

if st.session_state.show_form:
    with st.form("building_form"):
        st.markdown("""<h4 style='color: #1a237e;'>Building Details</h4>""", unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)  
        with col1:
            window_area = st.number_input("Window Area (ft²)", min_value=1, step=1, value=None, help="Total glazing area of the building envelope")
            shgc = st.number_input("Solar Heat Gain Coefficient (0-1)", min_value=0.0, max_value=1.0, step=0.01, value=None, help="Fraction of solar radiation admitted")

        with col2:
            glass_u_value = st.number_input("Window U-Value (0-10)", min_value=0.0, max_value=10.0, step=0.1, value=None, help="Overall heat transfer coefficient of the window")
            wall_area = st.number_input("Wall Area (ft²)", min_value=1, step=1, value=None, help="Total wall area of the building envelope")

        with col3:
            wall_u_value = st.number_input("Wall U-Value (0-10)", min_value=0.0, max_value=10.0, step=0.1, value=None, help="Overall heat transfer coefficient of the wall")
            city = st.text_input("City", value=None, help="Used to determine your climate zone and local energy requirements")

        # Centered submit button
        st.markdown("<div style='margin-top: 20px;'>", unsafe_allow_html=True)
        submit_button = st.form_submit_button("Submit")
        st.markdown("</div>", unsafe_allow_html=True)

        if submit_button:     
            # st.session_state.building_data = {'window_area': window_area, 'shgc': shgc, 'u_value': u_value, 'city': city.strip()}
            st.session_state.building_data['window_area'] = window_area
            st.session_state.building_data['shgc'] = shgc
            st.session_state.building_data['glass_u_value'] = glass_u_value
            st.session_state.building_data['wall_area'] = wall_area
            st.session_state.building_data['wall_u_value'] = wall_u_value
            st.session_state.building_data['city'] = city
        
            # Format the input for graph processing
            formatted_input = (
                f"window area = {int(st.session_state.building_data['window_area'])} ft2 "
                f"shgc = {st.session_state.building_data['shgc']} "
                f"glass u-value = {st.session_state.building_data['glass_u_value']} "
                f"wall area = {int(st.session_state.building_data['wall_area'])} ft2 "
                f"city = {st.session_state.building_data['city']} "
                f"wall u-value = {st.session_state.building_data['wall_u_value']} "
            )

            with st.chat_message("assistant"):
            # Process the input via the multi-agent graph stream.
                with st.spinner("Calculating building performance..."):
                    for state in graph.stream({
                        "messages": [("user", formatted_input)],
                        "next": "",
                        "user_id": st.session_state.user_id,
                        "existing_data": None
                    }, config={"configurable": {"thread_id": st.session_state.thread_id}}):
                        st.write(state)

                        # Validate input
                        if 'input_validation' in state:
                            if "Valid input" in state['input_validation']['messages'][0].content:
                                st.session_state.building_data['city'] = city
                                
                                # Display building inputs in formatted box
                                formatted_list = """
                                <div style='background-color: #ffffff; padding: 1rem; border-radius: 8px; box-shadow: 0 4px 20px rgba(26, 35, 126, 0.06);border-left: 2.0px solid #1a237e; margin: 1rem 0; width: 52%; max-width: 52%;'>
                                    <div style='font-size: 1.1em; font-weight: 500; color: #1a237e; margin-bottom: 0.8rem;'>
                                        Your Proposed Building Inputs
                                    </div>
                                    <div style='font-family: "Inter", sans-serif; font-size: 0.9em;'>
                                        • Glass area = <span style='font-weight: normal'>{} ft²</span><br>
                                        • SHGC = <span style='font-weight: normal'>{}</span><br>
                                        • Glass U-value = <span style='font-weight: normal'>{}</span><br>
                                        • Wall area = <span style='font-weight: normal'>{} ft²</span><br>
                                        • Wall U-value = <span style='font-weight: normal'>{}</span><br>
                                        • City = <span style='font-weight: normal'>{}</span>
                                    </div>
                                </div>
                                """.format(
                                    f"{int(st.session_state.building_data['window_area']):,}",
                                    st.session_state.building_data['shgc'],
                                    st.session_state.building_data['glass_u_value'],
                                    f"{int(st.session_state.building_data['wall_area']):,}",
                                    st.session_state.building_data['wall_u_value'],
                                    st.session_state.building_data['city']
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
                                    'glass_u_value': state['input_validation'].get('glass_u_value'),
                                    'wall_area': state['input_validation'].get('wall_area'),
                                    'wall_u_value': state['input_validation'].get('wall_u_value')
                                }

                            else:
                                # Handle invalid city
                                st.session_state.building_data['city'] = None
                                st.session_state.current_input = 'city'
                                st.session_state.messages.append({
                                    "role": "assistant",
                                    "content": state['input_validation']['messages'][0].content
                                })
                                st.session_state.thread_id = str(uuid.uuid4())  # Reset thread ID for new input
                                st.rerun()

                        # Collect ASHRAE lookup data if present
                        if 'ashrae_lookup' in state:
                            st.session_state.last_state.update({
                                'ashrae_climate_zone': state['ashrae_lookup'].get('ashrae_climate_zone'),
                                'ashrae_shgc': state['ashrae_lookup'].get('ashrae_shgc'),
                                'ashrae_glass_u': state['ashrae_lookup'].get('ashrae_glass_u'),
                                'ashrae_wall_u': state['ashrae_lookup'].get('ashrae_wall_u')
                            })

                        # Store calculation results for report generation
                        if 'calculation' in state:
                            if 'proposed_total_heat_gain' in state['calculation']:
                                st.session_state.last_state.update({
                                    'proposed_total_heat_gain': state['calculation'].get('proposed_total_heat_gain'),
                                    'proposed_cooling_energy': state['calculation'].get('proposed_cooling_energy'),
                                    'proposed_cost': state['calculation'].get('proposed_cost')
                                })
                            if 'baseline_total_heat_gain' in state['calculation']:
                                st.session_state.last_state.update({
                                    'baseline_total_heat_gain': state['calculation'].get('baseline_total_heat_gain'),
                                    'baseline_cooling_energy': state['calculation'].get('baseline_cooling_energy'),
                                    'baseline_cost': state['calculation'].get('baseline_cost')
                                })
                        # Trigger a scroll to bottom of the chat
                        html(
                            """
                            <div id="div" />
                            <script>
                                // Scroll the div into view smoothly
                                var div = document.getElementById('div');
                                div.scrollIntoView({ behavior: 'smooth', block: 'end' });
                            </script>
                            """
                        )
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
                                st.session_state.show_chat = True  # Enable chat interface
                                
                                st.rerun()
                                
                            except Exception as e:
                                st.error(f"Error formatting recommendation: {str(e)}")

# =============================================================================
# If the last_state with validated values is present, show button for generating final PDF report
# But only if we haven't already shown it in the current chat session
if 'last_state' in st.session_state and 'report_generated' not in st.session_state: # Custom styling for report download button
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
                # Mark that we've displayed and processed the report button
                st.session_state.report_generated = True

                pdf_data = generate_performance_report(st.session_state.last_state)
                st.download_button(
                    "Download PDF",
                    pdf_data,
                    "BPA_Analysis_Report.pdf",
                    "application/pdf"
                )     

            except Exception as e:
                st.error(f"Error generating PDF: {str(e)}")



# Chat interface for asking questions after analysis
if not st.session_state.show_form and 'show_chat' in st.session_state and st.session_state.show_chat:
    # Display a text input for questions
    user_question = st.chat_input("You can ask any question about your building's performance...")
    
    if user_question:
        # Add user question to messages
        st.session_state.messages.append({
            "role": "user",
            "content": user_question
        })
        
        # Display the new user message
        with st.chat_message("user"):
            st.markdown(user_question)
        
        # Process through graph with LLM node
        with st.chat_message("assistant"):
            with st.spinner("Analyzing your question..."):
                for state in graph.stream({
                    "messages": [("user", user_question)],
                    "next": "llm",
                    "user_id": st.session_state.user_id,
                    "existing_data": None,
                    # Pass all the relevant building data from session_state
                    **{k: v for k, v in st.session_state.last_state.items() if k not in ["messages", "next"]}
                }, config={"configurable": {"thread_id":  st.session_state.thread_id}}):
                    
                    # Look for LLM response
                    if "llm" in state:
                        llm_response = state["llm"]["messages"][0].content
                        st.write(llm_response)
                        
                        # Save to conversation history
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": llm_response
                        })
    # Trigger a scroll to bottom of the chat
    html("""
        <div id="div" />
        <script>
            // Scroll the div into view smoothly
            var div = document.getElementById('div');
            div.scrollIntoView({ behavior: 'smooth', block: 'end' });
        </script>
        """)