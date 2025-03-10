"""
Multi-agent orchestration using LangGraph.
Manages agent workflow, state, and interactions for building performance analysis.
"""

from dotenv import load_dotenv
load_dotenv()
import json
import uuid

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage

from agents import llm_agent, research_agent, ashrae_lookup_agent, recommendation_agent, input_validation_agent
from core_engine.tools import calculation_tool, radiation_tool
from models import llm_gemini, llm_gpt
from schemas import AgentState, Recommendation, SupervisorState, members
from database import building_data, get_user_history

llm = llm_gpt # llm_gpt preferred

# Supervisor agent system prompt
# Controls workflow between agents based on input state
system_prompt = f"""You are a supervisor tasked with managing a conversation between the following workers: {members}. 

For User ID: {{user_id}}
{{user_data}}

Given the following user request, respond with the worker to act next. Each worker will perform a task and respond 
with their results and status. When finished, respond with FINISH.

If user_data contains building information:
    - Use those values for calculations
    - Skip asking for inputs we already have
    - If baseline and proposed values exist, then route to recommedation for comparison

If no user_data:
    1. Send all inputs to input_validation to check:
        - SHGC (0-1)
        - Window area (ft²)
        - U-value
        - City

    2. After validation, send validated input to ashrae_lookup
        - When you see ashrae_data in the state, route to utility to get local electricity rates
        - After getting local electricity rates, route to radiation_node to get the solar radiation value

    3. After utility rates and solar radiation values are found:
        - First route to calculation for proposed calculations (using user's U-value and SHGC)
        - Then route to calculation again for baseline calculations (using ASHRAE U-value and SHGC)
        - Proposed AND Baseline calculations must be complete before proceeding

    4. Only after BOTH Proposed AND Baseline calculations are complete:
        - Route to recommendation for comparison
        - Then route to FINISH

Route to llm only for general building questions, never for calculations or data lookups.
"""

# # Nodes
# def supervisor_node(state: AgentState) -> AgentState:
#     print("------------------ SUPERVISOR NODE START ------------------\n")
#     messages = [{"role": "system", "content": system_prompt}] + state["messages"]
#     response = llm.with_structured_output(SupervisorState).invoke(messages)
#     next1 = response.next
#     if next1 == "FINISH":
#         next1 = END

#     print(f"Routing to {next1}")
#     print("\n------------------ SUPERVISOR NODE END ------------------\n")
#     return {"next": next1}

# The supervisor is an LLM node that decides what node to execute next - chore orchestrator
def supervisor_node(state: AgentState) -> AgentState:
    print("\n=== SUPERVISOR NODE START ===")
    
    if USE_DATABASE:
        user_id = state.get('user_id')
        user_data = "No previous building data"

        # Create user_data string if we building data from the user exists
        if any(key in state for key in ['city', 'window_area', 'shgc', 'u_value']):
            user_data = "Building data in state:\n"
            for key in ['city', 'window_area', 'shgc', 'u_value', 'baseline_cost', 'proposed_cost']:
                if key in state:
                    user_data += f"- {key}: {state[key]}\n"        
        
        formatted_prompt = system_prompt.format(
            user_id=user_id,
            user_data=user_data
        )

    else:
        formatted_prompt = system_prompt

    messages = [{"role": "system", "content": formatted_prompt}] + state["messages"]
    response = llm.with_structured_output(SupervisorState).invoke(messages)
    
    next1 = response.next
    if next1 == "FINISH":
        next1 = END

    # Store in MongoDB if enabled
    if USE_DATABASE and state.get("user_id"):
        if next1 == "ashrae_lookup" or next1 == END:
            building_data(state["user_id"], state)

    print(f"Routing to: {next1}")
    print("=== SUPERVISOR NODE END ===\n")
    return {"next": next1}

def llm_node(state: AgentState) -> AgentState:
    """
    General-purpose LLM agent for handling non-technical queries.
    Only used when specific agent tasks are not required.
    """
    result = llm_agent.invoke(state) # We're passing the state to the "create_react_agent" 
    return {"messages": [HumanMessage(content=result["messages"][-1].content, name="llm_node")]}


def input_validation_node(state: AgentState) -> AgentState:
    """
    Validates building input data against the rules specified in the class BuildingInput.
    Returns error state if validation fails, which triggers the user to re-input values.
    """
    result = input_validation_agent.invoke({"messages": state['messages'][-1].content})
    print("AGENT VALIDATION SAID", result["messages"][-1].content)
    
    # Check if validation result is valid and and parse input
    if "Valid input" in result["messages"][-1].content:
        user_input = state["messages"][0].content
        # Extract and convert input values to appropriate types if necessary
        return {
            "city": user_input.split("city =")[1].strip(),
            "window_area": int(user_input.split("window area =")[1].split("ft2")[0].strip().replace(",", "")),
            "shgc": float(user_input.split("shgc =")[1].split()[0].strip()),
            "u_value": float(user_input.split("u-value =")[1].split("city")[0].strip()),
            "messages": [HumanMessage(content=result["messages"][-1].content, name="input_validation")]
        }
    else:
        error_message  = f"{result["messages"][-1].content}  \nPlease enter it again:"
        return {
            "messages": [HumanMessage(content=error_message, name="input_validation")],
            "next": START
        }

