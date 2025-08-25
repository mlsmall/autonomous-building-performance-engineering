"""
Multi-agent orchestration using LangGraph.
Manages agent workflow, state, and interactions for building performance analysis.
"""

from dotenv import load_dotenv
load_dotenv()
import json, uuid, re

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage

from core_engine.tools import calculation_tool, radiation_tool, ashrae_lookup_tool, tavily_tool, ASHRAE_VALUES
from models import llm_gpt_4o, llm_mistral, llm_gemini_25, llm_gemini_20
from schemas import AgentState, SupervisorState, members, BuildingInput

USE_DATABASE = False  # Or True if you want to use the database

if USE_DATABASE:
    from database import building_data, get_user_history
else:
    building_data = None
    def get_user_history(*args, **kwargs):
        return None

llm = llm_gpt_4o

# Supervisor agent system prompt
system_prompt = f"""You are a supervisor tasked with managing a conversation between the following workers: {members}.

For User ID: {{user_id}}
{{user_data}}

Given the following user request, respond with the worker to act next. Each worker will perform a task and respond 
with their results and status. When finished, respond with END.

If user_data contains building information:
    - Use those values for calculations
    - Skip asking for inputs we already have
    - If baseline and proposed values exist, then route to recommedation for comparison

If user_data indicates no previous building data exists:
    1. Send all inputs to input_validation to check:
        - SHGC (0-1)
        - Window area (ft²)
        - Glass u-value
        - Wall area (ft²)
        - Wall U-value
        - City

    2. If you see "Valid input" message from input_validation, route to ashrae_lookup
        - When you see ashrae_to in the state, route to utility to get local electricity rates
        - When you see utility_rate in the state, route to radiation_node to get the solar radiation value

    3. When you see radiation in the state:
        - If proposed_total_heat_gain is NOT in state, route to calculation for proposed calculations
        - If proposed_total_heat_gain is in state but baseline_total_heat_gain is NOT in state, route to calculation for baseline calculations
        - If BOTH proposed_total_heat_gain AND baseline_total_heat_gain are in state, route to recommendation

    4. After recommendation is complete:
        - Route to END

    5. After recommendations are shown:
        - STOP
        - Wait for the user to write a message or question
        - Route to llm to answer questions or messages
        - After llm responds, route to END and wait for user input again
"""

# The supervisor decides what node to execute next - orchestrator
def supervisor_node(state: AgentState) -> AgentState:
    
    # Stop after recommendation
    if len(state["messages"]) > 0 and state["messages"][-1].name == "recommendation":
        return {"next": END}
    
     # Check if we just came from llm - if so, wait for user input
    if len(state["messages"]) > 0 and state["messages"][-1].name == "llm":
        return {"next": END}  # Wait for user input after answering a question
    
    # Force baseline calculation if proposed exists
    if 'proposed_total_heat_gain' in state and 'baseline_total_heat_gain' not in state:
        return {"next": "calculation"}  
    
    #  user_data string with current state data
    user_data = "Current state data:\n"
    for key, value in state.items():
        if key not in ['messages', 'next', 'user_id']:
            user_data += f"- {key}: {value}\n"
    
    if USE_DATABASE:
        user_id = state.get('user_id')
    else:
        user_id = "N/A"
    
    # Feed dynamic data to the system prompt
    user_data_prompt = system_prompt.format(
        user_id=user_id,
        user_data=user_data if user_data != "Current state data:\n" else "No previous building data available."
    )

    # print("=== SUPERVISOR ACTUAL PROMPT ===")
    # print(formatted_prompt)
    # print("=== END SUPERVISOR PROMPT ===")

    # Pass the state data to the supervisor
    messages = [{"role": "system", "content": user_data_prompt}] + state["messages"]
    response = llm.with_structured_output(SupervisorState).invoke(messages)

    if response is None:
    # Fallback: assume free-form user question-> send to LLM node
        return {"next": "llm"}

    next1 = response.next
    
    # Store building data in MongoDB if enabled
    if USE_DATABASE and state.get("user_id"):
        if next1 == "ashrae_lookup" or next1 == END:
            building_data(state["user_id"], state)

    print(f"Routing to: {next1}")
    print("=== SUPERVISOR NODE END ===\n")
    return {"next": next1}


