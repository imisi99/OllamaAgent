import random
import streamlit as st

st.header(":red[Ollama] :rainbow[_Agent_]", divider="grey", width="content")

chat_holders = [
    "What's on your mind ?",
    "How can i help you today ?",
    "Hey Imisioluwa",
    "Back at it again !",
]

st.subheader(chat_holders[random.randint(0, len(chat_holders) - 1)])

if prompt := st.chat_input(
    "",
    key="chat",
    accept_file="multiple",
):
    st.rerun()
