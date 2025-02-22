from langgraph.graph import MessagesState
from pydantic import BaseModel, Field, model_validator
from typing import Literal

# This agent state is the input to each node in the graph
# Ttracks all data through the process:
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
    # Calculation results
    proposed_heat_gain: float = None
    proposed_cooling_energy: float = None
    proposed_cost: float = None
    baseline_heat_gain: float = None
    baseline_cooling_energy: float = None
    baseline_cost: float = None

# Validates user input
class BuildingInput(BaseModel): 
    window_area: float = Field(gt=0, description="Window area in ft²")
    shgc: float = Field(gt=0, lt=1, description="Solar Heat Gain Coefficient")
    u_value: float = Field(gt=0, lt=20, description="u-value")
    city: str = Field(description=(
        "It MUST be the name of a city from anywhere in the world."
        "It must NOT be a country, province or state")
    )
                       


# class Recommendation(BaseModel):
#     """Structure for window performance comparison"""
#     performance_delta: float = Field(description="Percentage difference from baseline")
#     recommendations: list[str] = Field(description="List of formatted recommendations that MUST follow this format: \
#         First line: 'Your glass choice means:' \
#         Then bullet points showing the diffs (negative diff means proposed value is higher than baseline): \
#         * {abs(diff):,.0f} {'more' if diff < 0 else 'less'} BTU/hr heat gain &nbsp; &emsp; <span style='color: #43a047'>✓</span>\n \
#         * {abs(diff):,.0f} {'more' if diff < 0 else 'less'} kWh/year &nbsp; &emsp; &emsp; <span style='color: #43a047'>✓</span>\n \
#         * ${abs(diff):,.2f} {'more' if diff < 0 else 'less'} in cooling costs &emsp; <span style='color: #43a047'>✓</span>\n \
#         Performance is {abs(performance_delta):.1f}% {'less' if performance_delta < 0 else 'better'} than baseline.")
    
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

class Recommendation(BaseModel):
    """Structure for window performance comparison"""
    performance_delta: float = Field(description="Percentage difference from baseline")
    recommendations: list[str] = Field(description="List of formatted recommendations that MUST follow this format: \
        First line: '<span style='color: #1a237e; font-weight: 600; font-size: 1.1em; display: block; margin: 0px; padding: 0px; line-height: 1;'>PERFORMANCE ANALYSIS</span>\
        <div style='border-bottom: 1px solid #dee2e6; width: 200px; margin: 12px; padding: 0px;'></div>\
        &emsp; <span style='display: inline-block; width: 120px;'>Heat Gain</span> <span style='color: {'#43a047' if diff > 0 else '#d32f2f'}'>{'✓' if diff > 0 else '↓'}</span> &nbsp; &nbsp; {abs(diff):,.0f} {('less' if diff > 0 else 'more')} BTU/hr\n \
        &emsp; <span style='display: inline-block; width: 120px;'>Energy Usage</span> <span style='color: {'#43a047' if diff > 0 else '#d32f2f'}'>{'✓' if diff > 0 else '↓'}</span> &nbsp; &nbsp; {abs(diff):,.0f} {('less' if diff > 0 else 'more')} kWh/year\n \
        &emsp; <span style='display: inline-block; width: 120px;'>Cost Impact</span> <span style='color: {'#43a047' if diff > 0 else '#d32f2f'}'>{'✓' if diff > 0 else '↓'}</span> &nbsp; &nbsp; ${abs(diff):,.2f} {('less' if diff > 0 else 'more')}\n\n \
        <div style='margin-top: 16px;'>Overall Performance: &nbsp;<span style='color: {'#43a047' if performance_delta > 0 else '#b71c1c'}'>{abs(performance_delta):.1f}%</span>&nbsp;{('better' if performance_delta > 0 else 'less')} than baseline</div>")


members = ["llm", "input_validation", "ashrae_lookup", "calculation", "recommendation", "utility"] # Current Agents
options = members + ["FINISH"]

# Our team supervisor is an LLM node. It picks the next agent to process and decides when the work is completed
class SupervisorState(BaseModel): # This is a Pydantic class that returns a literal
    """Worker to route to next. If no workers are needed, route to FINISH"""
    next: Literal[*options] # type: ignore 