def input_validation_node(state: AgentState) -> AgentState:
    """
    Validates building input data against the rules specified in the class BuildingInput.
    Returns error state if validation fails, which triggers the user to re-input values.
    """
    if 'proposed_cost' in state:  # Prevent re-validation after analysis
        return {"next": "llm"}
    
    validation_input = state['messages'][-1].content
    print("INPUT VALIDATION RECEIVED:", validation_input)
    
    # Direct LLM validation
    import json
    schema = BuildingInput.model_json_schema()
    schema_str = json.dumps(schema, indent=2)
    
    prompt = f"""You are an input validator. Check if this input is valid:

Input: {validation_input}

Validation schema:
{schema_str}

If all values are valid, respond with exactly: "Valid input"
If any values are invalid, respond with: "Invalid input: [specific reason]"

Be precise and check the actual numbers against the schema rules."""

    # print("=== Validation PROMPT SENT TO LLM ===")
    # print(prompt)
    # print("=== END PROMPT ===")
    
    validation_result = llm.invoke(prompt)
    result = {"output": validation_result.content}
    # print("VALIDATION NODE OUTPUT", result.get("output"))
    

    if "Valid input" in result.get("output", ""):
        user_input = state["messages"][0].content
        # Extract and convert input values to appropriate types if necessary
        return {
            "city": re.search(r'city\s*=\s*([^=\n]+?)(?=\s*(?:wall|window|shgc|u-value|$))', user_input).group(1).strip(),
            "window_area": int(re.search(r'window\s+area\s*=\s*([\d,]+)\s*ft2\b', user_input).group(1).replace(",", "")),
            "shgc": float(re.search(r'shgc\s*=\s*(\d*\.?\d+)', user_input).group(1)),
            "glass_u_value": float(re.search(r'glass\s+u-?value\s*=\s*(\d*\.?\d+)(?=\s|$)', user_input).group(1)),
            "wall_area": int(re.search(r'wall\s+area\s*=\s*([\d,]+)\s*ft2\b', user_input).group(1).replace(",", "")),
            "wall_u_value": float(re.search(r'wall\s+u-?value\s*=\s*(\d*\.?\d+)', user_input).group(1)),
            "messages": [HumanMessage(content=result.get("output", ""), name="input_validation")]
        }
                            
    else:
        error_message = f'{result.get("output", "Invalid input")}  \nPlease enter it again:'
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
    # tool_message = ashrae_lookup_tool.invoke(city)

    data = ASHRAE_VALUES["Montreal"]  # Hardcoded data for testing
    tool_message = (
        f"To={data['To']}\n"
        f"CDD={data['CDD10']}\n"
        f"Climate Zone={data['zone']}\n"
        f"U-value={data['glass_u_factor']}\n"
        f"SHGC={data['shgc']}\n"
        f"Wall-U-Value={data['wall_u_value']}"
    )

    # Validate and extract ASHRAE values
    if "To=" in tool_message  and "CDD=" in tool_message :
        return {
            "ashrae_to": float(tool_message.split("To=")[1].split("\n")[0].strip()),
            "ashrae_cdd": float(tool_message.split("CDD=")[1].split("\n")[0].strip()),
            "ashrae_climate_zone": tool_message.split("Climate Zone=")[1].split("\n")[0].strip(),
            "ashrae_glass_u": float(tool_message.split("U-value=")[1].split("\n")[0].strip()),
            "ashrae_shgc": float(tool_message.split("SHGC=")[1].split("\n")[0].strip()),
            "ashrae_wall_u": float(tool_message.split("Wall-U-Value=")[1].strip()),
            "messages": [HumanMessage(content=tool_message, name="ashrae_lookup")]
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
    
    match = re.search(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", str(result))
    radiation_value = float(match.group(0)) if match else 0.0

    print("RADIATION NODE RESULT", result)
    return {
        "radiation": radiation_value,
        "messages": [HumanMessage(content=str(radiation_value), name="radiation")]
    }


def utility_node(state: AgentState) -> AgentState:
    """
    Gets local utility rates for cost calculations.
    """
    city = state["city"]

    # Format query to get only numeric rate value
    query = f"Find an estimated value for the commercial utility rates ($/kWh) in {city}. \
        Please provide only a numeric estimated utility rate value without any additional text. \
        If no utility rate is available, please return '0.1'."
    
    # result = tavily_tool.invoke(input_value={"messages": [HumanMessage(content=query)]}, input_type=dict)

    content_raw = "0.1"  # Hardcoded for testing
    
    # Extract first numeric value
    match = re.search(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", content_raw)
    content = match.group(0) if match else "0.1"

    return {
        "utility_rate": float(content),
        "messages": [HumanMessage(content=content, name="utility")]
    }

def calculation_node(state: AgentState) -> AgentState:
    """
    Performs building performance calculations for both proposed and baseline cases.
    Currently calculates heat gain, energy use, and operating costs using ASHRAE data.
    """

    # Determine if calculating proposed or baseline case
    if "proposed_total_heat_gain" not in state: 
        calculation_type = "proposed"
        shgc = state["shgc"]
        glass_u_value = state["glass_u_value"]
        wall_u_value = state["wall_u_value"]
    else:
        calculation_type = "baseline"
        shgc = state["ashrae_shgc"]
        glass_u_value = state["ashrae_glass_u"]
        wall_u_value = state["ashrae_wall_u"]

    # Format the calculation query and pass the values
    query = f"""
glass_heat_gain = window_heat_gain(area={state["window_area"]}, SHGC={shgc}, glass_u_value={glass_u_value}, To={state["ashrae_to"]}, radiation={state["radiation"]})
wall_heat_gain = wall_heat_gain(wall_area={state["wall_area"]}, U={wall_u_value}, To={state["ashrae_to"]})
total_heat = total_heat_gain(glass_heat_gain, wall_heat_gain)
energy = annual_cooling_energy(total_heat, {state["ashrae_cdd"]})
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
    print(calculation_type, "CALCULATION PARSED VALUES", parsed_values)
    # Return results with appropriate prefix (baseline/proposed)
    key_prefix = "baseline" if calculation_type == "baseline" else "proposed"

    return {
        f"{key_prefix}_total_heat_gain": parsed_values["total_heat_gain"],
        f"{key_prefix}_cooling_energy": parsed_values["annual_energy"],
        f"{key_prefix}_cost": parsed_values["annual_cost"],
        f"{key_prefix}_glass_heat_gain": parsed_values["glass_heat_gain"],
        f"{key_prefix}_wall_heat_gain": parsed_values["wall_heat_gain"],
        "messages": [HumanMessage(content=result, name="calculation")]
    }

def recommendation_node(state: AgentState) -> AgentState:
    """
    Analyzes performance differences between proposed and baseline values
    Generates and returns formatted recommendations based on energy and cost comparisons.
    """
    # Direct calculation without ReAct agent
    import json
    
    # Calculate differences as (Proposed - Baseline)
    heat_gain_diff = state['proposed_total_heat_gain'] - state['baseline_total_heat_gain']
    energy_diff = state['proposed_cooling_energy'] - state['baseline_cooling_energy']
    cost_diff = state['proposed_cost'] - state['baseline_cost']
    performance_delta = ((state['proposed_cost'] - state['baseline_cost']) / state['baseline_cost']) * 100

    # Create recommendation JSON directly
    recommendation_data = {
        "performance_delta": performance_delta,
        "recommendations": [
            f"heat_gain_diff: {heat_gain_diff}",
            f"energy_diff: {energy_diff}", 
            f"cost_diff: {cost_diff}"
        ]
    }
    
    return {
        "messages": [HumanMessage(content=json.dumps(recommendation_data), name="recommendation")]
        }

def llm_node(state: AgentState) -> AgentState:
    """
    General-purpose LLM agent for handling non-technical queries and post-analysis conversation.
    Provides answers about building performance based on state data.
    """
    # Create a context with all the building data from the state
    building_context = "Building Analysis Data:\n"
    
    # Dynamically add all relevant state data to the context
    for key, value in state.items():
        # Skip non-data fields and empty values
        if key not in ["messages", "next"] and value is not None:
            # Format the key for better readability
            formatted_key = key.replace('_', ' ').title()
            building_context += f"- {formatted_key}: {value}\n"

    # Create enhanced system message with building context
    enhanced_system_message = f"""You are a highly-trained building performance analyst. 
    You can provide the user with information about their building's energy performance.
    You have access to the following building data and analysis results:
    {building_context}
    Please keep the answer concise.
    """
    # print("ENHANCED SYSTEM MESSAGE", enhanced_system_message)
    user_question = state["messages"][-1].content
    print("USER QUESTION:", user_question)
    
    enhanced_messages = [{"role": "system", "content": enhanced_system_message}, 
                         {"role": "user", "content": user_question}]

    result = llm.invoke(enhanced_messages)
    llm_output = result.content

    return {
        "messages": [HumanMessage(content=llm_output, name="llm")],
        "next": END 
        }  
   

# StateGraph manages agent workflow and routing
builder = StateGraph(AgentState)

# Register all agent nodes
builder.add_node("supervisor", supervisor_node)
builder.add_node("input_validation", input_validation_node)
builder.add_node("ashrae_lookup", ashrae_lookup_node) # Energy code Lookup
builder.add_node("radiation_node", radiation_node) # Radiation data lookup
builder.add_node("calculation", calculation_node)
builder.add_node("recommendation", recommendation_node)
builder.add_node("utility", utility_node)
builder.add_node("llm", llm_node)


# Define graph connection
builder.add_edge(START, "supervisor") # All workflows start at supervisor

# Each agent reports back to the supervisor after completion
for member in members:
    builder.add_edge(member, "supervisor")

# The supervisor populates the "next" field in the graph states which either routes to a node or finishes based on the state
builder.add_conditional_edges("supervisor", lambda state: state["next"]) # Pass the state and returns the key of the next state

# MemorySaver maintains data between agent calls (# Short-term memory)
memory = MemorySaver()

# Compile graph with memory integration
graph = builder.compile(checkpointer=memory) 

# Database configuration and main loop
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
        print(f"* glass u-value: {user_data['glass_u_value']}")
        print(f"* Wall area: {user_data['wall_area']} ft²")
        print(f"* Wall u-value: {user_data['wall_u_value']}")
        print(f"* City: {user_data['city']}")
        print("\nType 'go' to see your analysis, or enter new inputs to recalculate.")
    else:
        print("----INITIAL MESSAGE-----")
        print("Hello, I'm your personal building performance engineer. Please enter these inputs:")
        print("* Window area (ft²)")
        print("* SHGC value (0-1)")
        print("* glass u-value")
        print("* Wall area (ft²)")
        print("* Wall u-value")
        print("* Building location (city)")

    thread_id = str(uuid.uuid4())  
    
    while True:
        user_input = input(">> ")
        if user_input.lower() in ["exit", "quit", "q"]:
            print("See you Later. Have a great day!")
            break

        # Create new thread_id for processing each input
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
                # thread_id = str(uuid.uuid4())  # Reset thread_id for new input
                break  # breaks stream, returns to input loop

            # Display recommendations at the end when available
            if 'recommendation' in state:
                recs = json.loads(state['recommendation']['messages'][0].content)
                print("\n" + "\n".join(recs['recommendations']) + "\n")
                print("\nYou can now ask questions about your building's performance. Type 'exit', 'quit', or 'q' to quit.")

            if "llm" in state:
                print("BPA:", state["llm"]["messages"][0].content)
                

# Run the main loop
if __name__ == "__main__":
    main_loop()