def ashrae_lookup_node(state: AgentState) -> AgentState:
    """
    Retrieves ASHRAE energy standards data for a given city.
    Returns climate zone, baseline U-value, and SHGC requirements.
    """
    city = state["city"]
    result = ashrae_lookup_agent.invoke({"messages": [HumanMessage(content=city)]})
    # Parse ASHRAE data from tool response
    tool_message = result["messages"][2].content  # 0 - HumanMessage, 1 - AIMessage, 2 - ToolMessage

    # Validate and extract ASHRAE values
    if "To=" in tool_message  and "CDD=" in tool_message :
        return {
            "ashrae_to": float(tool_message.split("To=")[1].split("\n")[0].strip()),
            "ashrae_cdd": float(tool_message.split("CDD=")[1].split("\n")[0].strip()),
            "ashrae_climate_zone": int(tool_message.split("Climate Zone=")[1].split("\n")[0].strip()),
            "ashrae_u_factor": float(tool_message.split("U-value=")[1].split("\n")[0].strip()),
            "ashrae_shgc": float(tool_message.split("SHGC=")[1].strip()),
            "messages": [HumanMessage(content=result["messages"][-1].content, name="ashrae_lookup")]
        }
    else:
        # Handle invalid city
        return {
            "messages": [HumanMessage(
                content=f"ASHRAE data not found for '{city}'", 
                name="ashrae_lookup"
            )],
            "city": None,  # Clear city
            "next": "input_validation"  # Re-validate
        }

def radiation_node(state: AgentState) -> AgentState:
    """
    Retrieves solar radiation value for a given city.
    """
    city = state["city"]
    result = radiation_tool.invoke(city)

    print("RADIATION NODE RESULT", result)
    return {
        "radiation": float(result),
        "messages": [HumanMessage(content=str(result), name="radiation")]
    }


def utility_node(state: AgentState) -> AgentState:
    """
    Gets local utility rates for cost calculations.
    Uses research agent and Tavily to search current commercial rates.
    """
    city = state["city"]
    # Format query to get only numeric rate value
    query = f"Find an estimated value for the commercial utility rates ($/kWh) in {city}. \
        Please provide only a numeric estimated utility rate value without any additional text. \
        If no utility rate is available, please return '0.1'."
    result = research_agent.invoke({"messages": [HumanMessage(content=query)]})
    return {
        "utility_rate": float(result["messages"][-1].content),
        "messages": [HumanMessage(content=result["messages"][-1].content, name="utility")]
    }

def calculation_node(state: AgentState) -> AgentState:
    """
    Performs building performance calculations for both proposed and baseline cases.
    Currently calculates heat gain, energy use, and operating costs using ASHRAE data.
    """
    # Determine if calculating proposed or baseline case
    if "proposed_heat_gain" not in state: 
        calculation_type = "proposed"
        shgc = state["shgc"]
        u = state["u_value"]
    else:
        calculation_type = "baseline"
        shgc = state["ashrae_shgc"]
        u = state["ashrae_u_factor"]

    # Format calculation query with appropriate values
    query = f"""
heat_gain = window_heat_gain(area={state["window_area"]}, SHGC={shgc}, U={u}, To={state["ashrae_to"]}, radiation={state["radiation"]})
energy = annual_cooling_energy(heat_gain, {state["ashrae_cdd"]})
cost = annual_cost(energy, {state["utility_rate"]})
    """
    result = calculation_tool.invoke(query)
    # Parse the output from the calculation tool
    stdout_index = result.find('Stdout:') # Find the start of the stdout
    stdout = result[stdout_index + len('Stdout:'):].strip() # Extract the stdout
    
    # Convert calculation tool results to float values
    lines = stdout.split('\n') # Split into lines 
    parsed_values = {}
    for line in lines: # Parse each line
        if '=' in line:
            key, value = line.split('=', 1)
            parsed_values[key.strip()] = float(value.strip())
    print("CALCULATION PARSED VALUES", parsed_values, calculation_type)
    # Return results with appropriate prefix (baseline/proposed)
    key_prefix = "baseline" if calculation_type == "baseline" else "proposed"
    return {
        f"{key_prefix}_heat_gain": parsed_values["heat_gain"],
        f"{key_prefix}_cooling_energy": parsed_values["annual_energy"],
        f"{key_prefix}_cost": parsed_values["annual_cost"],
        "messages": [HumanMessage(content=result, name="calculation")]
    }
# def recommendation_node(state: AgentState) -> AgentState:
#     # First use React agent to get analysis
#     result = recommendation_agent.invoke(state)
#     print()
#     # Then use structured output to format the response
#     response = llm.with_structured_output(Recommendation).invoke([HumanMessage(content=result["messages"][-1].content)])
    
#     # Return both the structured response and message
#     state["messages"] = [HumanMessage(content=response.model_dump_json(), name="recommendation")]
#     return state

