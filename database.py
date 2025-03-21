from pymongo import MongoClient
from datetime import datetime
from schemas import AgentState

from dotenv import load_dotenv
import os
load_dotenv()


# MongoDB setup
client = MongoClient(os.getenv("MONGODB_URI"))
db = client["building_db"]
buildings = db["buildings"]

# Create a new document in the database
def building_data(user_id: str, state: AgentState):
    state_data = {key: value for key, value in state.items() 
                 if value is not None 
                 and key != 'next'
                 and key != 'messages'
                 and key != 'existing_data'}
    
    # Create or update the document
    buildings.update_one(
        {"user_id": user_id},
        {"$set": {**state_data,"timestamp": datetime.now()}}
    )

    stored = buildings.find_one({"user_id": user_id})
    stored['_id'] = str(stored['_id'])
    return stored

# Retrieve a document from the database
def get_user_history(user_id: str):
    stored = buildings.find_one({"user_id": user_id})
    if stored:
        stored['_id'] = str(stored['_id'])
    return stored

# Test the database
if __name__ == "__main__":
    from schemas import AgentState
    
    state = AgentState(
        messages=[],
        next="",
        city="Montreal",
        window_area=1500.0,
        shgc=0.4,
        u_value=0.35,
        ashrae_to=95.0,
        ashrae_cdd=1200.0,
        ashrae_climate_zone=6,
        ashrae_u_factor=0.42,
        ashrae_shgc=0.38,
        utility_rate=0.15,
        proposed_heat_gain=45000.0,
        proposed_cooling_energy=12000.0,
        proposed_cost=1800.0,
        baseline_heat_gain=50000.0,
        baseline_cooling_energy=13000.0,
        baseline_cost=1950.0
    )
    
    building_data("test_user", state)
