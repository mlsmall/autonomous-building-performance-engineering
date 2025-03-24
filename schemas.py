from langgraph.graph import MessagesState
from pydantic import BaseModel, Field
from typing import Literal

# This agent state is the input to each node in the graph
# Tracks all data through the process:
class AgentState(MessagesState):
    # The 'next' field indicates where to route to next
    next: str
    # Input data
    user_id: str = None 
    city: str = None
    window_area: float = None
    shgc: float = None
    u_value: float = None
    # ASHRAE data
    ashrae_to: float = None
    ashrae_cdd: float = None
    ashrae_climate_zone: int = None
    ashrae_u_factor: float = None
    ashrae_shgc: float = None
    # Utility data
    utility_rate: float = None
    # Solar radiation data
    radiation: float = None
    # Calculation results
    proposed_total_heat_gain: float = None
    proposed_cooling_energy: float = None
    proposed_cost: float = None
    baseline_total_heat_gain: float = None
    baseline_cooling_energy: float = None
    wall_area: float = None # Add wall area
    wall_u_value: float = None # Add wall u-value
    wall_heat_gain: float = None # Add wall heat gain
    baseline_cost: float = None

# Validates user input
class BuildingInput(BaseModel): 
    window_area: float = Field(gt=0, description="Window area in ft²")
    shgc: float = Field(gt=0, lt=1.1, description="Solar Heat Gain Coefficient")
    u_value: float = Field(gt=0, lt=20, description="The u-value must be between 0 and 20")
    city: str = Field(description="It MUST be the name of a city from anywhere in the world."
        "It must NOT be a country, province, state, fruit, animal, plant, or vegtable")
    )
    wall_area: float = Field(gt=0, description="Wall area in ft²")
    wall_u_value: float = Field(gt=0, lt=20, description="The wall u-value must be between 0 and 20")
            

# class Recommendation(BaseModel):
#     """Structure for window performance comparison"""
#     performance_delta: float = Field(description="Percentage difference from baseline")
#     recommendations: list[str] = Field(description="List of formatted recommendations that MUST follow this format: \
#         First line: '<span style='color: #1a237e; font-size: 1.0em;'>Your glass choice means:</span>\n' \
#         Then bullet points showing the diffs (if diff is negative, show red '↓' and 'more', if positive show green ✓ and 'less'): \
#         &emsp; <span style='color: {'#d32f2f' if diff < 0 else '#43a047'}' > {'↓' if diff < 0 else '✓'}</span> &nbsp; &nbsp; {abs(diff):,.0f} {'more' if diff < 0 else 'less'} BTU/hr heat gain\n \
#         &emsp; <span style='color: {'#d32f2f' if diff < 0 else '#43a047'}' > {'↓' if diff < 0 else '✓'}</span> &nbsp; &nbsp;{abs(diff):,.0f} {'more' if diff < 0 else 'less'} kWh/year\n \
#         &emsp; <span style='color: {'#d32f2f' if diff < 0 else '#43a047'}' > {'↓' if diff < 0 else '✓'}</span> &nbsp; &nbsp; ${abs(diff):,.2f} {'more' if diff < 0 else 'less'} in cooling costs\n \
#         Your energy performance is {abs(performance_delta):.1f}% {'less' if performance_delta < 0 else 'better'} than the baseline.")

# class Recommendation(BaseModel):
#     """Structure for window performance comparison"""
#     performance_delta: float = Field(description="Percentage difference from baseline")
#     recommendations: list[str] = Field(description="""List of formatted recommendations:
#         <span style='color: #1a237e; font-weight: 600; font-size: 1.1em; display: block; margin: 0px; padding: 0px; line-height: 1;'>PERFORMANCE ANALYSIS</span>
#         <div style='border-bottom: 1px solid #dee2e6; width: 200px; margin: 15px 0; padding: 0px;'></div>
#         &emsp; <span style='display: inline-block; width: 120px;'>Peak Heat Gain</span> <span style='color: {'#43a047' if heat_gain_diff < 0 else '#d32f2f'}'>{'✓' if heat_gain_diff < 0 else '↓'}</span> &nbsp; &nbsp; {abs(heat_gain_diff):,.0f} {'less' if heat_gain_diff < 0 else 'more'} BTU/hr
#         &emsp; <span style='display: inline-block; width: 120px;'>Energy Usage</span> <span style='color: {'#43a047' if energy_diff < 0 else '#d32f2f'}'>{'✓' if energy_diff < 0 else '↓'}</span> &nbsp; &nbsp; {abs(energy_diff):,.0f} {'less' if energy_diff < 0 else 'more'} kWh/year
#         &emsp; <span style='display: inline-block; width: 120px;'>Cooling Costs</span> <span style='color: {'#43a047' if cost_diff < 0 else '#d32f2f'}'>{'✓' if cost_diff < 0 else '↓'}</span> &nbsp; &nbsp; ${abs(cost_diff):,.2f} {'less' if cost_diff < 0 else 'more'}
#         <div style='margin-top: 16px;'>Overall Performance: &nbsp;<span style='color: {'#43a047' if performance_delta < 0 else '#b71c1c'}'>{abs(performance_delta):.1f}%</span>&nbsp;{'better' if performance_delta < 0 else 'worse'} than baseline</div>""")

class Recommendation(BaseModel):
    """Structure for window performance comparison"""
    performance_delta: float = Field(description="Percentage difference from baseline")
    recommendations: list[str] = Field(description="""List of formatted output that MUST follow this format:
    heat_gain_diff: float = Field(description="Proposed - Baseline heat gain difference")
    energy_diff: float = Field(description="Proposed - Baseline energy difference")
    cost_diff: float = Field(description="Proposed - Baseline cost difference")""")
    
members = ["llm", "input_validation", "ashrae_lookup", "calculation", "recommendation", "utility", "radiation_node"] # Current Agents
options = members + ["FINISH"]

# Our team supervisor is an LLM node. It picks the next agent to process and decides when the work is completed
class SupervisorState(BaseModel): # This is a Pydantic class that returns a literal
    """Worker to route to next. If no workers are needed, route to FINISH"""
    next: Literal[*options] # type: ignore 
