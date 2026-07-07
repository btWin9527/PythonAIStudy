from langchain.agents import create_agent


def get_weather(city: str) -> str:
    """
    Get wwather for a given city.
    """
    return f"It's a always sunny in {city}!"


agent = create_agent(
    tools=[get_weather],
    model="gpt-4",
    system_prompt="You are a helpful assistant.",
)

result = agent.invoke({
    "messages": [{"role": "user", "content": "What's the weather in San Francisco?"}]
})

print(result["messages"][-1].content_blocks)
