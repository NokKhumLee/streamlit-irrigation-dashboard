# geodash/services/knowledge_base_rag.py
"""
Knowledge base system with RAG (Retrieval Augmented Generation).
Manages geological documents, well reports, and domain knowledge.
"""
import os
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import streamlit as st
import requests

# Vector database imports (using ChromaDB - lightweight and local)
try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False
    st.warning("ChromaDB not installed. Run: pip install chromadb")


class KnowledgeBaseManager:
    """
    Manages the knowledge base directory and document indexing.
    Supports PDF, TXT, MD, JSON files.
    """
    
    def __init__(self, kb_dir: str = "geodash/knowledge_base"):
        """
        Initialize knowledge base manager.
        
        Args:
            kb_dir: Path to knowledge base directory
        """
        self.kb_dir = Path(kb_dir)
        self.kb_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        self.docs_dir = self.kb_dir / "documents"
        self.reports_dir = self.kb_dir / "reports"
        self.guidelines_dir = self.kb_dir / "guidelines"
        self.embeddings_dir = self.kb_dir / ".embeddings"
        
        for directory in [self.docs_dir, self.reports_dir, self.guidelines_dir, self.embeddings_dir]:
            directory.mkdir(exist_ok=True)
        
        # Initialize vector database
        self.collection_name = "geological_knowledge"
        self.client = None
        self.collection = None
        
        if CHROMA_AVAILABLE:
            self._init_vector_db()
        
        # Document metadata cache
        self.metadata_file = self.kb_dir / "metadata.json"
        self.metadata = self._load_metadata()
    
    def _init_vector_db(self):
        """Initialize ChromaDB vector database."""
        try:
            self.client = chromadb.PersistentClient(
                path=str(self.embeddings_dir),
                settings=Settings(anonymized_telemetry=False)
            )
            
            # Get or create collection
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
    
    def add_document(
        self, 
        file_path: Path, 
        category: str = "general",
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Add a document to the knowledge base.
        
        Args:
            file_path: Path to document file
            category: Document category (general, report, guideline)
            metadata: Additional metadata
            
        Returns:
            True if successful
        """
        try:
            # Read document content
            content = self._read_document(file_path)
            
            if not content:
                return False
            
            # Chunk the content
            chunks = self._chunk_text(content)
            
            # Generate document ID
            doc_id = f"{category}_{file_path.stem}"
            
            # Store metadata
            doc_metadata = {
                "filename": file_path.name,
                "category": category,
                "path": str(file_path),
                "chunks": len(chunks),
                **(metadata or {})
            }
            self.metadata[doc_id] = doc_metadata
            self._save_metadata()
            
            # Add to vector database if available
            if self.collection:
                self._add_to_vector_db(doc_id, chunks, doc_metadata)
            
            return True
            
        except Exception as e:
            st.error(f"Error adding document: {e}")
            return False
    
    def _read_document(self, file_path: Path) -> str:
        """Read document content based on file type."""
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
                    st.warning("pypdf not installed. Run: pip install pypdf")
                    return ""
            
            else:
                st.warning(f"Unsupported file type: {suffix}")
                return ""
                
        except Exception as e:
            st.error(f"Error reading {file_path}: {e}")
            return ""
    
    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """
        Split text into overlapping chunks for better context retrieval.
        
        Args:
            text: Text to chunk
            chunk_size: Maximum characters per chunk
            overlap: Overlap between chunks
            
        Returns:
            List of text chunks
        """
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence endings
                for delimiter in ['. ', '.\n', '! ', '?\n']:
                    last_delim = text[start:end].rfind(delimiter)
                    if last_delim > chunk_size // 2:  # Don't break too early
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
            # Create IDs for each chunk
            ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
            
            # Create metadata for each chunk
            metadatas = [
                {**metadata, "chunk_index": i, "doc_id": doc_id} 
                for i in range(len(chunks))
            ]
            
            # Add to collection
            self.collection.add(
                documents=chunks,
                metadatas=metadatas,
                ids=ids
            )
            
        except Exception as e:
            st.warning(f"Vector DB indexing failed: {e}")
    
    def search(self, query: str, n_results: int = 5) -> List[Dict]:
        """
        Search knowledge base for relevant content.
        
        Args:
            query: Search query
            n_results: Number of results to return
            
        Returns:
            List of relevant document chunks with metadata
        """
        if not self.collection:
            return []
        
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            # Format results
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
    
    def remove_document(self, doc_id: str) -> bool:
        """Remove a document from the knowledge base."""
        try:
            if doc_id in self.metadata:
                # Remove from metadata
                del self.metadata[doc_id]
                self._save_metadata()
                
                # Remove from vector DB
                if self.collection:
                    # Get all chunk IDs for this document
                    results = self.collection.get(
                        where={"doc_id": doc_id}
                    )
                    if results['ids']:
                        self.collection.delete(ids=results['ids'])
                
                return True
            return False
            
        except Exception as e:
            st.error(f"Error removing document: {e}")
            return False
    
    def index_directory(self, directory: Path, category: str = "general"):
        """Index all supported documents in a directory."""
        supported_extensions = ['.txt', '.md', '.pdf', '.json']
        indexed = 0
        
        for file_path in directory.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                if self.add_document(file_path, category):
                    indexed += 1
        
        return indexed
    
    def create_sample_knowledge_base(self):
        """Create sample documents for the knowledge base."""
        
        # 1. Groundwater basics
        groundwater_basics = """# Groundwater Basics in Thailand

## Overview
Groundwater is a critical water resource in Thailand, particularly in agricultural regions like Suphan Buri.

## Aquifer Systems
Thailand has several major aquifer systems:
- **Shallow aquifers (0-50m)**: Seasonal, vulnerable to contamination
- **Medium aquifers (50-150m)**: Most productive, optimal for wells
- **Deep aquifers (150m+)**: More stable but expensive to access

## Optimal Drilling Depths
Research shows that wells drilled to 80-150m depth have:
- Success rate: 75-85%
- Sustainable water yield: 5-15 m³/hour
- Lower contamination risk
- Cost-effective operation

## Seasonal Variations
Thailand has two distinct seasons affecting groundwater:

### Rainy Season (May-October)
- Higher water table
- Increased recharge
- Better drilling conditions
- Success rate increases by 10-15%

### Dry Season (November-April)
- Lower water table
- Reduced flow rates
- More challenging drilling
- Higher risk of well failure

## Regional Characteristics - Suphan Buri
Suphan Buri province characteristics:
- Average depth to water: 10-30m
- Productive depth range: 80-120m
- Aquifer type: Alluvial deposits
- Water quality: Generally good, some salinity in eastern areas
"""
        
        # 2. Drilling guidelines
        drilling_guidelines = """# Well Drilling Guidelines - Dan Chang District

## Pre-Drilling Assessment

### Site Selection
1. Check proximity to contamination sources (>30m from septic systems)
2. Verify property boundaries and access
3. Review existing well data in the area
4. Conduct preliminary geophysical survey if budget allows

### Optimal Locations
- Avoid low-lying flood-prone areas
- Select higher ground when possible
- Consider distance from distribution points
- Check for underground utilities

## Drilling Specifications

### Recommended Depths by Purpose
- **Domestic use**: 80-100m
- **Agricultural irrigation**: 100-150m
- **Commercial/Industrial**: 120-180m

### Well Diameter
- Domestic: 6-8 inches (150-200mm)
- Agricultural: 8-12 inches (200-300mm)

### Casing Requirements
- Steel or UPVC casing required
- Minimum thickness: 5mm for steel
- Screen length: 20-40% of productive zone

## Cost Estimation (2025 prices)

### Drilling Costs
- Average: 1,200-1,500 THB per meter
- Includes: drilling, casing, screen
- Does not include: pump, electrical, permits

### Example Total Costs
- 80m well: 96,000-120,000 THB
- 120m well: 144,000-180,000 THB
- 150m well: 180,000-225,000 THB

### Additional Costs
- Pump system: 30,000-80,000 THB
- Electrical connection: 20,000-50,000 THB
- Permits and testing: 5,000-15,000 THB

## Best Practices

### Timing
- Ideal months: May-June (early rainy season)
- Avoid: Peak dry season (March-April)
- Plan 2-3 weeks for completion

### Contractor Selection
- Verify licenses and insurance
- Check references and past projects
- Get detailed written quotes
- Ensure warranty coverage

### Post-Drilling
- Water quality testing required
- Development period: 1-2 weeks
- Regular maintenance schedule
- Monitor water levels seasonally

## Common Issues and Solutions

### Low Yield
- May need deeper drilling
- Consider pump placement depth
- Check for screen clogging

### Water Quality Issues
- Test for bacterial contamination
- Check mineral content
- May need treatment system

### Seasonal Fluctuations
- Normal in shallow wells (<60m)
- Deep wells more stable
- Plan for dry season capacity
"""
        
        # 3. Regional geology
        regional_geology = """# Geological Profile - Dan Chang District, Suphan Buri

## Location
- Province: Suphan Buri
- District: Dan Chang (อำเภอด่านช้าง)
- Coordinates: 14.85-15.05°N, 99.50-99.75°E
- Elevation: 5-15m above sea level

## Geological Formation

### Surface Layer (0-10m)
- Clay and silt deposits
- Low permeability
- Seasonal saturation

### Upper Aquifer (10-50m)
- Sandy clay and fine sand
- Moderate permeability
- Seasonal water table fluctuation
- Vulnerable to contamination

### Middle Aquifer (50-150m) - PRIMARY TARGET
- Medium to coarse sand with gravel
- High permeability
- Stable water supply
- Best drilling target

### Deep Aquifer (150m+)
- Consolidated sediments
- Lower permeability than middle aquifer
- Very stable but expensive to access

## Hydrogeological Properties

### Water Table Depth
- Wet season: 5-15m
- Dry season: 15-30m
- Average: 20m

### Aquifer Productivity
- Transmissivity: 100-500 m²/day
- Specific yield: 15-25%
- Sustainable yield: 50-150 m³/day per well

### Water Quality
- pH: 6.5-7.5
- TDS: 200-600 mg/L
- Hardness: Moderate (150-300 mg/L as CaCO₃)
- Iron: Sometimes elevated (>0.3 mg/L)

## Success Factors by Location

### Eastern Dan Chang
- Better aquifer development
- Higher success rates (80-85%)
- Optimal depth: 90-120m

### Western Dan Chang
- More variable geology
- Success rate: 70-80%
- May need deeper drilling: 120-150m

### Central Dan Chang
- Most developed area
- High competition for water
- Recommend 100-130m depth

## Risk Factors

### High Risk Areas
- Former rice paddies with pesticide use
- Areas with industrial activity
- Locations near waste disposal sites

### Geological Challenges
- Clay lenses that reduce productivity
- Occasional limestone layers
- Variable sand thickness

## Recommendations

### Site Investigation
1. Review existing well logs within 500m
2. Check success/failure patterns
3. Consider geophysical survey for large projects

### Drilling Strategy
- Target middle aquifer (80-150m)
- Plan for continuous casing
- Budget for potential depth adjustments
- Have contingency for water testing
"""
        
        # 4. FAQ document
        faq = """# Frequently Asked Questions - Groundwater Wells

## General Questions

**Q: How deep should I drill?**
A: For Dan Chang district, 80-120m is optimal for most purposes. This depth typically:
- Reaches productive aquifers
- Provides stable water supply
- Costs 96,000-180,000 THB
- Has 75-85% success rate

**Q: When is the best time to drill?**
A: Early rainy season (May-June) is ideal because:
- Easier to locate water
- Better drilling conditions
- Higher success rates
- Contractor availability

**Q: How much does it cost?**
A: Total costs typically range:
- Drilling: 1,200-1,500 THB/meter
- 100m well total: ~150,000-250,000 THB (including pump)
- Operating costs: 500-2,000 THB/month (electricity)

## Technical Questions

**Q: Why do some wells fail?**
A: Common reasons:
1. Insufficient depth (stopped above productive zone)
2. Poor site selection (clay-rich areas)
3. Wrong season (drilling in peak dry season)
4. Inadequate casing or screen
5. Contamination from surface water

**Q: How long does a well last?**
A: With proper maintenance:
- Expected lifespan: 20-30 years
- Pump replacement: every 5-10 years
- Regular maintenance: essential
- Annual inspection: recommended

**Q: What about water quality?**
A: Dan Chang water typically:
- Safe for irrigation (always)
- Usually safe for drinking (test required)
- May need treatment for iron
- Generally low salinity

## Regulatory Questions

**Q: Do I need permits?**
A: Yes, for commercial use:
- Provincial water resources permit
- Environmental impact assessment (large wells)
- Domestic wells: simpler process
- Processing time: 1-3 months

**Q: Are there restrictions?**
A: Current regulations:
- Depth limits: Usually none for private wells
- Volume limits: May apply for commercial
- Spacing: Recommended 50m+ from neighbors
- Protection zones: 30m from contamination sources

## Maintenance Questions

**Q: What maintenance is needed?**
A: Regular tasks:
- Monthly: Check pump operation
- Quarterly: Inspect casing and wellhead
- Annually: Professional inspection
- Every 2-3 years: Clean screen if needed

**Q: How do I know if my well is failing?**
A: Warning signs:
- Decreased water flow
- Pump running longer
- Unusual sounds or vibrations
- Water quality changes
- Sand in water

## Cost and ROI Questions

**Q: Is it worth the investment?**
A: Typically yes if:
- Water bills >3,000 THB/month
- Agricultural use planned
- Public water unreliable
- ROI: Usually 3-7 years for agricultural use

**Q: Can I get financing?**
A: Options include:
- Bank of Agriculture and Agricultural Cooperatives (BAAC)
- Commercial bank agricultural loans
- Government subsidy programs
- Cooperative funding
"""
        
        # Save documents
        docs = {
            "groundwater_basics.md": groundwater_basics,
            "drilling_guidelines.md": drilling_guidelines,
            "regional_geology.md": regional_geology,
            "faq.md": faq
        }
        
        for filename, content in docs.items():
            filepath = self.docs_dir / filename
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
        
        return len(docs)


class RAGChatbot:
    """
    RAG-enabled chatbot that uses knowledge base for context.
    Integrates with OpenRouter API.
    """
    
    def __init__(self, kb_manager: KnowledgeBaseManager, openrouter_key: Optional[str] = None):
        """
        Initialize RAG chatbot.
        
        Args:
            kb_manager: Knowledge base manager instance
            openrouter_key: OpenRouter API key
        """
        self.kb = kb_manager
        self.api_key = openrouter_key or os.getenv("OPENROUTER_API_KEY")
        self.model = "anthropic/claude-3.5-haiku"
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
    
    def chat_with_context(
        self, 
        user_message: str,
        conversation_history: List[Dict[str, str]],
        n_context_docs: int = 3
    ) -> Dict[str, any]:
        """
        Chat with RAG context from knowledge base.
        
        Args:
            user_message: User's question
            conversation_history: Previous messages
            n_context_docs: Number of KB documents to retrieve
            
        Returns:
            Dict with response, sources, and cost
        """
        # Search knowledge base for relevant context
        kb_results = self.kb.search(user_message, n_results=n_context_docs)
        
        # Build context from KB results
        context_text = self._build_context_from_results(kb_results)
        
        # Build system prompt with context
        system_prompt = self._build_rag_system_prompt(context_text)
        
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
                "context_used": len(kb_results) > 0
            }
            
        except Exception as e:
            return {
                "response": f"❌ Error: {str(e)}",
                "sources": [],
                "cost": 0,
                "context_used": False
            }
    
    def _build_context_from_results(self, results: List[Dict]) -> str:
        """Build context string from KB search results."""
        if not results:
            return "No relevant documents found in knowledge base."
        
        context_parts = ["=== KNOWLEDGE BASE CONTEXT ===\n"]
        
        for i, result in enumerate(results, 1):
            content = result["content"][:500]  # Limit length
            source = result["metadata"].get("filename", "Unknown")
            context_parts.append(f"\n[Source {i}: {source}]\n{content}\n")
        
        context_parts.append("\n=== END CONTEXT ===")
        
        return "\n".join(context_parts)
    
    def _build_rag_system_prompt(self, context: str) -> str:
        """Build system prompt with RAG context."""
        return f"""You are an expert geological consultant specializing in groundwater management 
and well drilling in Thailand, particularly in the Suphan Buri region.

{context}

Use the above context from our knowledge base to provide accurate, detailed answers.
When you reference information from the context, mention which source it's from.
If the context doesn't fully answer the question, use your general knowledge but make it clear.

Provide practical, actionable advice. Use metric units. Be concise but thorough."""
    
    def _calculate_cost(self, usage: Dict) -> float:
        """Calculate cost (simplified)."""
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        
        # Claude Haiku pricing
        cost = (input_tokens * 0.80 + output_tokens * 4.0) / 1_000_000
        return round(cost, 6)


# Streamlit UI component for knowledge base management
class KnowledgeBaseUI:
    """Streamlit UI for managing knowledge base."""
    
    def __init__(self, kb_manager: KnowledgeBaseManager):
        self.kb = kb_manager
    
    def render_management_panel(self):
        """Render knowledge base management panel."""
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 📚 Knowledge Base")
        
        docs = self.kb.get_all_documents()
        st.sidebar.metric("Documents", len(docs))
        
        if st.sidebar.button("🔄 Refresh Index"):
            indexed = self.kb.index_directory(self.kb.docs_dir)
            st.sidebar.success(f"Indexed {indexed} documents")
        
        if st.sidebar.button("📝 Create Sample Docs"):
            count = self.kb.create_sample_knowledge_base()
            st.sidebar.success(f"Created {count} sample documents")
            # Re-index after creating
            self.kb.index_directory(self.kb.docs_dir)
            st.rerun()
        
        with st.sidebar.expander("📄 View Documents"):
            for doc_id, metadata in docs.items():
                st.caption(f"📄 {metadata.get('filename', doc_id)}")
                st.caption(f"   Category: {metadata.get('category', 'N/A')}")
                st.caption(f"   Chunks: {metadata.get('chunks', 0)}")


# Export main classes
__all__ = [
    "KnowledgeBaseManager",
    "RAGChatbot",
    "KnowledgeBaseUI"
]