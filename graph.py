from dotenv import load_dotenv
load_dotenv()
import json, os

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage

from agents import llm_agent, research_agent, ashrae_lookup_agent, recommendation_agent, input_validation_agent
from tools import calculation_tool
from models import llm_gemini, llm_gpt
from schemas import AgentState, Recommendation, SupervisorState, members
from database import building_data, get_user_history

llm = llm_gpt

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

system_prompt = f"""You are a supervisor tasked with managing a conversation between the following workers: {members}. 

For User ID: {{user_id}}
Status: {{status}}
{{previous_data}}

Given the following user request, respond with the worker to act next. Each worker will perform a task and respond 
with their results and status. When finished, respond with FINISH.

1. For new users or incomplete data, send all inputs to input_validation to check:
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

For existing users with complete data:
- Use stored values unless user specifically requests changes
- Allow updates to individual values without requiring complete revalidation
- Show previous analysis results if requested

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
    status = "EXISTING USER - Data Found" if state.get('existing_data') else "NEW USER - No Previous Data"
    previous_data = f'Previous Analysis Found: {state.get("existing_data")}' if state.get('existing_data') else 'No previous analysis available.'
    
    print("Formatting prompt with:", {  # Debug 2
        'user_id': state.get('user_id'),
        'status': status,
        'previous_data': previous_data
    })
    
    formatted_prompt = system_prompt.format(
        user_id=state.get('user_id'),
        status=status,
        previous_data=previous_data
    )

    messages = [{"role": "system", "content": formatted_prompt}] + state["messages"]
    response = llm.with_structured_output(SupervisorState).invoke(messages)

    
    next1 = response.next
    if next1 == "FINISH":
        next1 = END

    # Store in MongoDB at ASHRAE lookup and end of analysis
    if state.get("user_id"):
        print("Storing state in MongoDB...")  
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

    # If validation passes, parse and store values in state
    if "valid" in result["messages"][-1].content.lower():
        user_input = state["messages"][0].content
        state["city"] = user_input.split("city =")[1].strip()
        state["window_area"] = int(user_input.split("window area =")[1].split("ft2")[0].strip().replace(",", ""))
        state["shgc"] = float(user_input.split("shgc =")[1].split()[0].strip())
        state["u_value"] = float(user_input.split("u-value =")[1].split("city")[0].strip())
    
    state["messages"] = [HumanMessage(content=result["messages"][-1].content, name="input_validation")]
    
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
    
    # Store in state
    state["ashrae_to"] = float(to_value)
    state["ashrae_cdd"] = float(cdd_value)
    state["ashrae_climate_zone"] = int(zone_value)
    state["ashrae_u_factor"] = float(u_value)
    state["ashrae_shgc"] = float(shgc_value)

    state["messages"] = [HumanMessage(content=result["messages"][-1].content, name="ashrae_lookup")]
    
    return state

# def utility_node(state: AgentState) -> AgentState:
    # city = state["city"] # Get city from state
    # query = f"Find the current electricity utility rates ($/kWh) for {city}"
    # result = research_agent.invoke({"messages": [HumanMessage(content=query)]})
    # return {"messages": [HumanMessage(content=result["messages"][-1].content, name="utility")]}
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
        calculation_type = "proposed"
        shgc = state["shgc"]
        u = state["u_value"]
    else:
        calculation_type = "baseline"
        shgc = state["ashrae_shgc"]
        u = state["ashrae_u_factor"]

    # Run calculations
    query = f"""
