# Autonomous Multi-Agent Generative AI System for Real-Time Building Performance Engineering

This agentic network marks a significant shift in building performance modeling: the first autonomous multi-agent system that combines engineering calculations with generative AI to automate complex engineering decisions.

This isn't just another:
- "AI-powered" recommendation system
- LLM chatbot "researcher" giving generic summaries
- Static building energy calculator 
- Basic performance metrics tool

## What Makes It Different:
- Engineering calculations based on science, not rule of thumbs or LLM guesses
- Multi-agent system that explains how building design choices affect energy use, costs, and performance
- Interactive design guidance that doesn't just show problems, but provides better solutions
- Integrates international energy codes and standards
- Replaces frustrating energy management tools with natural conversation

## How It Works

### Scenario 1: HVAC System Selection

User: "I'm considering VRF for my 50,000 sq ft office building in Miami"

AI: "For a Miami office of that size, a VAV distribution system is the more practical choice. Let me show you the numbers:

- You're looking at $850,000 for VAV installation ($17/sq ft) costs versus $1.1M for VRF ($22/sq ft)

- Now, VRF runs at a COP of approximately 3.4 compared to VAV's 3.0, which would give you energy savings of about $16,800 a year

However, Miami's high humidity means you'd need additional dehumidification equipment with VRF, adding $75,000 to your costs. The VAV system will handle your building's humidity better through its central cooling coil, and you won't have to deal with managing a large refrigerant system throughout your building."

User: "And what if I change my windows to a glass with a low-e coating and an SHGC of 0.24?"

AI: "Well, since your current building design has an SHGC of 0.28, lowering it to 0.24 would reduce your cooling load by 15,000 kWh/year. This means you'll save about $1,800 in annual energy costs and cut your peak cooling demand by 12%. This change would also get you 1-2 more points in your LEED v4.1 Energy and Atmosphere credit category that you're working on."

### Scenario 2: Energy Cost Reduction

User: "I need to cut my energy costs"

AI: "Let me look at your 72,000 sqft Houston medical center. Here's what we can do:

Quick wins:
- Upgrading your current glass (SHGC 0.38) to low-e glass (SHGC 0.25) saves $18,500/year
- Adding CO2 sensors and demand controls saves $22,000/year in ventilation costs
- Total investment: $165,000, payback in 4.1 years

Larger investments to consider:
- Upgrading your old chillers (COP 4.0) to new units (COP 5.0) saves $32,000/year
- Adding roof insulation (from R-15 to R-25) saves $15,000/year
- Total investment: $295,000, payback in 6.3 years"

### Scenario 3: New Phoenix Office

User: "I'm designing a new office building in Phoenix, about 100,000 square feet."

AI: "Can you tell me your current window-to-wall ratio and glass specifications? This will help me analyze the solar gain impact."

User: "Planning on 40% window-to-wall with standard glass, SHGC 0.40"

AI: "Based on ASHRAE 90.1-2019 Energy Standard for Climate Zone 2B (Phoenix), the baseline SHGC should be 0.25. Your proposed design with SHGC 0.40 means:
- $48,000/year higher cooling energy costs than baseline
- Peak cooling load 15% above baseline (additional 70 tons)
- $125,000 more for larger HVAC equipment

AI: Want to see some options that could save money?"

User: "Yes"

AI: "Here are three approaches, ranked by impact:

1. High-performance low-e glass (SHGC 0.23):
- Energy cost savings of $30,000/year
- Cuts peak cooling by 20%
- This reduction means you can drop from a 480-ton water-cooled chiller to a 385-ton system, saving $57,000 in equipment costs
- Additional cost: $288,000 ($15/sqft premium for 19,200 sqft of glass)
- 9.6 year payback including equipment savings

2. External shading + standard glass:
- Energy cost savings of $23,000/year
- Cuts peak cooling by 15%
- Could reduce chiller size by 60 tons, saving about $36,000 in equipment
- Additional cost: $635,000 ($33/sqft for 19,200 sqft of shading)
- 27 year payback including equipment savings
- Maintenance concerns with external system and Phoenix dust storms

3. Reduced window area (40% to 30%) with standard glass:
- Energy cost savings of $15,000/year
- Cuts peak cooling by 12%
- Saves you $86,400 in initial glass costs
- Reduces natural light significantly
- Minimal impact on equipment sizing"

## Why It Matters
Get professional engineering analysis in seconds, with personalized design guidance and recommendations from concept to completion.

## System Architecture

```ascii
 ┌────────────────────────────────────────────────────────────────────────────────────┐
 │                              Autonomous Agent Network                              │
 └────────────────────────────────────────────────────────────────────────────────────┘

┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐
│   Input   │  │ Knowledge │  │ Resource  │  │   Calc.   │  │   Rec.    │  │ Technical │
│Validation │  │ Retrieval │  │ Research  │  │   Agent   │  │   Agent   │  │  Report   │
└─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘
      │              │              │              │              │              │    
      │              ▼              │              │              ▼              │    
      │        ┌──────────┐         │              │         ┌──────────┐        │    
      │        │  Vector  │         │              │         │  Vector  │        │    
      │        │  Store   │         │              │         │  Store   │        │    
      │        └────┬─────┘         │              │         └────┬─────┘        │    
      │             │               │              │              │              │    
      ▼             ▼               ▼              ▼              ▼              ▼    
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                                   State Management                                   │
│                                 (LangGraph Workflow)                                 │
└──────────────────────────────────────────────────────────────────────────────────────┘
                                          ▲                                        
                                          │                                        
                                          ▼                                        
      ┌────────────────────────────────────────────────────────────────────────────┐
      │                             Supervisor Agent                               │
      └────────────────────────────────────────────────────────────────────────────┘
                                          ▲                                        
                                          │                                        
                                   ┌──────┴──────┐                                
                                   │   MongoDB   │                                
                                   │ Persistence │                                
                                   └─────────────┘                                
```
## Technical Implementation

This system implements a multi-agent architecture using LangGraph for agent orchestration and state management:

Agent Framework:
- Stateful agent design using LangGraph's StateGraph:
  - MemorySaver maintains agent's internal state (building specs, calculations, results)
  - Agents use different prompts based on their current state
  - ReAct Supervisor agent (GPT-4) determines control flow between other agents
  - Human-in-the-loop to approve report format
- ReAct (Reasoning + Action) pattern implementation:
  - Thought: Analyze current state and requirements
  - Action: Choose appropriate tool/calculation
  - Observation: Analyzes tool outputs and responses
  - Final Answer: Return structured response

Specialized Agents:
- Input Validation Agent: Checks and validates building input data
- Knowledge Retrieval Agent: Queries vector store for building codes, standards, and design guides
- Resource Research Agent: Retrieves utility rates via Tavily Search tool and climate data from vector stores
- Calculation Agent: Executes building performance calculations via Python REPL tool
- Recommendation Agent: Compares results to benchmarks, analyzes building, and proposes design improvements
- Technical Report Agent: Formats analysis results into structured graphs, tables, and reports

State Management:
- Supervisor agent directs routes between agents based on conversation state
- Short-term memory via MemorySaver checkpoints during session
- Long-term persistent storage of agent state data
- Pydantic models to enforce input and output state structure

Data Infrastructure:
- MongoDB stores user and building data
- Chroma vector database with text embeddings
- RAG retrieves documents for LLM use


## License
Copyright © 2025 Mauro Small
This project is proprietary and confidential. See the [LICENSE](LICENSE) file for details.
Viewing and forking for personal reference only. No commercial use, distribution, or modification permitted.