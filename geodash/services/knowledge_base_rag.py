# geodash/services/knowledge_base_rag.py - UPDATED with bilingual support
"""
Bilingual Knowledge base system with RAG (Retrieval Augmented Generation).
Supports both Thai and English queries and responses.
"""
import os
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import streamlit as st
import requests

# Vector database imports
try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False
    st.warning("ChromaDB not installed. Run: pip install chromadb")


class KnowledgeBaseManager:
    """Manages the knowledge base directory and document indexing."""
    
    def __init__(self, kb_dir: str = "geodash/knowledge_base"):
        self.kb_dir = Path(kb_dir)
        self.kb_dir.mkdir(parents=True, exist_ok=True)
        
        self.docs_dir = self.kb_dir / "documents"
        self.reports_dir = self.kb_dir / "reports"
        self.guidelines_dir = self.kb_dir / "guidelines"
        self.embeddings_dir = self.kb_dir / ".embeddings"
        
        for directory in [self.docs_dir, self.reports_dir, self.guidelines_dir, self.embeddings_dir]:
            directory.mkdir(exist_ok=True)
        
        self.collection_name = "geological_knowledge"
        self.client = None
        self.collection = None
        
        if CHROMA_AVAILABLE:
            self._init_vector_db()
        
        self.metadata_file = self.kb_dir / "metadata.json"
        self.metadata = self._load_metadata()
    
    def _init_vector_db(self):
        """Initialize ChromaDB vector database."""
        try:
            self.client = chromadb.PersistentClient(
                path=str(self.embeddings_dir),
                settings=Settings(anonymized_telemetry=False)
            )
            
            try:
                self.collection = self.client.get_collection(name=self.collection_name)
            except:
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={"description": "Geological and groundwater knowledge"}
                )
        except Exception as e:
            st.warning(f"Vector DB initialization failed: {e}")
    
    def _load_metadata(self) -> Dict:
        """Load document metadata cache."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_metadata(self):
        """Save document metadata cache."""
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, indent=2, ensure_ascii=False)
    
    def add_document(self, file_path: Path, category: str = "general", metadata: Optional[Dict] = None) -> bool:
        """Add a document to the knowledge base."""
        try:
            content = self._read_document(file_path)
            if not content:
                return False
            
            chunks = self._chunk_text(content)
            doc_id = f"{category}_{file_path.stem}"
            
            doc_metadata = {
                "filename": file_path.name,
                "category": category,
                "path": str(file_path),
                "chunks": len(chunks),
                **(metadata or {})
            }
            self.metadata[doc_id] = doc_metadata
            self._save_metadata()
            
            if self.collection:
                self._add_to_vector_db(doc_id, chunks, doc_metadata)
            
            return True
        except Exception as e:
            st.error(f"Error adding document: {e}")
            return False
    
    def _read_document(self, file_path: Path) -> str:
        """Read document content."""
        suffix = file_path.suffix.lower()
        
        try:
            if suffix in ['.txt', '.md']:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            elif suffix == '.json':
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return json.dumps(data, indent=2)
            elif suffix == '.pdf':
                try:
                    import pypdf
                    reader = pypdf.PdfReader(file_path)
                    text = ""
                    for page in reader.pages:
                        text += page.extract_text() + "\n"
                    return text
                except ImportError:
                    st.warning("pypdf not installed")
                    return ""
            else:
                st.warning(f"Unsupported file type: {suffix}")
                return ""
        except Exception as e:
            st.error(f"Error reading {file_path}: {e}")
            return ""
    
    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Split text into overlapping chunks."""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            if end < len(text):
                for delimiter in ['. ', '.\n', '! ', '?\n']:
                    last_delim = text[start:end].rfind(delimiter)
                    if last_delim > chunk_size // 2:
                        end = start + last_delim + len(delimiter)
                        break
            
            chunks.append(text[start:end].strip())
            start = end - overlap
        
        return chunks
    
    def _add_to_vector_db(self, doc_id: str, chunks: List[str], metadata: Dict):
        """Add document chunks to vector database."""
        if not self.collection:
            return
        
        try:
            ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
            metadatas = [{**metadata, "chunk_index": i, "doc_id": doc_id} for i in range(len(chunks))]
            
            self.collection.add(
                documents=chunks,
                metadatas=metadatas,
                ids=ids
            )
        except Exception as e:
            st.warning(f"Vector DB indexing failed: {e}")
    
    def search(self, query: str, n_results: int = 5) -> List[Dict]:
        """Search knowledge base for relevant content."""
        if not self.collection:
            return []
        
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            formatted_results = []
            
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    formatted_results.append({
                        "content": doc,
                        "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                        "distance": results['distances'][0][i] if results['distances'] else 0
                    })
            
            return formatted_results
        except Exception as e:
            st.warning(f"Search failed: {e}")
            return []
    
    def get_all_documents(self) -> Dict[str, Dict]:
        """Get all documents in the knowledge base."""
        return self.metadata
    
    def create_sample_knowledge_base(self):
        """Create sample documents."""
        # Use the documents from your existing code
        # (I'll keep this short for brevity)
        docs = {
            "groundwater_basics.md": """# Groundwater Basics in Thailand
[Your existing content]""",
            "drilling_guidelines.md": """# Well Drilling Guidelines
[Your existing content]""",
        }
        
        for filename, content in docs.items():
            filepath = self.docs_dir / filename
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
        
        return len(docs)
    
    def index_directory(self, directory: Path, category: str = "general"):
        """Index all supported documents in a directory."""
        supported_extensions = ['.txt', '.md', '.pdf', '.json']
        indexed = 0
        
        for file_path in directory.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                if self.add_document(file_path, category):
                    indexed += 1
        
        return indexed


