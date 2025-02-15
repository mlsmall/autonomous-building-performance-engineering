import streamlit as st
from streamlit_extras.stylable_container import stylable_container
from graph import graph, USE_DATABASE
import json

# Rest of the code remains the same, and remove the USE_DATABASE = False line since we're importing it
# Premium look settings
st.set_page_config(layout="wide", page_title="Building Performance Assistant")

# Custom CSS for premium feel
st.markdown("""
<style>
    .main {
        background-color: #f8f9fa;
    }
    .stApp {
        background: linear-gradient(180deg, #ffffff 0%, #f8f9fa 100%);
    }
    .css-1d391kg {
        padding: 3rem 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Clean, minimal sidebar
with st.sidebar:
    st.title("Energy Analysis")
    st.markdown("---")
    st.markdown("### Quick Guide")
    st.markdown("Enter your building details in this format:")
    st.code("window area = 10000 ft2\nshgc = 0.40\nu-value = 0.9\ncity = Montreal")
    st.markdown("---")
    st.markdown("Made with 🏗️ by Kalevi Productions")

# Initialize session state for chat
if 'messages' not in st.session_state:
    st.session_state.messages = []
    st.session_state.user_id = None if USE_DATABASE else "test_user"
    # Add initial message
    st.session_state.messages.append({
        "role": "assistant", 
        "content": """Hello, I'm your building performance analyst and engineer. Please enter these inputs:
* Window area (ft²)
* SHGC value (0-1)
* U-value
* Building location (city)"""
    })

# Main content
st.title("Building Performance Assistant")

# User ID Input (only if using database)
if USE_DATABASE and not st.session_state.user_id:
    user_id = st.text_input("Please enter your email as user ID:")
    if st.button("Start Analysis"):
        st.session_state.user_id = user_id
        st.rerun()

# Chat Interface
if st.session_state.user_id:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant" and "%" in message["content"]:
                formatted_content = message["content"].replace("• ", "\n• ").replace("\n", "\n\n")
            else:
                formatted_content = message["content"]
            st.markdown(formatted_content)

    # Chat input
    if prompt := st.chat_input("Enter your building details:"):
        # Add user message to chat
        st.session_state.messages.append({"role": "user", "content": prompt})
        
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