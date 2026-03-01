import random
import streamlit as st

st.header(":red[Ollama] :rainbow[_Agent_]", divider="grey", width="content")

chat_holders = [
    "what's on your mind ?",
    "how can i help you today ?",
]

st.subheader(chat_holders[random.randint(0, len(chat_holders) - 1)])

prompt = st.chat_input(
    "",
    key="chat",
    accept_file="multiple",
)
