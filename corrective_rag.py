from langchain import hub
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from db_creation.ashrae_db import retriever
from models import llm_gemini, llm_gpt, llm_llama, llm_cohere

llm = llm_gpt

# Load the prompt
prompt = hub.pull("rlm/rag-prompt")
# print(f"Prompt from hub ---> {prompt}")

# Post-processing
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

### Create document grader class
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

# Create the RAG Chain
rag_chain = prompt | llm | StrOutputParser()

class GradeDocuments(BaseModel):
    """Binary score for relevance check on retrieved documents"""
    binary_score: str = Field(description="Are documents relevant to the question, 'yes' or 'no'?")

# LLM with function call
structured_llm_grader = llm.with_structured_output(GradeDocuments)

# Prompt
grader_system = """You are a grader assessing the relevance of a retrieved document to a user question. \n
If the document contains keyword(s) or semantic meaning related to the question, grade it as relevant. \n
It does not need to be a stringent test. The goal is to filter out erroneous retrievals. \n
Give a binary score 'yes' or 'no', where 1 means that the document is relevant to the question"""

# Is the question I'm passing relevant to the document
grade_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", grader_system),
        ("human", "Retrieved document: \n\n {document} \n\n User question: {question}")
    ]
)

retrieval_grader = grade_prompt | structured_llm_grader

### Lets Create the Re-Writer
# Prompt
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

# Prompt to re-write a question to be more optimized for a web search
re_write_system = """ You're a question re-writer that convers an input question to a better version that is optimized for \
a web search. Look at the input and try to reason about the underlying semantic intent and meaning."""

re_write_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", re_write_system),
        ("human", "Here is the initial question: \n\n {question} \n Formulate an improved question.")
    ]
)

question_rewriter = re_write_prompt | llm | StrOutputParser()


### Create the functions
def retrieve(state):
    # print("Retrieving...")

    question = state["question"]
    documents = retriever.invoke(question)

    # Add these debug prints
    # print("\n=== RETRIEVAL DEBUG ===")
    # print("Input question:", question)
    # print(f"\nDocuments retrieved: {len(documents)}")
    # print("\nFULL Content of Retrieved Documents:")
    # for i, doc in enumerate(documents):
    #     print(f"\nDocument {i+1}:")
    #     print(doc.page_content)
    #     print("-" * 50)
    
    return {"documents": documents, "question": question}

def grade_documents(state):
    print("Checking if documents are relevant to the question...")

    question = state["question"]
    documents = state["documents"]
    
    filtered_docs = []
    web_search = "Yes"  # Start assuming no relevant docs

    # # Score each document
    for doc in documents:
        score = retrieval_grader.invoke({"question": question, "document": doc.page_content})

        grade = score.binary_score
        if grade == "yes":
            # print("Document is relevant to the question")
            filtered_docs.append(doc)
            web_search = "No"
        # else:
        #     print("Document is not relevant to the question")
    
    return {"documents": filtered_docs, "question": question, "web_search": web_search}

def generate(state):
    """Generate answer. Return new key added to state, generation, that contains LLM generation"""
    
    # print("Generating answer...")
    question = state["question"]
    documents = state["documents"]

    generation = rag_chain.invoke({"context": documents, "question": question})

    # print("\n=== GENERATION DEBUG ===")
    # print("Generation output:", generation)

    return {"documents": documents, "question": question, "generation": generation}

# When the question is not relevant to the documents, we transform the query
def transform_query(state):
    """ Transform the query to produce a better question """
    print("Transforming the query...")

    question = state["question"]
    documents = state["documents"]

    # Re-write question
    better_question = question_rewriter.invoke({"question": question})
    print("New question ->", better_question)
    
    return {"documents": documents, "question": better_question}

# Web Search using Tavily

from langchain_community.tools.tavily_search import TavilySearchResults
from langchain.schema import Document

web_search_tool = TavilySearchResults(k=5)

def web_search(state):
    """
    Perform a web search using Tavily based on the re-phrased question and returns updated document keys with appended web results
    """
    print("Performing web search...")
    question = state["question"]
    documents = state["documents"]

    # Perform web search and update document keys with web results
    
    docs = web_search_tool.invoke(question)
    # web_results = "\n".join(docs)
    web_results = "\n".join(doc['content'] for doc in docs)
    web_results = Document(page_content=web_results)
    documents.append(web_results)

    return {"documents": documents, "question": question}

def decide_to_generate(state):
    """
    Decide whether to generate an LLM answer or regenerate the question
    """
    print("Assesing graded documents...")
    web_search = state["web_search"]

    if web_search == "Yes":
        # All documents have been filtered check their relevance
        # We will regenerate a new query
        print("--- Decision: No documents are relevant to the question. Changing the query...")
        return "transform_query"
    else:
        # We have relevant documents, so generate answer
        print("---Decision: Generating answer...")
        return "generate"

# Code Skeleton
from langgraph.graph import END, StateGraph, START
from typing_extensions import TypedDict, List

class State(TypedDict):
    """
    Represents the state of the graph
    
    Attributes:
        question: The question asked
        generation: LLM generation
        web_search: Web search results
        documents: list of documents
    """
    question: str
    generation: str
    web_search: str
    documents: List[str]

workflow = StateGraph(State)
workflow.add_node("retrieve", retrieve)
workflow.add_node("grade_documents", grade_documents)
workflow.add_node("generate", generate)
workflow.add_node("transform_query", transform_query)
workflow.add_node("web_search_node", web_search)

# Build graph
workflow.add_edge(START, "retrieve")
workflow.add_edge("retrieve", "grade_documents")
workflow.add_conditional_edges("grade_documents", decide_to_generate, {"transform_query": "transform_query", "generate": "generate"})
workflow.add_edge("transform_query", "web_search_node")
workflow.add_edge("web_search_node", "generate")
workflow.add_edge("generate", END)

# Compile
graph = workflow.compile()

# Display the graph
# graph.get_graph(xray=True).draw_mermaid_png(output_file_path="graph_flow.png")


# Run
# inputs = {"question": "What is the SHGC for Vertical Fenestration 0%–40% of Wall (for all frame types) \
# in climate zone 6 according to Building Envelope Requirements? \
# Please provide only the numeric SHGC value without any additional text."}

# # Run the graph and print outputs
# for output in graph.stream(inputs):
#     for key, value in output.items():
#         # Node
#         print(f"Node '{key}':")
#     print("-------------------")

# # Final generation
# print("Final output:")
# print(value["generation"])