class BilingualRAGChatbot:
    """
    Bilingual RAG-enabled chatbot with knowledge base support.
    Automatically detects and responds in Thai or English.
    """
    
    def __init__(self, kb_manager: KnowledgeBaseManager, openrouter_key: Optional[str] = None):
        self.kb = kb_manager
        self.api_key = openrouter_key or os.getenv("OPENROUTER_API_KEY")
        self.model = "anthropic/claude-3.5-haiku"
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
    
    def detect_language(self, text: str) -> str:
        """Detect if text is Thai or English."""
        thai_chars = sum(1 for char in text if '\u0E00' <= char <= '\u0E7F')
        total_chars = len(text.strip())
        
        if total_chars > 0 and (thai_chars / total_chars) > 0.2:
            return 'th'
        return 'en'
    
    def chat_with_context(
        self, 
        user_message: str,
        conversation_history: List[Dict[str, str]],
        n_context_docs: int = 3,
        force_language: Optional[str] = None
    ) -> Dict[str, any]:
        """Chat with RAG context from knowledge base in detected language."""
        
        # Detect language
        detected_lang = force_language or self.detect_language(user_message)
        
        # Search knowledge base
        kb_results = self.kb.search(user_message, n_results=n_context_docs)
        
        # Build context
        context_text = self._build_context_from_results(kb_results)
        
        # Build system prompt with bilingual support
        system_prompt = self._build_bilingual_rag_system_prompt(context_text, detected_lang)
        
        # Prepare messages
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_message})
        
        # Call API
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            
            payload = {
                "model": self.model,
                "messages": messages,
                "max_tokens": 2000,
                "temperature": 0.7,
            }
            
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            assistant_message = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            cost = self._calculate_cost(usage)
            
            return {
                "response": assistant_message,
                "sources": [r["metadata"].get("filename", "Unknown") for r in kb_results],
                "cost": cost,
                "context_used": len(kb_results) > 0,
                "language": detected_lang
            }
            
        except Exception as e:
            error_msg = f"❌ Error / ข้อผิดพลาด: {str(e)}"
            return {
                "response": error_msg,
                "sources": [],
                "cost": 0,
                "context_used": False,
                "language": detected_lang
            }
    
    def _build_context_from_results(self, results: List[Dict]) -> str:
        """Build context string from KB search results."""
        if not results:
            return "No relevant documents found in knowledge base."
        
        context_parts = ["=== KNOWLEDGE BASE CONTEXT ===\n"]
        
        for i, result in enumerate(results, 1):
            content = result["content"][:500]
            source = result["metadata"].get("filename", "Unknown")
            context_parts.append(f"\n[Source {i}: {source}]\n{content}\n")
        
        context_parts.append("\n=== END CONTEXT ===")
        
        return "\n".join(context_parts)
    
    def _build_bilingual_rag_system_prompt(self, context: str, language: str) -> str:
        """Build bilingual system prompt with RAG context."""
        
        if language == 'th':
            return f"""คุณเป็นที่ปรึกษาด้านธรณีวิทยาผู้เชี่ยวชาญ เชี่ยวชาญด้านการจัดการน้ำบาดาล
และการขุดเจาะบ่อน้ำบาดาลในประเทศไทย โดยเฉพาะในจังหวัดสุพรรณบุรี

{context}

ใช้ข้อมูลจากฐานความรู้ข้างต้นเพื่อให้คำตอบที่ถูกต้องและละเอียด
เมื่อคุณอ้างอิงข้อมูลจากบริบท ให้ระบุแหล่งที่มา
หากบริบทไม่ครอบคลุมคำถามทั้งหมด ให้ใช้ความรู้ทั่วไปของคุณ แต่ต้องชี้แจงให้ชัดเจน

ให้คำแนะนำที่ปฏิบัติได้จริงและตรงประเด็น ใช้หน่วยเมตริก กระชับแต่ละเอียดครบถ้วน
ตอบเป็นภาษาไทยเท่านั้น"""
        else:
            return f"""You are an expert geological consultant specializing in groundwater 
management and well drilling in Thailand, particularly in the Suphan Buri region.

{context}

Use the above context from our knowledge base to provide accurate, detailed answers.
When you reference information from the context, mention which source it's from.
If the context doesn't fully answer the question, use your general knowledge but make it clear.

Provide practical, actionable advice. Use metric units. Be concise but thorough.
Respond in English only."""
    
    def _calculate_cost(self, usage: Dict) -> float:
        """Calculate cost."""
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        cost = (input_tokens * 0.80 + output_tokens * 4.0) / 1_000_000
        return round(cost, 6)


