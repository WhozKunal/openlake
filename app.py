from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests
from langchain_community.llms import HuggingFaceHub
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain.chains import ConversationalRetrievalChain
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Download and process Bee Movie script
def get_bee_movie_script():
    url = "https://courses.cs.washington.edu/courses/cse163/20wi/files/lectures/L04/bee-movie.txt"
    response = requests.get(url)
    return response.text

# Initialize language model and vector store
def initialize_chain():
    # Get the script
    script = get_bee_movie_script()
    
    # Split the text into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )
    chunks = text_splitter.split_text(script)
    
    # Initialize embeddings
    embeddings = HuggingFaceEmbeddings()
    
    # Create vector store
    vectorstore = Chroma.from_texts(
        texts=chunks,
        embedding=embeddings,
        persist_directory="./chroma_db"
    )
    
    # Initialize Mistral model
    llm = HuggingFaceHub(
        repo_id="mistralai/Mistral-7B-Instruct-v0.1",
        huggingfacehub_api_token=os.getenv("HUGGINGFACE_API_TOKEN")
    )
    
    # Create chain
    chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vectorstore.as_retriever(),
        return_source_documents=True
    )
    
    return chain

# Initialize the chain
qa_chain = initialize_chain()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    query = data.get('message', '')
    chat_history = data.get('history', [])
    
    try:
        # Get response from chain
        result = qa_chain({"question": query, "chat_history": chat_history})
        
        return jsonify({
            "response": result["answer"],
            "success": True
        })
    except Exception as e:
        return jsonify({
            "error": str(e),
            "success": False
        }), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)