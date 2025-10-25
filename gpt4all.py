from gpt4all import GPT4All

def main():
    # Initialize the GPT4All model
    model = GPT4All("mistral-7b-instruct-v0.1.Q4_0.gguf")  # Using Mistral model

    # Define a prompt
    prompt = "Explain the theory of relativity in simple terms."

    # Generate a response from the model
    response = model.generate(prompt)

    # Print the response
    print("Response from GPT4All:")
    print(response)
if __name__ == "__main__":
    main()