heat_gain = window_heat_gain(area={state["window_area"]}, SHGC={shgc}, U={u}, To={state["ashrae_to"]})
energy = annual_cooling_energy(heat_gain, {state["ashrae_cdd"]})
cost = annual_cost(energy, {state["utility_rate"]})
    """
    print("CALCULATION TOOL query:", query)
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
    
    print('PARSED VALUES CHECK: Heat gain:', heat_gain, "annual energy", annual_energy, "annual cost", annual_cost)
    
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

# def recommendation_node(state: AgentState) -> AgentState:
#     # Prepare the input data for the recommendation_tool
#     print("STARTING TO ACCESS STATE VARIABLES")
#     query = {
#         "proposed_heat_gain": state["proposed_heat_gain"],
#         "baseline_heat_gain": state["baseline_heat_gain"],
#         "proposed_cooling_energy": state["proposed_cooling_energy"],
#         "baseline_cooling_energy": state["baseline_cooling_energy"],
#         "proposed_cost": state["proposed_cost"],
#         "baseline_cost": state["baseline_cost"],
#         "shgc": state["shgc"],
#         "ashrae_shgc": state["ashrae_shgc"],
#         "u_value": state["u_value"],
#         "ashrae_u_factor": state["ashrae_u_factor"],
#     }

#     # Convert the query to a string to pass to the agent
    
#     print("QUERY PROCESSED", query)
#     result = recommendation_agent.invoke({"messages": [("user", query)]})
#     agent_response = result["messages"][-1].content
#     print("REACT AGENT RESPONSE:", agent_response)  
#     recommendation = llm.with_structured_output(Recommendation).invoke([HumanMessage(content=agent_response)])
    
#     # Return the structured response
#     state["messages"] = [HumanMessage(content=recommendation.model_dump_json(), name="recommendation")]

#     return state

def recommendation_node(state: AgentState) -> AgentState:
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


    print("\n=== RECOMMENDATION NODE: Sending message to agent ===")
    result = recommendation_agent.invoke({"messages": [("user", message)]})
    agent_response = result["messages"][-1].content
    recommendation = llm.with_structured_output(Recommendation).invoke([HumanMessage(content=agent_response)])
    
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
config = {"configurable": {"thread_id": "1"}} # passed to the StateGraph constructor to identiy our threads
memory = MemorySaver() # Checkpointer for short-term (within-thread) memory

# Compile graph with memory
graph = builder.compile(checkpointer=memory) # This is where the memory is integrated to the graph

# Draw the graph
#graph.get_graph(xray=True).draw_mermaid_png(output_file_path="graph.png")

# Create a main loop
# def main_loop():
#     print("Welcome! Please enter your email as your user ID")
#     user_id = input("user ID: ")
#     existing_data = get_user_history(user_id)

#     print("----INITIAL MESSAGE-----")
#     print("Hello, I'm your building energy analyst. I need these inputs:")
#     print("* Window area (ft²)")
#     print("* SHGC value (0-1)")
#     print("* U-value")
#     print("* Building location (city)")

#     while True:
#         user_input = input(">> ")
#         if user_input.lower() in ["exit", "quit", "q"]:
#             print("See you Later. Have a great day!")
#             break

        
#         for state in graph.stream({"messages": [("user", user_input)], config=config):
#             print(state)
#             if 'recommendation' in state:
#                 recs = json.loads(state['recommendation']['messages'][0].content)
#                 print("\n" + "\n".join(recs['recommendations']) + "\n")

def main_loop():
    print("Welcome! Please enter your email as your user ID")
    user_id = input("User ID: ")
    existing_data = get_user_history(user_id)
    
    print("----INITIAL MESSAGE-----")
    print("Hello, I'm your building energy analyst. I need these inputs:")
    print("* Window area (ft²)")
    print("* SHGC value (0-1)")
    print("* U-value")
    print("* Building location (city)")

    while True:
        user_input = input(">> ")
        if user_input.lower() in ["exit", "quit", "q"]:
            print("See you Later. Have a great day!")
            break

        for state in graph.stream({
            "messages": [("user", user_input)],
            "next": "",
            "user_id": user_id,
            "existing_data": existing_data
        }, config=config): 
            print(state)
            if 'recommendation' in state:
                recs = json.loads(state['recommendation']['messages'][0].content)
                print("\n" + "\n".join(recs['recommendations']) + "\n")
# Run the main loop
if __name__ == "__main__":
    main_loop()
    
    # Add debug here to see state history
    # print("\n=== DEBUG: STATE HISTORY ===")
    # for state in graph.get_state_history(config):
    #     print("\nMessages:", len(state.values["messages"]))
    #     print("Last message:", state.values["messages"][-1].content if state.values["messages"] else "No messages")
    #     print("Next node:", state.next)
    #     print("-" * 80)