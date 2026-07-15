import streamlit as st
from openai import OpenAI
from utils.mongodb import check_identifier, log_transcript
import os

def setup_session_state():
    """Initialize session state variables"""
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if "user_identifier" not in st.session_state:
        st.session_state["user_identifier"] = ""

    if "conversation_finished" not in st.session_state:
        st.session_state["conversation_finished"] = False

    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    if "response_counter" not in st.session_state:
        st.session_state["response_counter"] = 0
        
    if "session_id" not in st.session_state:
        st.session_state["session_id"] = None

    if "chatbot_prompt" not in st.session_state:
        # Load the prompt from the prompt.txt file
        prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "prompt.txt")
        try:
            with open(prompt_path, "r", encoding="utf-8") as file:
                st.session_state["chatbot_prompt"] = file.read()
        except FileNotFoundError:
            st.error("Prompt file not found. Please ensure prompt.txt exists in the prompts directory.")
            st.session_state["chatbot_prompt"] = "You are a helpful assistant."

    if "mongodb_uri" not in st.session_state:
        st.session_state["mongodb_uri"] = st.secrets.get("MONGODB_CONNECTION_STRING", "")
        
    if "mongodb_database_name" not in st.session_state:
        st.session_state["mongodb_database_name"] = st.secrets.get("MONGODB_DATABASE_NAME", "")

    # Set up OpenAI client
    try:
        client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
        return client
    except KeyError:
        st.error("OpenAI API key not found in secrets. Please check your .streamlit/secrets.toml file.")
        return None

def login_page():
    """Display the login page"""
    st.title("🔐 Login to Decimal Misconceptions Chatbot")

    st.markdown("""
    Welcome to the Decimal Misconceptions Chatbot!

    This chatbot simulates a 13-year-old student struggling with decimal concepts.
    You'll need to log in with a valid identifier to start chatting.
    """)

    identifier = st.text_input(
        "Enter your identifier:",
        key="identifier_input",
        value=st.session_state.get("user_identifier", ""),
        help="Enter a valid identifier to access the chatbot"
    )

    if st.button("Login", use_container_width=True):
        if identifier and len(identifier.strip()) >= 3:
            if check_identifier(st.session_state.get("mongodb_uri", ""), st.session_state.get("mongodb_database_name", ""), identifier):
                st.session_state["user_identifier"] = identifier
                st.session_state["logged_in"] = True
                st.success("✅ Login successful! Redirecting to chat...")
                st.session_state.conversation_finished = False
                st.rerun()
            else:
                st.error("❌ Invalid identifier. Please check your identifier and try again.")
        else:
            st.warning("⚠️ Please enter an identifier with at least 3 characters.")

def chat_page(client):
    """Display the chat interface"""
    st.title("Decimal Misconceptions Chatbot")

    # Display user info
    st.markdown(f"**Logged in as:** {st.session_state['user_identifier']}")

    # Logout button
    col1, col2, col3 = st.columns([1, 1, 1])
    with col3:
        if st.button("Logout", key="logout") and st.session_state.chat_history and not st.session_state.conversation_finished:
            st.session_state.conversation_finished = True 
            st.session_state["logged_in"] = False
            session_id = log_transcript(
                st.session_state["mongodb_uri"],
                st.session_state["mongodb_database_name"],
                "decimal_misconceptions_chatbot",
                st.session_state.chat_history
            )
            st.session_state.session_id = session_id 
            st.session_state["chat_history"] = [] 
            st.session_state["response_counter"] = 0  
            st.rerun()

    st.markdown("---")

    # Display chat history
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    MAX_RESPONSES = 50
    if prompt := st.chat_input(
        "Ask the student about decimals...",
        disabled=st.session_state.response_counter >= MAX_RESPONSES
    ):
        # Add user message to history
        st.session_state.chat_history.append({"role": "user", "content": prompt})

        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate AI response
        if st.session_state.response_counter < MAX_RESPONSES:
            with st.chat_message("assistant"):
                messages_with_system_prompt = [
                    {"role": "system", "content": st.session_state["chatbot_prompt"]}
                ] + [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.chat_history
                ]

                try:
                    stream = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=messages_with_system_prompt,
                        stream=True,
                    )
                    response = st.write_stream(stream)

                    # Add AI response to history
                    st.session_state.chat_history.append({"role": "assistant", "content": response})
                    st.session_state.response_counter += 1

                except Exception as e:
                    st.error(f"Error generating response: {str(e)}")
                    # Add error message to history
                    error_msg = "Sorry, I encountered an error. Please try again."
                    st.session_state.chat_history.append({"role": "assistant", "content": error_msg})
        else:
            with st.chat_message("assistant"):
                st.markdown("I've reached the maximum number of responses for this session. Thanks for chatting!")
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": "I've reached the maximum number of responses for this session. Thanks for chatting!"
            })

def main():
    """Main application function"""
    st.set_page_config(
        page_title="Decimal Misconceptions Chatbot",
        page_icon="🤖",
        layout="wide"
    )

    # Initialize session state and get client
    client = setup_session_state()

    if not client:
        st.error("Failed to initialize OpenAI client. Please check your configuration.")
        return

    # Route to appropriate page
    if not st.session_state.get("logged_in", False):
        login_page()
    else:
        chat_page(client)

if __name__ == "__main__":
    main()
