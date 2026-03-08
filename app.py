from flask import Flask, request, jsonify, render_template
import google.generativeai as genai
import os
from rag_engine import RAGEngine
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Configure Gemini API
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("Warning: GEMINI_API_KEY not found in environment. Please add it to .env.")
else:
    genai.configure(api_key=api_key)

# Initialize RAG Engine
rag = RAGEngine(model_name='models/gemini-embedding-001')

try:
    rag.load_and_chunk_docs()
    rag.generate_embeddings()
except Exception as e:
    print(f"Error initializing RAG engine: {e}")

# session_id -> list of messages
history_db = {}

def get_session_history(session_id):
    if session_id not in history_db:
        history_db[session_id] = []
    # Limit history to last 10 messages
    return history_db[session_id][-10:]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    session_id = data.get('sessionId', 'default')
    user_message = data.get('message', '').strip()

    if not user_message:
        return jsonify({"error": "Message is required"}), 400

    try:
        # Search for relevant context
        retrieved_chunks = rag.similarity_search(user_message, top_k=3, threshold=0.45)
        
        # Get history
        history = get_session_history(session_id)
        history_text = "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in history])
        
        # Build grounded prompt
        if not retrieved_chunks:
            context_text = "No relevant context found."
        else:
            context_text = "\n\n".join([c['content'] for c in retrieved_chunks])

        prompt = f"""
        You are a support assistant. Use the context below to answer the user's question.
        Priority: Context > History.
        If the answer isn't in the context, say: 'I'm sorry, I don't have enough information to answer that.'
        
        ### Context:
        {context_text}
        
        ### Conversation History:
        {history_text}
        
        ### User Question:
        {user_message}
        
        Response:
        """

        # Generation config
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        
        try:
            response = model.generate_content(
                prompt, 
                generation_config={"temperature": 0.1}
            )
            ai_reply = response.text.strip()
            
            tokens_used = 0
            if hasattr(response, 'usage_metadata'):
                tokens_used = response.usage_metadata.total_token_count
            
        except Exception as api_err:
            print(f"API Error: {api_err}")
            err_msg = str(api_err)
            if "quota" in err_msg.lower():
                return jsonify({"error": "Rate limit exceeded."}), 429
            elif "key" in err_msg.lower():
                return jsonify({"error": "Invalid API Key."}), 401
            else:
                return jsonify({"error": "Service temporarily unavailable."}), 503

        # Save to history
        history_db[session_id].append({"role": "user", "content": user_message})
        history_db[session_id].append({"role": "assistant", "content": ai_reply})

        return jsonify({
            "reply": ai_reply,
            "retrievedChunks": len(retrieved_chunks),
            "similarityScores": [round(c['score'], 4) for c in retrieved_chunks],
            "tokensUsed": tokens_used
        })

    except Exception as e:
        import traceback
        print(f"Server Error:\n{traceback.format_exc()}")
        return jsonify({
            "error": "Internal server error",
            "details": None
        }), 500

if __name__ == '__main__':
    app.run(port=5000)
