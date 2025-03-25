from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_cohere import ChatCohere
from langchain_mistralai import ChatMistralAI 

from langchain_community.cache import InMemoryCache
from langchain_core.globals import set_llm_cache

# Initialize the cache
# set_llm_cache(InMemoryCache())

max_tokens = 2000 # GPT-4o mini can generate up to 16,384 tokens in a single output.

embedding_google = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004", task_type="retrieval_document")
embedding_openai = OpenAIEmbeddings(model="text-embedding-3-small")

llm_gemini = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0) 
llm_gpt = ChatOpenAI(model="gpt-4o-mini", temperature=0)
llm_deep = ChatOllama(model="deepseek-r1", temperature=0)
llm_deep15 = ChatOllama(model="deepseek-r1:1.5b", temperature=0)
llm_llama= ChatOllama(model="llama3.2:3b", temperature=0)
llm_cohere = ChatCohere(model="command-r", temperature=0)
llm_mistral = ChatMistralAI(model="mistral-small-latest", temperature=0, max_retries=5)
# open-mistral-nemo