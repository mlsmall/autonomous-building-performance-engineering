from dotenv import load_dotenv
load_dotenv()
import json
import uuid

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage
from langgraph.graph.message import add_messages

from agents import llm_agent, research_agent, ashrae_lookup_agent, recommendation_agent, input_validation_agent
from tools import calculation_tool
from models import llm_gemini, llm_gpt
from schemas import AgentState, Recommendation, SupervisorState, members
from database import building_data, get_user_history

llm = llm_gpt # llm_gpt preferred

# system_prompt = (
#     f"""You are a supervisor tasked with managing a conversation between the following workers: {members}. 
#     Given the following user request, respond with the worker to act next. Each worker will perform a task and respond 
#     with their results and status. When finished, respond with FINISH.

#     1. Send all inputs to input_validation to check:
#         - SHGC (0-1)
#         - Window area (ft²)
#         - U-value
#         - City

#     2. After validation, send validated input to ashrae_lookup
#         - When you see ashrae_data in the state, route to utility to get local electricity rates

#     3. After utility rates are found:
#         - First route to calculation for proposed design (using user's U-value)
#         - Then route to calculation again for baseline design (using ASHRAE U-value)
#         - Both calculations must be complete before proceeding

#     4. Only after BOTH calculations are complete:
#         - Route to recommendation for comparison
#         - Then route to FINISH

#     Route to llm only for general building questions, never for calculations or data lookups.
#     """
# )

