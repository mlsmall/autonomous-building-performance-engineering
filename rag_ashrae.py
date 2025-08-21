from langchain import hub
from langchain_core.output_parsers import StrOutputParser
from db_creation.ashrae_db import retriever
from models import llm_gemini_25

llm = llm_gemini_25

# Load the RAG prompt
prompt = hub.pull("rlm/rag-prompt")
rag_chain = prompt | llm | StrOutputParser()

def retrieve(state):
    """Retrieve relevant documents for a question"""
    question = state["question"]
    print("🔍 Retrieving documents for:", question)
    documents = retriever.invoke(question)
    print(f"📑 Found {len(documents)} documents")
    return {"documents": documents, "question": question}

def generate(state):
    """Generate answer using RAG"""
    question = state["question"]
    documents = state["documents"]
    print("🤖 Generating answer...")
    generation = rag_chain.invoke({"context": documents, "question": question})
    print("✅ Done")
    return {"documents": documents, "question": question, "generation": generation}

if __name__ == "__main__":
    zone_number = 6
    question = f"What is the U-value for Vertical Fenestration 0%–40% of Wall for Nonmetal framing, all \
        in climate zone {zone_number} according to Table Building Envelope Requirements? \
        Only provide the numeric U-value. Do not provide any additional text."

    # Run the retrieval and generation
    state = {"question": question}
    state = retrieve(state)
    state = generate(state)
    
    # Final output
    print("\nFinal output:")
    print(state["generation"])