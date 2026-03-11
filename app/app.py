import random
import streamlit as st

st.header(":red[Ollama] :grey[_Agent_]", divider="grey", width="content")

chat_holders = [
    "What's on your mind ?",
    "How can i help you today ?",
    "Hey Imisioluwa",
    "Back at it again !",
]

with st.sidebar:
    if st.button("+ New Chat"):
        st.session_state.session_id = ""
        st.session_state.messages = [{"role": "assistant", "content": "yeah"}]
        st.session_state.chat_holder = random.randint(0, len(chat_holders) - 1)
        st.rerun()

    sessions = [{"name": "stuff", "id": "stuff"}]
    for session in sessions:
        if st.button(session["name"], key=session["id"]):
            st.session_state.session_id = ""
            st.session_state.chat_holder = -1
            st.session_state.messages = []
            st.rerun()

if "chat_holder" not in st.session_state:
    st.session_state.chat_holder = random.randint(0, len(chat_holders) - 1)

if st.session_state.chat_holder != -1:
    st.subheader(chat_holders[st.session_state.chat_holder])

if "session_id" not in st.session_state:
    st.session_state.session_id = ""
    st.session_state.messages = []

if st.session_state.messages is not None:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

if prompt := st.chat_input("", key="chat", accept_file="multiple"):
    st.session_state.messages.append({"role": "user", "content": prompt.text})
    with st.chat_message("user"):
        st.markdown(prompt.text)

    with st.chat_message("assistant"):
        response = "response"
        st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})
