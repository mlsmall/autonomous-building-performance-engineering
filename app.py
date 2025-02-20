import streamlit as st
from streamlit_extras.stylable_container import stylable_container
from graph import graph, USE_DATABASE
import json

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
    
    .stElementContainer,
    .stChatInput,
    [data-baseweb="textarea"] {
        width: 100% !important;
        max-width: 80% !important;
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
if 'messages' not in st.session_state:
    st.session_state.messages = []
    st.session_state.user_id = None if USE_DATABASE else "test_user"
    # Add initial message
    st.session_state.messages.append({
        "role": "assistant", 
        "content": """Hello, I'm your building performance engineer. Please enter these inputs:
* Window area (ft²)
* SHGC value (0-1)
* U-value
* Building location (city)"""
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
            with st.spinner("Analyzing building performance..."):

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