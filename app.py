import uuid
import streamlit as st
from agent_helper import Agent

st.title("Chatbot with langgraph")

# Sidebar: system message input
with st.sidebar:
    st.header("Chat Settings")
    system_prompt = st.text_area(
        "System Message",
        value=st.session_state.get("system_prompt", "You are a helpful assistant"),
        help="Define how the assistant should behave.",
        height=300
    )

    ## display agent_with_memory.png
    st.subheader("Agent Memory Visualization")
    st.write("This image shows the agent's memory and state transitions.")
    st.image("agent_with_memory.png")

    # Update agent if system prompt changes
    if "system_prompt" not in st.session_state or st.session_state.system_prompt != system_prompt:
        st.session_state.system_prompt = system_prompt
        st.session_state.abot = Agent(system=system_prompt)
        st.session_state.messages = []  # optionally clear history if system changes

# Initialize session state
if "abot" not in st.session_state:
    st.session_state.abot = Agent(system=system_prompt)

if "chat_id" not in st.session_state:
    st.session_state.chat_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(name=message["role"]):
        st.markdown(message["content"])

# Handle new user input
if message := st.chat_input("What is up?"):
    st.session_state.messages.append({"role": "user", "content": message})
    with st.chat_message("user"):
        st.markdown(message)

    ai_response = st.session_state.abot.invoke(message, thread_id=st.session_state.chat_id)
    with st.chat_message("assistant"):
        st.markdown(ai_response)
    st.session_state.messages.append({"role": "assistant", "content": ai_response})
