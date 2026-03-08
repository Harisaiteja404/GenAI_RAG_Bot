import json
import numpy as np
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

class RAGEngine:
    def __init__(self, docs_path='docs.json', model_name='models/gemini-embedding-001'):
        self.docs_path = docs_path
        self.model_name = model_name
        self.chunks = []
        self.embeddings = []
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)

    def load_and_chunk_docs(self, chunk_size=300):
        """Load and split documents into smaller chunks."""
        with open(self.docs_path, 'r') as f:
            docs = json.load(f)
        
        self.chunks = []
        for doc in docs:
            content = f"Title: {doc['title']}\nContent: {doc['content']}"
            
            # Basic chunking by character count
            if len(content) > chunk_size * 4:
                for i in range(0, len(content), chunk_size * 4):
                    self.chunks.append(content[i:i + chunk_size * 4])
            else:
                self.chunks.append(content)
        return self.chunks

    def generate_embeddings(self):
        """Generate vector embeddings for all document chunks."""
        if not self.chunks:
            self.load_and_chunk_docs()
        
        try:
            responses = genai.embed_content(
                model=self.model_name,
                content=self.chunks,
                task_type="retrieval_document"
            )
            
            # Handle both list and single return formats
            if 'embedding' in responses:
                self.embeddings = np.array(responses['embedding'])
            elif 'embeddings' in responses:
                self.embeddings = np.array(responses['embeddings'])
            else:
                raise ValueError(f"Invalid response format: {responses.keys()}")
            
            return self.embeddings
        except Exception as e:
            print(f"Error generating embeddings: {e}")
            raise

    def get_query_embedding(self, query):
        """Generate embedding for a search query."""
        try:
            response = genai.embed_content(
                model=self.model_name,
                content=query,
                task_type="retrieval_query"
            )
            if 'embedding' in response:
                return np.array(response['embedding'])
            else:
                raise ValueError(f"Invalid response format: {response.keys()}")
        except Exception as e:
            print(f"Error generating query embedding: {e}")
            raise

    def similarity_search(self, query, top_k=3, threshold=0.4):
        """Find most relevant chunks using cosine similarity."""
        query_embedding = self.get_query_embedding(query)
        
        # Calculate cosine similarity
        dot_products = np.dot(self.embeddings, query_embedding)
        norm_chunks = np.linalg.norm(self.embeddings, axis=1)
        norm_query = np.linalg.norm(query_embedding)
        
        similarities = dot_products / (norm_chunks * norm_query)
        
        # Sort and filter by threshold
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            score = float(similarities[idx])
            if score >= threshold:
                results.append({
                    "content": self.chunks[idx],
                    "score": score
                })
        
        return results

if __name__ == "__main__":
    # Local Test
    engine = RAGEngine()
    engine.load_and_chunk_docs()
    engine.generate_embeddings()
    query = "How do I change my password?"
    results = engine.similarity_search(query)
    for res in results:
        print(f"Score: {res['score']:.4f}\n{res['content']}\n")
