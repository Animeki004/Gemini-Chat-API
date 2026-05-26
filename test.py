from openai import OpenAI

# 1. Replace this with the API key you generated from your Telegram bot (/newkey)
API_KEY = "sk-KrfjeL5r36EvBLMj4a5rMW94C-lZEKKouNcVyCr-KVo"

# 2. Point the OpenAI client to your local FastAPI server
client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key=API_KEY
)

def run_test():
    print("🔄 Fetching available models...")
    try:
        models = client.models.list()
        print(f"✅ Successfully fetched {len(models.data)} models.")
    except Exception as e:
        print(f"❌ Failed to fetch models: {e}")
        return
    
    print("\n💬 Starting Chat Loop! (Type 'quit' or 'exit' to stop)")
    print("---------------------------------------------------------")
    
    # Store conversation history so the bot remembers context
    conversation_history = []
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            
            if user_input.lower() in ['quit', 'exit']:
                print("\nGoodbye! 👋")
                break
                
            if not user_input:
                continue

            # Add user message to history
            conversation_history.append({"role": "user", "content": user_input})
            
            print("⏳ Waiting for response...")
            
            response = client.chat.completions.create(
                model="gemini-2.5-pro",
                messages=conversation_history
            )
            
            bot_reply = response.choices[0].message.content
            
            # Add bot response to history
            conversation_history.append({"role": "assistant", "content": bot_reply})
            
            print(f"\n🤖 Gemini: {bot_reply}")
            
        except KeyboardInterrupt:
            print("\n\nGoodbye! 👋")
            break
        except Exception as e:
             print(f"\n❌ Failed to get chat completion: {e}")
             # Remove the last user message so it can be retried if needed
             if conversation_history and conversation_history[-1]["role"] == "user":
                 conversation_history.pop()

if __name__ == "__main__":
    if API_KEY == "sk-your-api-key-here":
        print("⚠️ Please put your generated API Key in the API_KEY variable at the top of this script first!")
    else:
        run_test()