# THIS PROMPT WORKS
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

    3. After utility rates are found:
        - First route to calculation for proposed design (using user's U-value)
        - Then route to calculation again for baseline design (using ASHRAE U-value)
        - Both calculations must be complete before proceeding

    4. Only after BOTH calculations are complete:
        - Route to recommendation for comparison
        - Then route to FINISH

Route to llm only for general building questions, never for calculations or data lookups.
"""

# # Nodes
# # The supervisor is an LLM node that decides what node to execute next
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

# Supervisor node
def supervisor_node(state: AgentState) -> AgentState:
    print("\n=== SUPERVISOR NODE START ===")
    
    if USE_DATABASE:
        user_id = state.get('user_id')
        # Create user_data string if we have building data
        if any(key in state for key in ['city', 'window_area', 'shgc', 'u_value']):
            user_data = "Building data in state:\n"
            for key in ['city', 'window_area', 'shgc', 'u_value', 'baseline_cost', 'proposed_cost']:
                if key in state:
                    user_data += f"- {key}: {state[key]}\n"
        else:
            user_data = "No previous building data"
        
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

    # Store in MongoDB only if enabled
    if USE_DATABASE and state.get("user_id"):
        if next1 == "ashrae_lookup" or next1 == END:
            building_data(state["user_id"], state)

    print(f"Routing to: {next1}")
    print("=== SUPERVISOR NODE END ===\n")
    return {"next": next1}

def llm_node(state: AgentState) -> AgentState:
    result = llm_agent.invoke(state) # We're passing the state here to the "create_react_agent" 
    return {"messages": [HumanMessage(content=result["messages"][-1].content, name="llm_node")]}


def input_validation_node(state: AgentState) -> AgentState:
    result = input_validation_agent.invoke(state)
    # print("INPUT VALIDATION AGENT SAYS:\n", result['messages'][1].content)
    # If validation passes, parse and store values in state
    if "Valid input" in result["messages"][-1].content:
        user_input = state["messages"][0].content
        state["city"] = user_input.split("city =")[1].strip()
        state["window_area"] = int(user_input.split("window area =")[1].split("ft2")[0].strip().replace(",", ""))
        state["shgc"] = float(user_input.split("shgc =")[1].split()[0].strip())
        state["u_value"] = float(user_input.split("u-value =")[1].split("city")[0].strip())
        state["messages"] = [HumanMessage(content=result["messages"][-1].content, name="input_validation")]
    else:
        error_message = result["messages"][-1].content + "\nPlease enter your building details again:"
        state["messages"] = [HumanMessage(content=error_message, name="input_validation")]
        state["next"] = START  # Route back to start for new input
        
    return state

def ashrae_lookup_node(state: AgentState) -> AgentState:
    city = state["city"]
    city_message = HumanMessage(content=city)
    result = ashrae_lookup_agent.invoke({"messages": [city_message]})
    tool_message = result["messages"][2].content
    
    # Parse values
    to_value = tool_message.split("To=")[1].split("\n")[0].strip()
    cdd_value = tool_message.split("CDD=")[1].split("\n")[0].strip()
    zone_value = tool_message.split("Climate Zone=")[1].split("\n")[0].strip()
    u_value = tool_message.split("U-value=")[1].split("\n")[0].strip()
    shgc_value = tool_message.split("SHGC=")[1].strip()
    print("\nASHARE tool response values")
    print(f"To={to_value}\nCDD={cdd_value}\nClimate Zone={zone_value}\nU-value={u_value}\nSHGC={shgc_value}\n")
    
    # Store in state
    state["ashrae_to"] = float(to_value)
    state["ashrae_cdd"] = float(cdd_value)
    state["ashrae_climate_zone"] = int(zone_value)
    state["ashrae_u_factor"] = float(u_value)
    state["ashrae_shgc"] = float(shgc_value)

    state["messages"] = [HumanMessage(content=result["messages"][-1].content, name="ashrae_lookup")]
    
    return state

def utility_node(state: AgentState) -> AgentState:
    city = state["city"]
    query = f"Find an estimated value for the commercial utility rates ($/kWh) in {city}. \
        Please provide only a numeric estimated utility rate value without any additional text."
    result = research_agent.invoke({"messages": [HumanMessage(content=query)]})
    #print("UTILITY RESPONSE", result)
    
    # Store full response in messages
    state["messages"] = [HumanMessage(content=result["messages"][-1].content, name="utility")]
    
    # Extract and store just the value
    print("Extracted utility rate:", result["messages"][-1].content)
    state["utility_rate"] = float(result["messages"][-1].content)  # Get just the content
    
    return state

def calculation_node(state: AgentState) -> AgentState:
    # Set values based on whether it's proposed or baseline
    if "proposed_heat_gain" not in state:  # Check if key exists in state:
        #print("\n=== PROPOSED DESIGN CALCULATION ===")
        calculation_type = "proposed"
        shgc = state["shgc"]
        u = state["u_value"]
    else:
        #print("\n=== BASELINE DESIGN CALCULATION ===")
        calculation_type = "baseline"
        shgc = state["ashrae_shgc"]
        u = state["ashrae_u_factor"]

    # print(f"Using values:")
    # print(f"Area: {state['window_area']} ft²")
    # print(f"SHGC: {shgc}")
    # print(f"U-value: {u}")
    # print(f"To: {state['ashrae_to']}")
    # print(f"CDD: {state['ashrae_cdd']}")

    # Run calculations
    query = f"""
heat_gain = window_heat_gain(area={state["window_area"]}, SHGC={shgc}, U={u}, To={state["ashrae_to"]})
energy = annual_cooling_energy(heat_gain, {state["ashrae_cdd"]})
cost = annual_cost(energy, {state["utility_rate"]})
    """
    result = calculation_tool.invoke(query)

    # Parse the output from the calculation tool
    # Find 'Stdout:' in the result string
    stdout_index = result.find('Stdout:')
    
    # Extract everything after 'Stdout:'
    stdout = result[stdout_index + len('Stdout:'):].strip()
    
    # Split into lines and parse each line
    lines = stdout.split('\n')
    parsed_values = {}
    for line in lines:
        if '=' in line:
            key, value = line.split('=', 1)
            parsed_values[key.strip()] = float(value.strip())

    # Now parsed_values contains your heat_gain, annual_energy, and annual_cost
    heat_gain = parsed_values['heat_gain']
    annual_energy = parsed_values['annual_energy']
    annual_cost = parsed_values['annual_cost']
    

    # After calculation:
    # print(f"\nResults:")
    # print(f"Heat Gain: {heat_gain} BTU/hr")
    # print(f"Annual Energy: {annual_energy} kWh")
    # print(f"Annual Cost: ${annual_cost}")
    # print(f"\n=== {calculation_type} DESIGN CALCULATION END ===\n")

    # Store results
    if calculation_type == "proposed":
        state["proposed_heat_gain"] = heat_gain
        state["proposed_cooling_energy"] = annual_energy
        state["proposed_cost"] = annual_cost
    else:
        state["baseline_heat_gain"] = heat_gain
        state["baseline_cooling_energy"] = annual_energy
        state["baseline_cost"] = annual_cost

    state["messages"] = [HumanMessage(content=result, name="calculation")]
    
    return state

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
    """Analyzes performance differences between proposed and baseline values"""
    
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
    
    print("Input to the recommendation agent", message)
    result = recommendation_agent.invoke({"messages": [("user", message)]})
    agent_response = result["messages"][-1].content
    print("Recommendation schema input:", agent_response)
    recommendation = llm.with_structured_output(Recommendation).invoke([HumanMessage(content=agent_response)])
    #print("\nLLM OUTPUT:", recommendation)
    state["messages"] = [HumanMessage(content=recommendation.model_dump_json(), name="recommendation")]
    return state

# Build graph
builder = StateGraph(AgentState)

# Add nodes
builder.add_node("supervisor", supervisor_node)
builder.add_node("input_validation", input_validation_node)
builder.add_node("ashrae_lookup", ashrae_lookup_node)
builder.add_node("calculation", calculation_node)
builder.add_node("recommendation", recommendation_node)
builder.add_node("llm", llm_node)
builder.add_node("utility", utility_node)

# Add edges
builder.add_edge(START, "supervisor")

for member in members: # Each member always reports back to the supervisor when done
    builder.add_edge(member, "supervisor")

# The supervisor populates the "next" field in the graph states which routes to a node or finishes
builder.add_conditional_edges("supervisor", lambda state: state["next"]) # Pass the state and returns the key of the next state

# ADD SHORT TERM MEMORY
# Set the configuration needed for the state
#config = {"configurable": {"thread_id": "1"}} # passed to the StateGraph constructor to identiy our threads
memory = MemorySaver() # Checkpointer for short-term (within-thread) memory

# Compile graph with memory
graph = builder.compile(checkpointer=memory) # This is where the memory is integrated to the graph

# Draw the graph
#graph.get_graph(xray=True).draw_mermaid_png(output_file_path="graph.png")

USE_DATABASE = False  # Toggle to True/False to enable/disable database
def main_loop():
    if USE_DATABASE:
        print("Welcome! Please enter your email as your user ID")
        user_id = input("User ID: ")
        user_data = get_user_history(user_id)
    else:
        user_id = "test_user"
        user_data = None

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

        # INSIDE THE while True: LOOP (where you get user input)
        thread_id = str(uuid.uuid4())  # New unique ID each input
        config = {"configurable": {"thread_id": thread_id}}  # Use it here
        
        stream_state = {
            "messages": [("user", user_input)],
            "next": "",
            "user_id": user_id if USE_DATABASE else None
        }
        # Population the stream with values from the retrieved user data
        if user_data:
            for key, value in user_data.items():
                if key not in ['_id', 'user_id', 'created_at', 'timestamp']:
                    stream_state[key] = value

        for state in graph.stream(stream_state, config=config):
            i = 0
            if 'input_validation' in state and "Valid input" not in state['input_validation']['messages'][0].content:
                    print("I =", i, state['input_validation']['messages'])
                    i += 1
                    print("------------------------------------------------------")
                    print("\n" + state['input_validation']['messages'][0].content + "\n")
                    break  #  breaks stream, returns to input loop
            if 'recommendation' in state:
                recs = json.loads(state['recommendation']['messages'][0].content)
                print("\n" + "\n".join(recs['recommendations']) + "\n")

# Run the main loop
if __name__ == "__main__":
    main_loop()