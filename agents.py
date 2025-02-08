from langgraph.prebuilt import create_react_agent

from tools import tavily_tool, input_validation_tool, ashrae_lookup_tool, recommendation_tool, llm_tool
from models import llm_gemini, llm_gpt

llm = llm_gemini

# Agents
llm_agent = create_react_agent(
    llm, tools=[llm_tool], 
    state_modifier="You are a highly-trained research analyst and can provide the user with the information they need.\
        You are tasked with finding the answer to the user's question without using any tools.\
        Answer the user's question to the best of your ability."
)

research_agent = create_react_agent(
    llm, tools=[tavily_tool], state_modifier="You are a highly trained researcher. You are tasked with \
    finding the answer to the user's question. You have access to the following tool: Tavily Search. Use it wisely.")

input_validation_agent = create_react_agent(llm, tools=[input_validation_tool],
    state_modifier="You are an input validator. Check if SHGC (0-1), window area (ft²), U-value, and city are provided and valid."
)

ashrae_lookup_agent = create_react_agent(
    llm, 
    tools=[ashrae_lookup_tool],
    state_modifier="You look up requested information from ASHRAE documents using RAG."
)

recommendation_agent = create_react_agent(
    llm,
    tools=[recommendation_tool],
    state_modifier="""You analyze building component performance and provide clear recommendations.
    You receive performance comparisons and create helpful insights.
    Keep recommendations clear and direct."""
)