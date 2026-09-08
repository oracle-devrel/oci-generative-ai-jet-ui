from agent_reasoning.interceptor import ReasoningInterceptor


def main():
    print("Initializing Reasoning Interceptor...")
    client = ReasoningInterceptor()

    # Example 1: Standard Generation (Non-streaming)
    print("\n--- Example 1: Standard (No Strategy) ---")
    resp = client.generate(model="gemma3:270m", prompt="What is 2+2?")
    print(f"Response: {resp['response']}")

    # Example 2: CoT Generation (Streaming)
    print("\n--- Example 2: CoT Strategy (Streaming) ---")
    stream = client.generate(
        model="gemma3:270m+cot",
        prompt="If I have 3 apples and eat 1, how many do I have?",
        stream=True,
    )

    print("Streaming output:", end=" ")
    for chunk in stream:
        if "response" in chunk:
            print(chunk["response"], end="", flush=True)
    print()

    # Example 3: Chat with ToT
    print("\n--- Example 3: Chat Interface with ToT ---")
    messages = [
        {"role": "user", "content": "I need a creative name for a pet rock. Give me options."}
    ]
    resp = client.chat(model="gemma3:270m+tot", messages=messages)
    print(f"Final Response:\n{resp['response']}")


if __name__ == "__main__":
    main()
