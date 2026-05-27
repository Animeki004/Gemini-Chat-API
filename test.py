from gemini_client import Chatbot, Model

# Initialize bot
bot = Chatbot(
    cookie_path="cookies.json",
    model=Model.G_3_1_FLASH_LITE
)

print("Gemini Chat Started")
print("Type 'exit' to quit.\n")

while True:
    user_input = input("You: ")

    if user_input.lower() == "exit":
        break

    # Optional image input
    image_path = input("Image path (press Enter to skip): ").strip()

    try:
        if image_path:
            response = bot.ask(
                user_input,
                image=image_path
            )
        else:
            response = bot.ask(user_input)

        print("\nGemini:", response["content"])
        print()

    except Exception as e:
        print("Error:", e)