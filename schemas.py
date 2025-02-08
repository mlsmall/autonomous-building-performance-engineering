from langgraph.graph import MessagesState
from pydantic import BaseModel, Field
from typing import Literal

# This agent state is the input to each node in the graph
# Ttracks all data through the process:
class AgentState(MessagesState):
    # The 'next' field indicates where to route to next
    next: str
    # Input data
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
    u_value: float = Field(gt=0, description="U-value")
    city: str = Field(min_length=1, description="Building location")

# Forces output format
class Recommendation(BaseModel):
    """Structure for window performance comparison"""
    performance_delta: float = Field(description="Percentage difference from baseline")
    recommendations: list[str] = Field(description="List of formatted recommendations that MUST follow this format: \
        First line: 'Your glass choice means:' \
        Then bullet points showing ABSOLUTE DIFFERENCES between baseline and proposed: \
        • {abs(baseline - proposed):,.0f} {'more' if proposed > baseline else 'less'} BTU/hr heat gain \
        • {abs(baseline - proposed):,.0f} {'more' if proposed > baseline else 'less'} kWh/year \
        • ${abs(baseline - proposed):,.2f} {'more' if proposed > baseline else 'less'} in cooling costs \
        Last line: Shows performance_delta as percent better/worse than baseline")

members = ["llm", "input_validation", "ashrae_lookup", "calculation", "recommendation", "utility"] # Agent names
options = members + ["FINISH"]

# Our team supervisor is an LLM node. It picks the next agent to process and decides when the work is completed
class SupervisorState(BaseModel): # This is a Pydantic class that returns a literal
    """Worker to route to next. If no workers are needed, route to FINISH"""
    next: Literal[*options] # type: ignore 