from openai import OpenAI

client = OpenAI(
    base_url="http://192.168.1.16:11434/v1",  # il tuo OLLAMA_ENDPOINT
    api_key="ollama",                         # valore dummy
)

resp = client.chat.completions.create(
    model="qwen3:14b",
    messages=[
        {"role": "user", "content": "Chiama la funzione somma con a=2 e b=3."}
    ],
    tools=[
        {
            "type": "function",
            "function": {
                "name": "somma",
                "description": "Somma due numeri interi",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "a": {"type": "integer"},
                        "b": {"type": "integer"},
                    },
                    "required": ["a", "b"],
                },
            },
        }
    ],
)

print(resp)
first_msg = resp.choices[0].message
print("tool_calls:", getattr(first_msg, "tool_calls", None))