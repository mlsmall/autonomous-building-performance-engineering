from langgraph.graph import MessagesState
from pydantic import BaseModel, Field
from typing import Literal

# This agent state tracks the building data:
class AgentState(MessagesState):
    # The 'next' field indicates where to route to next
    next: str
    # Input data
    user_id: str = None
    city: str = None
    glass_u_value: float = None
    shgc: float = None
    total_floor_area: float = None
    wall_area: float = None
    wall_u_value: float = None
    window_area: float = None
    # ASHRAE data
    ashrae_to: float = None
    ashrae_cdd: float = None
    ashrae_climate_zone: int = None
    ashrae_glass_u: float = None
    ashrae_shgc: float = None
    ashrae_wall_u: float = None
    # Utility data
    utility_rate: float = None
    # Solar radiation data
    radiation: float = None
    # Calculation results
    proposed_total_heat_gain: float = None
    proposed_cooling_energy: float = None
    proposed_cost: float = None
    proposed_glass_heat_gain: float = None
    proposed_wall_heat_gain: float = None
    baseline_total_heat_gain: float = None
    baseline_cooling_energy: float = None
    baseline_cost: float = None
    baseline_glass_heat_gain: float = None
    baseline_wall_heat_gain: float = None

# Validates user input
class BuildingInput(BaseModel):
    window_area: float = Field(gt=0, description="Window area in ft²")
    shgc: float = Field(gt=0, lt=1.1, description="Solar Heat Gain Coefficient")
    glass_u_value: float = Field(gt=0, lt=20, description="The u-value must be between 0 and 20")
    city: str = Field(description="It MUST be the name of a city from anywhere in the world."
        "It must NOT be a country, province, state, fruit, animal, plant, or vegtable")
    wall_area: float = Field(gt=0, description="Wall area in ft²")
    wall_u_value: float = Field(gt=0, lt=20, description="The wall u-value must be between 0 and 20")
            
class Recommendation(BaseModel):
    """Structure for window performance comparison"""
    performance_delta: float = Field(description="Percentage difference from baseline")
    recommendations: list[str] = Field(description="""List of formatted output that MUST follow this format:
    heat_gain_diff: float = Field(description="Proposed - Baseline heat gain difference")
    energy_diff: float = Field(description="Proposed - Baseline energy difference")
    cost_diff: float = Field(description="Proposed - Baseline cost difference")""")
    
members = ["llm", "input_validation", "ashrae_lookup", "calculation", "recommendation", "utility", "radiation_node"] # Current Agents
options = members + ["FINISH"]
class SupervisorState(BaseModel): # Pydantic class that returns a literal
    """Worker to route to next."""
    next: Literal[*options] # type: ignore 