class KnowledgeBaseUI:
    """Streamlit UI for managing knowledge base."""
    
    def __init__(self, kb_manager: KnowledgeBaseManager):
        self.kb = kb_manager
    
    def render_management_panel(self):
        """Render knowledge base management panel."""
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 📚 Knowledge Base")
        
        docs = self.kb.get_all_documents()
        st.sidebar.metric("Documents / เอกสาร", len(docs))
        
        if st.sidebar.button("🔄 Refresh Index / รีเฟรชดัชนี"):
            indexed = self.kb.index_directory(self.kb.docs_dir)
            st.sidebar.success(f"Indexed / จัดทำดัชนี {indexed} documents / เอกสาร")
        
        if st.sidebar.button("📝 Create Sample Docs / สร้างเอกสารตัวอย่าง"):
            count = self.kb.create_sample_knowledge_base()
            st.sidebar.success(f"Created / สร้าง {count} sample documents / เอกสารตัวอย่าง")
            self.kb.index_directory(self.kb.docs_dir)
            st.rerun()
        
        with st.sidebar.expander("📄 View Documents / ดูเอกสาร"):
            for doc_id, metadata in docs.items():
                st.caption(f"📄 {metadata.get('filename', doc_id)}")
                st.caption(f"   Category / หมวดหมู่: {metadata.get('category', 'N/A')}")
                st.caption(f"   Chunks / ส่วน: {metadata.get('chunks', 0)}")


# Export main classes
__all__ = [
    "KnowledgeBaseManager",
    "BilingualRAGChatbot",
    "KnowledgeBaseUI"
]