import os
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

from langchain_core.documents import Document
from langchain_chroma import Chroma
import pandas as pd
from langchain_community.document_loaders import DataFrameLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from models import embedding_google

import warnings
warnings.filterwarnings("ignore")  # Suppress all warnings
embedding = embedding_google

# Ensure the /tmp/radiation_vector_db directory exists for Streamlit Cloud compatibility
os.makedirs("/tmp/radiation_vector_db", exist_ok=True)

vector_store = Chroma(
    collection_name="rag-chroma",
    embedding_function=embedding,
    persist_directory="/tmp/radiation_vector_db"
)

rad_retriever = vector_store.as_retriever(search_kwargs={"k": 3})

if __name__ == "__main__":
    chunk_size = 2048
    chunk_overlap = 200
    files_path = "data/radiation"
    
    print(f"\nStarting to ingest files from the {files_path} folder...")
    documents = []
    for file in os.listdir(files_path):
        if file.endswith(".csv"):
            csv_path = os.path.join(files_path, file)
            df = pd.read_csv(csv_path)
            # Convert entire rows to string
            df['combined'] = df.apply(lambda x: ' '.join(x.astype(str)), axis=1)
            loader = DataFrameLoader(df, page_content_column="combined")
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