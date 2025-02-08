from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document

import warnings
warnings.filterwarnings("ignore")  # Suppress all warnings

embedding = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004", task_type="retrieval_document")


from langchain_chroma import Chroma
vector_store = Chroma(
    collection_name="rag-chroma",
    embedding_function=embedding,
    persist_directory="./vector_database"
)

# retriever = vector_store.as_retriever(search_type = "mmr", search_kwargs={"k": 10, "fetch_k": 50})
retriever = vector_store.as_retriever(search_kwargs={"k": 10})

if __name__ == "__main__":
    chunk_size = 4096
    chunk_overlap = 400
    files_path = "data"
    
    import os
    from langchain_community.document_loaders import PyMuPDFLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    print(f"\nStarting to ingest files from the {files_path} folder...")
    documents = []
    for file in os.listdir(files_path):
        if file.endswith(".pdf"):
            pdf_path = os.path.join("data", file)
            loader = PyMuPDFLoader(pdf_path)
            documents.extend(loader.load())

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    
    # Combine all pages into one document before splitting
    combined_text = " ".join([doc.page_content for doc in documents])
    doc_with_combined = Document(page_content=combined_text)

    doc_splits = text_splitter.split_documents([doc_with_combined])

    # Testing chunk size and overlap
    # print("\nFirst few chunks:")
    # for i, chunk in enumerate(doc_splits[:3]):
    #     print(f"\nChunk {i+1} length: {len(chunk.page_content)}")
    #     print(chunk.page_content)

    print(f"Adding {len(doc_splits)} documents to the vector store")
    start_time = datetime.now()
    vector_store.add_documents(documents=doc_splits)
    elapsed = datetime.now() - start_time
    print(f"Vector store updated successfully in {elapsed.seconds/60:.2f} minutes")