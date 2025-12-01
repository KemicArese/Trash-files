from gpt4all import GPT4All
import sys
import time

def main():
    print("Initializing the model (this might take a while)...")
    try:
        # Initialize the GPT4All model with a smaller model
        model = GPT4All("D:/Models/DeepSeek-R1-Distill-Qwen-7B-Q4_0.gguf")  # Using a smaller model for faster loading
        print("Model loaded successfully!")
    except Exception as e:
        print(f"Error loading the model: {str(e)}")
        sys.exit(1)

    # Define a prompt
    prompt = "Explain the theory of relativity in simple terms."

    # Generate a response from the model
    response = model.generate(prompt)

    # Print the response
    print("Response from GPT4All:")
    print(response)
if __name__ == "__main__":
    main()