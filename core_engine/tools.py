import json
from dotenv import load_dotenv

load_dotenv()

import matplotlib
from typing import Annotated
from langchain_core.tools import tool
import matplotlib
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_experimental.utilities import PythonREPL

from schemas import BuildingInput
from models import llm_gemini, llm_gpt, llm_mistral
from core_engine.ashrae_data import ASHRAE_VALUES
from corrective_rag import retrieve, generate
from radiation_rag import rad_generate, rad_retrieve

llm = llm_gpt

# Create a tool to call the LLM model
@tool
def llm_tool(query: Annotated[str, "The query to search for."]):
    """ A tool to call an LLM model to search for a query"""
    try:
        result = llm.invoke(query)
    except BaseException as e:
        return f"Failed to execute. Error: {e}"
    return result.content


repl = PythonREPL()
@tool
def python_repl_tool(code: Annotated[str, "The code to execute user instructions such as perform calculations or create charts"]):
    """Use this tool to execute Python code and do math. If you want to see the output of a value,
    you should print it out with 'print(...)'. This is visible to the user.""
    If you need to save a plot, you should save it to the ./ folder. Assume default values for charts and plots.
    If the user has not indicated a preference, make an assumption and create the plot. Do no use a sandboxed environment.
    Write the files to the ./ folder residing in the current folder.
    
    Clean the data provided before plotting a chart. If arrays are of unequal length, substitute missing data points with 0
    or the average of the array.
    
    Example:
    Do not save the plot to (sandbox:/plot.png) but to (./plot.png)

    Example:
    ``` 
    from matplotlib import pyplot as plt
    plt.savefig("./data/foo.png")
    ```
    """
    try:
        matplotlib.use('agg')
        result = repl.run(code) # The code is generated by the llm
    except BaseException as e:
        return f"Failed to execute. Error: {repr(e)}"
    
    result_str = f"Succesfully executed :\n```python\n{code}\nStdout: {result}"
    return result_str

tavily_tool = TavilySearchResults(max_results=3, search_depth="advanced")

# Input Validation Tool
@tool
def input_validation_tool(query: Annotated[str, "Check if all required inputs are present and valid"]):
    """Validates if SHGC, window area, U-value, and city are provided and valid"""
    try:
        result = llm.invoke(
            f"""Extract and validate these values from the input:
            Input: {query}

            Check that they match these rules: {BuildingInput.model_json_schema()}
            """
        )
        return result.content
    
    except Exception as e:
        return f"Error in validation: {str(e)}"
    
@tool
def ashrae_lookup_tool(city: Annotated[str, "Returns the data value for Montreal"]):
    """No matter what city is input. Returns ASHRAE values for Montreal."""
    data = ASHRAE_VALUES["Montreal"]
    return f"To={data['To']}\nCDD={data['CDD10']}\nClimate Zone={data['zone']}\nU-value={data['u_factor']}\nSHGC={data['shgc']}"

def ashrae_lookup_tool(city: Annotated[str, "Look up specific ASHRAE data"]):
    """Uses RAG to find ASHRAE information from validated input"""
    try:
        print("CITY:", city)
        # Use the existing retrieve and generate functions directly
        # 1. Temperature and CDD lookup
        climate_query = (
        f"What is the cooling design temperature (To) and cooling degree days (CDD10) \
        in {city} according to ASHRAE Table D Climate Design Data? \
        Please provide only the numeric values in the format: \
        To = [value] \
        CDD10 = [value]"
        )

        state = {"question": climate_query}
        climate_result = generate(retrieve(state))
        to_value = climate_result['generation'].split('To =')[1].split('\n')[0].strip()
        cdd_value = climate_result['generation'].split('CDD10 =')[1].strip()
        print("To:", to_value)
        print("CDD:", cdd_value)

        # 2. Climate Zone lookup
        climate_zone_query = (
        f"In Table B1 International Climate Zone Definitions, what is the climate zone number for {city}? \
        Please provide only the numeric climate zone value without any additional text."
        )
        state = {"question": climate_zone_query}
        zone_result = generate(retrieve(state))
        # Extract just the number from something like "Montreal Dorval International A is climate zone 6"
        zone_number = zone_result['generation'].split("zone")[-1].strip().rstrip('.')
        print("ZONE RESULT:", zone_number)

        # 3. ufactor_query lookup
        ufactor_query = (
        f"What is the U-factor for Vertical Fenestration 0%–40% of Wall for Nonmetal framing \
        in climate zone {zone_number} according to Building Envelope Requirements? \
        Please provide only the numeric U-factor value without any additional text."
        )
        state = {"question": ufactor_query}
        ufactor_result = generate(retrieve(state))
        u_value = ufactor_result['generation'].split("U-")[-1].split('.')[0].strip()
        print("U-FACTOR:", u_value)

        # 4. SHGC_query lookup
        shgc_query = (
        f"What is the SHGC for Vertical Fenestration 0%–40% of Wall (for all frame types) \
        in climate zone {zone_number} according to Building Envelope Requirements? \
        Please provide only the numeric SHGC value without any additional text."
        )
        state = {"question": shgc_query}
        shgc_result = generate(retrieve(state))
        shgc_value = shgc_result['generation']
        print("SHGC:", shgc_value)

        return f"To={to_value}\nCDD={cdd_value}\nClimate Zone={zone_number}\nU-value={u_value}\nSHGC={shgc_value}"

    except Exception as e:
        return f"Error in ASHRAE lookup: {str(e)}"

