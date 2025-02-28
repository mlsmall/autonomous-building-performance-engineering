from langgraph.prebuilt import create_react_agent
from schemas import BuildingInput

from core_engine.tools import tavily_tool, input_validation_tool, ashrae_lookup_tool, recommendation_tool, llm_tool
from models import llm_gemini, llm_gpt


llm = llm_gemini # llm_gemini recommended

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

# input_validation_agent = create_react_agent(llm, tools=[input_validation_tool],
#     state_modifier="You are an input validator. Check if SHGC (0-1), window area (ft²), U-value, and city are provided and valid."
# )

# # print("BUILDING INPUT BASEMODEL", BuildingInput.model_json_schema())

input_validation_agent = create_react_agent(
    llm,
    tools=[input_validation_tool],
    state_modifier=f"""You are an input validator. Use these exact validation rules from BuildingInput: {BuildingInput.model_json_schema()}
    
    Provide clear, professional feedback if values are invalid.
    If all values are valid, just say 'Valid input'."""
)



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


recommendation_agent = create_react_agent(
    llm,
    tools=[recommendation_tool],
    state_modifier="Pass the input data directly to recommendation_tool without modifying it. \
        Then return the recommendations result from the tool, without modifying it."
)