import streamlit as st
from streamlit_extras.stylable_container import stylable_container
from graph import main_loop, graph
import json

print("Starting Streamlit app...")

# Premium look settings
st.set_page_config(layout="wide", page_title="Building Energy Analyzer")

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

# Decorative sidebar - just for looks
with st.sidebar:
    st.title("Building Analysis")
    st.markdown("---")
    st.markdown("### Features")
    st.markdown("• Energy Analysis")
    st.markdown("• Cost Optimization")
    st.markdown("• ASHRAE Compliance")
    st.markdown("---")

# Initialize session state for chat
if 'messages' not in st.session_state:
    st.session_state.messages = []
    st.session_state.user_id = None
    print("Session state initialized")

# Main content
st.title("Building Energy Performance Analyzer")

# User ID Input (if not already provided)
if not st.session_state.user_id:
    user_id = st.text_input("Please enter your email as user ID:")
    if st.button("Start Analysis"):
        st.session_state.user_id = user_id

# Chat Interface
if st.session_state.user_id:
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    # Chat input
    if prompt := st.chat_input("Enter your building details:"):
        print(f"Received input: {prompt}")
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        print("Starting graph stream...")
        with st.empty():
            for state in graph.stream({
                "messages": [("user", prompt)],
                "user_id": st.session_state.user_id,
                "existing_data": None
            }, config={"configurable": {"thread_id": "1"}}):
                print(f"State update: {state}")
                st.write(state)
                
                if 'recommendation' in state:
                    print("Processing recommendation...")
                    recs = json.loads(state['recommendation']['messages'][0].content)
                    response = "\n".join(recs['recommendations'])
                    st.session_state.messages.append({"role": "assistant", "content": response})