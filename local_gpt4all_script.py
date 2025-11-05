from gpt4all import GPT4All
import sys
import argparse

def main():
    # Set up model directory
    import os
    model_dir = "D:/Models"
    os.makedirs(model_dir, exist_ok=True)
    
    parser = argparse.ArgumentParser(description="Run GPT4All chatbot")
    parser.add_argument("--model", help="Model name to use", 
                      default="mistral-7b-instruct-v0.1.Q4_0.gguf")
    args = parser.parse_args()

    model_name = args.model
    model_path = os.path.join(model_dir, model_name)

    print(f"Initializing model: {model_name}")
    print("This may take a moment... (model will be downloaded if needed)")

    try:
        # Initialize the model with specified model directory
        model = GPT4All(model_name, model_path=model_dir, allow_download=True)
        
        print(f"\nModel loaded at: {model_dir}")
        print("Type 'quit' to exit")
        print("Note: First generation might be slow as the model warms up")
        
        while True:
            user_input = input("\nYou: ").strip()
            if user_input.lower() == 'quit':
                break
                
            if not user_input:
                continue
                
            try:
                # Build a strict instruction prompt to avoid the model inventing other users
                instruction = (
                    "You are a concise, helpful assistant.\n"
                    "Answer only the user's question. Do NOT invent other users, forum posts, or prior conversations.\n"
                    "Keep replies short (4 or 5 sentences) unless the user asks for more."
                    "Give complete codes when user asks for code.\n"
                    "If the user asks for a list, use bullet points."
                    "Remain on topic and avoid unnecessary elaboration."
                    "If the user asks for code, provide it without additional commentary."
                    "Remember, your name is 'Curcuit', and you were developed by Nova Labs' AI team. Use this name in introductions only. You are not to create or reference any other fictional entities. You are specially developed to assist the Nova Labs team."
                    "You are a large language model trained to assist with a variety of tasks."
                    "Your primary goal is to provide accurate and helpful information to the user."
                    "If you don't know the answer, it's okay to say so."
                    "Be honest about your capabilities and limitations."
                    "Do not fabricate information."
                    "Do not create fictional users or conversations."
                    "Stay focused on the user's queries and provide clear, concise answers."
                    "Avoid unnecessary elaboration or tangents."
                    "Keep responses relevant and to the point."
                    "Be friendly and professional in your tone."
                    "Use proper grammar and spelling."
                )
                prompt = f"{instruction}\n\nUser: {user_input}\nAssistant:"

                # Generate response with conservative sampling to reduce hallucinations
                raw = model.generate(
                    prompt,
                    max_tokens=128,
                    temp=0.2,
                    top_k=40,
                    top_p=0.9,
                    repeat_penalty=1.1,
                )

                # Post-process: trim and remove any accidental multi-user text
                resp = raw.strip()
                # If the model echoes the prompt, strip it out
                if resp.startswith(prompt):
                    resp = resp[len(prompt):].strip()
                # If the model includes 'Assistant:' label, remove everything before it
                if "Assistant:" in resp:
                    resp = resp.split("Assistant:", 1)[1].strip()
                # If the model includes another 'User' block, keep only text before it
                if "\nUser" in resp:
                    resp = resp.split("\nUser", 1)[0].strip()

                print(f"\nBot: {resp}")
                
            except Exception as e:
                print(f"\nError generating response: {str(e)}")
                print("Try a different prompt or restart if issues persist")

    except Exception as e:
        print(f"\nError loading model: {str(e)}")
        if not args.allow_download:
            print("\nTip: Run with --allow-download to download the model if it's not found locally")
        sys.exit(1)

if __name__ == "__main__":
    main()