@tool
def radiation_tool(city: Annotated[str, "Look up specific solar radiation data"]):
    """Uses RAG to find solar radiation values from a given city"""
    try:
        query = (
        f"What is the solar radiation for {city}? \
        Please provide only the numeric value without any additional text."
        ) 
        documents = rad_retrieve(query)
        result = rad_generate(query, documents)
        
        return result

    except Exception as e:
        return f"Error in solar radiation lookup: {str(e)}"

@tool
def calculation_tool(query: Annotated[str, "Execute building energy calculations using provided values"]):
    """Performs building energy calculations"""
    try:
        calc_code = f"""
# Building Energy Calculation Formulas
def window_heat_gain(area, SHGC, glass_u_value, To, radiation):
    TD = (To*1.8 + 32) - 70 # Converting To from Celsius to Fahrenheit
    # radiation is given in KWh/m^2/day, convert to W/m^2, then everything to BTU/hr
    Q_solar = area * SHGC * radiation * 41.67 * 0.003412
    # U is in W/(m^2 * Kelvin) in Ashrae table. Convert to BTU/(hr * ft^2 * Fahrenheit)
    Q_conduction = glass_u_value * 0.1761 * area * TD
    return Q_solar + Q_conduction

def wall_heat_gain(wall_area, U, To):
    TD = (To*1.8 + 32) - 70 # Converting To from Celsius to Fahrenheit
    Q_wall_cond = U * 0.1761 * wall_area * TD # BTU/hr
    return Q_wall_cond

def total_heat_gain(glass_heat_gain, wall_heat_gain):
    total_heat = glass_heat_gain + wall_heat_gain
    return total_heat

def annual_cooling_energy(Q, CDD):
    # Convert peak load to annual energy use
    annual_energy = Q * CDD * 24 * (1/12000) * 0.85
    return annual_energy

def annual_cost(annual_energy, rate):
    cost = annual_energy * rate
    return cost
    

{query}

print(f"total_heat_gain={{total_heat}}")
print(f"annual_energy={{energy}}") # kWh/year
print(f"annual_cost={{cost}}")

"""
        result = python_repl_tool.invoke(calc_code)
        return result
    
    except Exception as e:
        return f"Error in calculations: {str(e)}"
    
# @tool
# def recommendation_tool(query: Annotated[str, "Compare building performance and provide recommendations"]):
#     """Analyzes performance differences between proposed and baseline values"""
#     try:
#         return f"""
#         Based on the analysis of:

#         Proposed vs Baseline:
#         Heat Gain: {query["proposed_heat_gain"]} vs {query["baseline_heat_gain"]} BTU/hr
#         Annual Energy: {query["proposed_cooling_energy"]} vs {query["baseline_cooling_energy"]} kWh/year
#         Annual Cost: ${query["proposed_cost"]} vs {query["baseline_cost"]}

#         ASHRAE Requirements:
#         SHGC: {query["shgc"]} vs required {query["ashrae_shgc"]}
#         U-Factor: {query["glass_u_value"]} vs required {query["ashrae_glass_u"]}

#         Calculate percentage differences between proposed and baseline values.
#         Analyze ASHRAE compliance and provide specific recommendations for improvement.
#         """
    
#     except Exception as e:
#         return f"Error formatting data: {str(e)}"



@tool
def recommendation_tool(query: Annotated[str, "Compare building performance and provide recommendations"]):
    """Analyzes performance differences between proposed and baseline values."""
    
    try:
        lines = query.strip().split('\n')
        data = {}
        for line in lines:
            key, value = line.strip().split(': ')
            data[key] = float(value)
        
        # heat_gain_diff = data['baseline_heat_gain'] - data['proposed_heat_gain']
        # energy_diff = data['baseline_cooling_energy'] - data['proposed_cooling_energy']
        # cost_diff = data['baseline_cost'] - data['proposed_cost']
        # performance_delta = ((data['baseline_cost'] - data['proposed_cost']) / data['baseline_cost']) * 100

        # Calculate differences as (Proposed - Baseline)
        heat_gain_diff = data['proposed_heat_gain'] - data['baseline_heat_gain']
        energy_diff = data['proposed_cooling_energy'] - data['baseline_cooling_energy']
        cost_diff = data['proposed_cost'] - data['baseline_cost']
        performance_delta = ((data['proposed_cost'] - data['baseline_cost']) / data['baseline_cost']) * 100

        print("Recommendation tool results")
        print(f"Heat Gain difference: {heat_gain_diff} BTU/hr")
        print(f"Annual Energy difference: {energy_diff} kWh/year")
        print(f"Annual Cost difference: ${cost_diff}")
        print(f"Performance delta: {performance_delta}%")

        return json.dumps({
            "heat_gain_diff": heat_gain_diff,
            "energy_diff": energy_diff,
            "cost_diff": cost_diff,
            "performance_delta": performance_delta
        })
    
    except Exception as e:
        return f"Error in recommendations: {str(e)}"
