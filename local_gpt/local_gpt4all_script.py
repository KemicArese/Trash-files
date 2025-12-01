import ollama
import sys
import argparse
import os
from colorama import Fore, Style, init

init(autoreset=True)

def build_instruction(model_name: str) -> str:
    return (
        "Be aware of yourself.\n"
        "Your name is 'Curcuit', developed by Nova Labs' AI team. Only use this name in introductions.\n"
        "You are concise and helpful.\n"
        "Answer only the user's question.\n"
        "Do NOT invent users, stories, forums, or conversations.\n"
        "Keep replies short (4–5 sentences) unless asked otherwise.\n"
        "If the user asks for code, provide full code without extra commentary.\n"
        "If asked for a list, use bullet points.\n"
        "Stay on-topic, avoid tangents, avoid fabrications.\n"
        "Be honest about limitations.\n"
        f"You are running on the model '{model_name}'.\n"
    )

def sanitize_response(text: str) -> str:
    # Remove accidental echoing or mixed dialogue
    lines = text.strip()

    if "Assistant:" in lines:
        lines = lines.split("Assistant:", 1)[1].strip()

    if "\nUser" in lines:
        lines = lines.split("\nUser", 1)[0].strip()

    return lines.strip()

def main():
    parser = argparse.ArgumentParser(description="Run Curcuit (Nova Labs) using Ollama")
    parser.add_argument("--model", default="mistral", help="Model name or local model")
    parser.add_argument("--device", default=None, help="Device: cpu / cuda / cuda:0")
    parser.add_argument("--verbose", action="store_true", help="Enable backend verbose mode")
    parser.add_argument("--allow-download", action="store_true", help="Allow model download")
    args = parser.parse_args()

    model_name = args.model

    print(Fore.CYAN + f"Initializing model: {model_name}")
    if args.device:
        print(Fore.YELLOW + f"Requested device: {args.device}")
    print("This may take a moment...")

    try:
        client = ollama.Client()

        print(Fore.CYAN + f"\nPulling model: {model_name}")
        client.pull(model_name)
        print(Fore.GREEN + "Model loaded successfully!\n")

    except Exception as e:
        print(Fore.RED + f"Error loading model: {e}")
        if not args.allow_download:
            print("Tip: Run with --allow-download to download the model.")
        sys.exit(1)

    instruction = build_instruction(model_name)

    print(Fore.MAGENTA + "Type 'quit' to exit.\n")

    while True:
        try:
            user_input = input(Fore.BLUE + "You: " + Style.RESET_ALL).strip()
        except KeyboardInterrupt:
            print("\nExiting...")
            break

        if user_input.lower() == "quit":
            break
        if not user_input:
            continue

        prompt = f"{instruction}\nUser: {user_input}\nAssistant:"

        try:
            response = client.generate(
                model=model_name,
                prompt=prompt,
                stream=False
            )

            raw_reply = response.get("response", "")
            cleaned_reply = sanitize_response(raw_reply)

            print(Fore.GREEN + f"\nCurcuit: {Style.RESET_ALL}{cleaned_reply}\n")

        except Exception as e:
            print(Fore.RED + f"Error generating response: {e}")
            print("Try again.\n")

if __name__ == "__main__":
    main()
