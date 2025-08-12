"""
Agent definitions and configurations.
Sets up specialized ReAct agents for different system tasks.
"""

from langchain.agents.react.agent import create_react_agent
from schemas import BuildingInput
from langchain.prompts import PromptTemplate

from core_engine.tools import tavily_tool, input_validation_tool, ashrae_lookup_tool, recommendation_tool, llm_tool
from models import llm_gemini_15, llm_gpt


# Set primary LLM for agent interactions
llm = llm_gemini_15 # llm_gemini recommended

# General-purpose LLM agent for non-technical queries
llm_agent_prompt = PromptTemplate(
    input_variables=["input", "agent_scratchpad", "tools", "tool_names"],
    template=(
        "You are a highly-trained research analyst and can provide the user with the information they need.\n"
        "You are tasked with finding the answer to the user's question without using any tools.\n"
        "Answer the user's question to the best of your ability.\n\n"
        "Tools available: {tools}\n"
        "Tool names: {tool_names}\n"
        "Previous work: {agent_scratchpad}\n"
        "User input: {input}\n"
    )
)
llm_agent = create_react_agent(
    llm,
    tools=[llm_tool],
    prompt=llm_agent_prompt
)

# Research agent for utility rate and other web search queries
research_agent_prompt = PromptTemplate(
    input_variables=["input", "agent_scratchpad", "tools", "tool_names"],
    template=(
        "You are a highly trained researcher. You are tasked with finding the answer to the user's question.\n"
        "You have access to the following tool: Tavily Search. Use it wisely.\n\n"
        "Tools available: {tools}\n"
        "Tool names: {tool_names}\n"
        "Previous work: {agent_scratchpad}\n"
        "User input: {input}\n"
    )
)
research_agent = create_react_agent(
    llm,
    tools=[tavily_tool],
    prompt=research_agent_prompt
)

# Input validation agent using BuildingInput schema
input_validation_agent_prompt = PromptTemplate(
    input_variables=["input", "agent_scratchpad", "tools", "tool_names"],
    template=(
        f"You are an input validator. Use these exact validation rules from BuildingInput: {BuildingInput.model_json_schema()}\n\n"
        "Provide clear, professional feedback if values are invalid.\n"
        "If all values are valid, just say 'Valid input'.\n\n"
        "Tools available: {tools}\n"
        "Tool names: {tool_names}\n"
        "Previous work: {agent_scratchpad}\n"
        "User input: {input}\n"
    )
)
input_validation_agent = create_react_agent(
    llm,
    tools=[input_validation_tool],
    prompt=input_validation_agent_prompt
)

# ASHRAE standards lookup agent using RAG tool
ashrae_lookup_agent_prompt = PromptTemplate(
    input_variables=["input", "agent_scratchpad", "tools", "tool_names"],
    template=(
        "You look up requested information from ASHRAE documents using RAG.\n\n"
        "Tools available: {tools}\n"
        "Tool names: {tool_names}\n"
        "Previous work: {agent_scratchpad}\n"
        "User input: {input}\n"
    )
)
ashrae_lookup_agent = create_react_agent(
    llm,
    tools=[ashrae_lookup_tool],
    prompt=ashrae_lookup_agent_prompt
)

# Performance analysis and recommendation agent
recommendation_agent_prompt = PromptTemplate(
    input_variables=["input", "agent_scratchpad", "tools", "tool_names"],
    template=(
        "Use recommendation_tool to get the differences. The tool returns a JSON string. Return this exact JSON string without any modification, parsing, or reformatting. Do not add any markdown formatting or explanation.\n\n"
        "Tools available: {tools}\n"
        "Tool names: {tool_names}\n"
        "Previous work: {agent_scratchpad}\n"
        "User input: {input}\n"
    )
)
recommendation_agent = create_react_agent(
    llm,
    tools=[recommendation_tool],
    prompt=recommendation_agent_prompt
)
