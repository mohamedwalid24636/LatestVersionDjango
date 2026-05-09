from gradio_client import Client

def ask_yousef_chatbot(message):
    try:
        client = Client("Yousef32/chatbot")
        result = client.predict(
            message=message,
            token="",  
            api_name="/handle"
        )
        

        chat_history, emotion, crisis_info, rag = result
        
        bot_reply = "I'm listening. Can you tell me more?"
        if chat_history:
            last_message = chat_history[-1]
            if last_message.get("content"):
                bot_reply = last_message["content"][0].get("text", bot_reply)
        
        return {
            "reply": bot_reply,
            "emotion": emotion,
            "crisis_info": crisis_info
        }
    except Exception as e:
        print(f"HuggingFace Error: {e}")
        return None
    