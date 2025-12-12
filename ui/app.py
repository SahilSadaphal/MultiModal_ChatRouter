import streamlit as st
import requests
import uuid

st.set_page_config(page_title="Multi-Modal Chatbot", layout="centered")

CHATBOT_API_URL = "http://localhost:8963/send"

if "session_id" not in st.session_state:
    st.session_state["session_id"] = None

if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

st.title("Multi-Modal Chatbot")
st.write("Type your message below or upload a file (PDF, Image, Audio) for multi-modal interaction.")

message_input = st.text_area("Your message:", height=120)
uploaded_file = st.file_uploader("Upload a file (optional):", type=None)

def send_message_to_bot(message, file=None):
    """Send user message and optional file to the chatbot API."""
    payload = {"query": message}

    if st.session_state.session_id:
        payload["session_id"] = st.session_state.session_id

    files = {}
    if file:
        files["file"] = (file.name, file.getvalue(), file.type)
    print(f"File :{files}")
    try:
        with st.spinner("Bot is thinking..."):
            response = requests.post(CHATBOT_API_URL, data=payload, files=files)

        if response.status_code == 200:
            data = response.json()
            st.session_state.session_id = data.get("session_id")
            return data.get("response")
        else:
            st.error(f"Server error: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"Error connecting to server: {e}")
        return None

if st.button("Send"):
    if not message_input.strip():
        st.warning("Please type a message before sending.")
    else:
        bot_reply = send_message_to_bot(message_input, uploaded_file)
        if bot_reply:
            st.session_state.chat_history.append(("You", message_input))
            st.session_state.chat_history.append(("Bot", bot_reply))


st.markdown("---")
st.header("Chat History")

for sender, msg in st.session_state.chat_history:
    if sender == "You":
        st.markdown(f"**You:** {msg}")
    else:
        st.markdown(f"**Bot:** {msg}")

