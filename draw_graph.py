from graph import graph
import os

# Get base graph
base_graph = graph.get_graph(xray=True).draw_mermaid()


cleaned_lines = []
skip_section = False
for line in base_graph.split('\n'):
    if 'subgraph' in line:
        skip_section = True
        continue
    if 'end' in line and not '__end__' in line: 
        skip_section = False
        continue
    if not skip_section:
        cleaned_lines.append(line.strip())

# Remove header and join lines
base_graph = '\n'.join(cleaned_lines)
base_graph = base_graph.replace("%%{init: {'flowchart': {'curve': 'linear'}}}%%\ngraph TD;", "")

enhanced_mermaid = f"""
%%{{init: {{
    'theme': 'base',
    'flowchart': {{
        'curve': 'basis',
        'padding': 15,
        'nodeSpacing': 30,
        'rankSpacing': 40
    }}
}}}}%%
graph TD;

{base_graph}

subgraph calc_steps[Calculation Steps]
    direction TB
    validate[Validate] --> convert[Convert]
    convert --> heat[Heat Gain]
    heat --> energy[Energy]
    energy --> cost[Cost]
end

subgraph rag_steps[ASHRAE RAG]
    direction TB
    retrieve[Retrieve] --> grade[Grade]
    grade --> transform[Transform]
    grade --> generate[Generate]
    transform -.-> web[Search]
    web -.-> generate
end

calculation --> calc_steps
ashrae_lookup_agent --> rag_steps

%% Add container boxes for the agent groups
input_box[" "]:::container
ashrae_box[" "]:::container
recommendation_box[" "]:::container
llm_box[" "]:::container
utility_box[" "]:::container

classDef container fill:#f2f0ff,stroke:#e9ecef,stroke-width:1px,width:150px,height:150px
classDef step_box fill:#f8f9fa,stroke:#dee2e6,stroke-width:2px
classDef node fill:#ffffff,stroke:#adb5bd,stroke-width:1px
class calc_steps,rag_steps step_box
class validate,convert,heat,energy,cost,retrieve,grade,transform,web,generate node
"""

with open("enhanced_graph.mmd", "w") as f:
    f.write(enhanced_mermaid)

os.system('mmdc -i enhanced_graph.mmd -o fancy_graph.png -b white -w 3000 -H 2000 -s 2')