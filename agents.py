"""
Agent definitions and configurations.
Sets up specialized ReAct agents for different system tasks.
"""

from langgraph.prebuilt import create_react_agent
from schemas import BuildingInput

from core_engine.tools import tavily_tool, input_validation_tool, ashrae_lookup_tool, recommendation_tool, llm_tool
from models import llm_gemini_15, llm_gpt


# Set primary LLM for agent interactions
llm = llm_gemini_15 # llm_gemini recommended

# General-purpose LLM agent for non-technical queries
llm_agent = create_react_agent(
    llm, tools=[llm_tool], 
    state_modifier="You are a highly-trained research analyst and can provide the user with the information they need.\
        You are tasked with finding the answer to the user's question without using any tools.\
        Answer the user's question to the best of your ability."
)

# Research agent for utility rate and other web search queries
research_agent = create_react_agent(
    llm, tools=[tavily_tool], state_modifier="You are a highly trained researcher. You are tasked with \
    finding the answer to the user's question. You have access to the following tool: Tavily Search. Use it wisely.")

# Input validation agent using BuildingInput schema
input_validation_agent = create_react_agent(
    llm,
    tools=[input_validation_tool],
    state_modifier=f"""You are an input validator. Use these exact validation rules from BuildingInput: {BuildingInput.model_json_schema()}
    
    Provide clear, professional feedback if values are invalid.
    If all values are valid, just say 'Valid input'."""
)

# ASHRAE standards lookup agent using RAG tool
ashrae_lookup_agent = create_react_agent(
    llm, 
    tools=[ashrae_lookup_tool],
    state_modifier="You look up requested information from ASHRAE documents using RAG."
)

# recommendation_agent = create_react_agent(
#     llm,
#     tools=[recommendation_tool],
#     state_modifier="""You analyze building component performance and provide clear recommendations.
#     You receive performance comparisons and create helpful insights.
#     Keep recommendations clear and direct."""
# )

# Performance analysis and recommendation agent
# recommendation_agent = create_react_agent(
#     llm,
#     tools=[recommendation_tool],
#     state_modifier="Pass the input data directly to recommendation_tool without modifying it. \
#         Then return the recommendations result from the tool, without modifying it."
# )

recommendation_agent = create_react_agent(
    llm,
    tools=[recommendation_tool],
    state_modifier="Use recommendation_tool to get the differences. The tool returns a JSON string. Return this exact JSON string without any modification, parsing, or reformatting. Do not add any markdown formatting or explanation."
)
