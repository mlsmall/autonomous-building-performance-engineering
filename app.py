import streamlit as st
from streamlit_extras.stylable_container import stylable_container
from graph import main_loop, graph
import json

print("DEBUG 0: Starting Streamlit app")

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

print("DEBUG 1: Initialized Streamlit settings")

# Initialize session state for chat
if 'messages' not in st.session_state:
    st.session_state.messages = []
    st.session_state.user_id = None
    print("DEBUG 2: Initialized session state")

# Main content
st.title("Building Energy Performance Analyzer")

# User ID Input (if not already provided)
if not st.session_state.user_id:
    print("DEBUG 3: Asking for user ID")
    user_id = st.text_input("Please enter your email as user ID:")
    if st.button("Start Analysis"):
        print(f"DEBUG 4: Got user ID: {user_id}")
        st.session_state.user_id = user_id
        st.rerun()

# Chat Interface
if st.session_state.user_id:
    print("DEBUG 5: Starting chat interface")
    # Display chat messages
    print("DEBUG 6: Displaying existing messages:", len(st.session_state.messages))
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
            print(f"DEBUG 7: Displayed message - Role: {message['role']}")

    # Chat input
    if prompt := st.chat_input("Enter your building details:"):
        print(f"DEBUG 8: Got new input: {prompt}")
        # Add user message to chat
        st.session_state.messages.append({"role": "user", "content": prompt})
        print("DEBUG 9: Added user message to session")
        
        print("DEBUG 10: Starting graph stream")
        for state in graph.stream({
            "messages": [("user", prompt)],
            "next": "",
            "user_id": st.session_state.user_id,
            "existing_data": None
        }, config={"configurable": {"thread_id": "1"}}):
            print(f"DEBUG 11: Processing state: {state.keys()}")
            st.write(state)
            print("DEBUG 12: Wrote state to Streamlit")
            
            if 'recommendation' in state:
                print("DEBUG 13: Found recommendations")
                try:
                    recs = json.loads(state['recommendation']['messages'][0].content)
                    print("DEBUG 14: Parsed recommendations JSON")
                    recommendations = "\n".join(recs['recommendations'])
                    print(f"DEBUG 15: Formatted recommendations: {recommendations}")
                    st.session_state.messages.append({"role": "assistant", "content": recommendations})
                    print("DEBUG 16: Added recommendations to session")
                except Exception as e:
                    print(f"DEBUG ERROR: Failed to process recommendations: {e}")
                    
        print("DEBUG 17: Graph stream completed")
        st.rerun()
        print("DEBUG 18: Triggered Streamlit rerun")

print("DEBUG 19: Streamlit app loop completed")