def recommendation_node(state: AgentState) -> AgentState:
    """
    Analyzes performance differences between proposed and baseline values
    Generates and returns formatted recommendations based on energy and cost comparisons.
    """

    # Format data to send to recommendation agent
    message = f"""proposed_heat_gain: {state['proposed_heat_gain']}
    baseline_heat_gain: {state['baseline_heat_gain']}
    proposed_cooling_energy: {state['proposed_cooling_energy']}
    baseline_cooling_energy: {state['baseline_cooling_energy']}
    proposed_cost: {state['proposed_cost']}
    baseline_cost: {state['baseline_cost']}
    shgc: {state['shgc']}
    ashrae_shgc: {state['ashrae_shgc']}
    u_value: {state['u_value']}
    ashrae_u_factor: {state['ashrae_u_factor']}"""
    print("RECOMMENDATION NODE MESSAGE:", message)
    # Get recommendations and format response based on the Recommendation class
    result = recommendation_agent.invoke({"messages": [("user", message)]})
    agent_response = result["messages"][-1].content
    print("AGENT RESPONSE BEFORE LLM:", agent_response)
    recommendation = llm.with_structured_output(Recommendation).invoke([HumanMessage(content=agent_response)])
    print("LLM RECOMMENDATION:", recommendation.model_dump_json())
    return {"messages": [HumanMessage(content=recommendation.model_dump_json(), name="recommendation")]}


# Graph construction and workflow definition
# StateGraph manages agent workflow and routing
builder = StateGraph(AgentState)

# Register all agent nodes
builder.add_node("supervisor", supervisor_node)
builder.add_node("input_validation", input_validation_node)
builder.add_node("ashrae_lookup", ashrae_lookup_node)
builder.add_node("radiation_node", radiation_node)
builder.add_node("calculation", calculation_node)
builder.add_node("recommendation", recommendation_node)
builder.add_node("llm", llm_node)
builder.add_node("utility", utility_node)

# Define graph connection
builder.add_edge(START, "supervisor") # All workflows start at supervisor

# Each agent always reports back to the supervisor after completion
for member in members: 
    builder.add_edge(member, "supervisor")

# The supervisor populates the "next" field in the graph states which either routes to a node or finishes based on the state
builder.add_conditional_edges("supervisor", lambda state: state["next"]) # Pass the state and returns the key of the next state

# MemorySaver maintains data between agent call (# Short-term memory)
memory = MemorySaver() # Keeps track of building data and calculation results

# Compile graph with memory integration
graph = builder.compile(checkpointer=memory) 

# Draw the graph
#graph.get_graph(xray=True).draw_mermaid_png(output_file_path="graph.png")

# Database configuration and main loop
USE_DATABASE = False  # Toggle to True/False for database functionality
def main_loop():
    """
    Main interaction loop for command-line interface.
    Handles user input, database integration, and agent responses.
    """

    if USE_DATABASE:
        print("Welcome! Please enter your user ID")
        user_id = input("User ID: ")
        user_data = get_user_history(user_id)
    else:
        user_id = "test_user"
        user_data = None

    # Display existing building data if found in database
    if user_data:
        print(f"Welcome to your personal building performance engineer {user_id}!")
        print("Your existing building data has been found:")
        print(f"* Window area: {user_data['window_area']} ft²")
        print(f"* SHGC: {user_data['shgc']}")
        print(f"* U-value: {user_data['u_value']}")
        print(f"* City: {user_data['city']}")
        print("\nType 'go' to see your analysis, or enter new inputs to recalculate.")
    else:
        print("----INITIAL MESSAGE-----")
        print("Hello, I'm your personal building performance engineer. Please enter these inputs:")
        print("* Window area (ft²)")
        print("* SHGC value (0-1)")
        print("* U-value")
        print("* Building location (city)")

    while True:
        user_input = input(">> ")
        if user_input.lower() in ["exit", "quit", "q"]:
            print("See you Later. Have a great day!")
            break

        # Create new thread_id for processing each input
        thread_id = str(uuid.uuid4())  
        config = {"configurable": {"thread_id": thread_id}}   

        # Initialize the stream state with user input and user id
        stream_state = {
            "messages": [("user", user_input)],
            "next": "",
            "user_id": user_id if USE_DATABASE else None
        }
        # Add retrieved user data to the stream is available
        if user_data:
            for key, value in user_data.items():
                if key not in ['_id', 'user_id', 'created_at', 'timestamp']:
                    stream_state[key] = value

        # Process input through the agent network
        for state in graph.stream(stream_state, config=config):
            # Handle invalid input
            if 'input_validation' in state and "Valid input" not in state['input_validation']['messages'][0].content:
                    print("\n" + state['input_validation']['messages'][0].content + "\n")
                    break  #  breaks stream, returns to input loop
            
            # Display recommendations at the end when available
            if 'recommendation' in state:
                recs = json.loads(state['recommendation']['messages'][0].content)
                print("\n" + "\n".join(recs['recommendations']) + "\n")

# Run the main loop
if __name__ == "__main__":
    main_loop()