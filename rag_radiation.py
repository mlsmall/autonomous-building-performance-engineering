from langchain import hub
from langchain_core.output_parsers import StrOutputParser

from db_creation.radiation_db import rad_retriever
from models import llm_gemini_15, llm_gpt, llm_llama, llm_cohere, llm_gemini_25

llm = llm_gemini_25

# Load the prompt
prompt = hub.pull("rlm/rag-prompt")
# print("--Prompt--", prompt)

# Create the RAG Chain
rag_chain = prompt | llm | StrOutputParser()

def rad_retrieve(question):
    documents = rad_retriever.invoke(question)
    # print("\n=== RETRIEVAL DEBUG ===")
    # print(f"\nDocuments retrieved: {len(documents)}")
    return documents

def rad_generate(question, documents):
    generation = rag_chain.invoke({"context": documents, "question": question})
    return generation

# Main execution
if __name__ == "__main__":
    question = "What is the solar radiation for Montreal?"
    docs = rad_retrieve(question)
    answer = rad_generate(question, docs)
    print("\nFinal output:")
    print(answer)