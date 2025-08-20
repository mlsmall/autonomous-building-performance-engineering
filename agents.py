"""
Agent definitions and configurations.
Sets up specialized ReAct agents for different system tasks.
"""

from langchain.agents.react.agent import create_react_agent
from langchain.agents import AgentExecutor
from schemas import BuildingInput
from langchain.prompts import PromptTemplate

from core_engine.tools import tavily_tool, input_validation_tool, ashrae_lookup_tool, recommendation_tool, llm_tool
from models import llm_gemini_15, llm_gpt, llm_gemini_25


# Set primary LLM for agent interactions
llm = llm_gemini_25 # llm_gemini recommended

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
llm_executor = AgentExecutor(
    agent=llm_agent,
    tools=[llm_tool],
    handle_parsing_errors=True,
    verbose=False,
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
research_executor = AgentExecutor(
    agent=research_agent,
    tools=[tavily_tool],
    handle_parsing_errors=True,
    verbose=False,
)

# Input validation agent using BuildingInput schema
schema_rules = str(BuildingInput.model_json_schema())
input_validation_agent_prompt = PromptTemplate(
    input_variables=["input", "agent_scratchpad", "tools", "tool_names"],
    template=(
        f"You are an input validator. Use these exact validation rules from BuildingInput: {schema_rules}\n\n"
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
input_validation_executor = AgentExecutor(
    agent=input_validation_agent,
    tools=[input_validation_tool],
    handle_parsing_errors=True,
    verbose=False,
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
ashrae_lookup_executor = AgentExecutor(
    agent=ashrae_lookup_agent,
    tools=[ashrae_lookup_tool],
    handle_parsing_errors=True,
    return_intermediate_steps=True,
    verbose=False,
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
recommendation_executor = AgentExecutor(
    agent=recommendation_agent,
    tools=[recommendation_tool],
    handle_parsing_errors=True,
    verbose=False,
)
