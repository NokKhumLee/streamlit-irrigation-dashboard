#!/usr/bin/env python3
"""
Quick setup script for Knowledge Base and RAG system.
Run this script to initialize everything automatically.

Usage:
    python setup_knowledge_base.py
"""

import os
import sys
from pathlib import Path


def print_step(step_num, message):
    """Print formatted step message."""
    print(f"\n{'='*60}")
    print(f"STEP {step_num}: {message}")
    print('='*60)


def create_directory_structure():
    """Create all necessary directories."""
    print_step(1, "Creating directory structure")
    
    directories = [
        "geodash/knowledge_base/documents",
        "geodash/knowledge_base/reports",
        "geodash/knowledge_base/guidelines",
        "geodash/knowledge_base/.embeddings",
        "geodash/services",
    ]
    
    for directory in directories:
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        print(f"✅ Created: {directory}")
    
    # Create __init__.py for services
    init_file = Path("geodash/services/__init__.py")
    if not init_file.exists():
        init_file.touch()
        print(f"✅ Created: {init_file}")
    
    print("\n✅ Directory structure created successfully!")


def check_dependencies():
    """Check if required packages are installed."""
    print_step(2, "Checking dependencies")
    
    required_packages = {
        "chromadb": "chromadb",
        "pypdf": "pypdf",
        "requests": "requests",
    }
    
    missing_packages = []
    
    for package, pip_name in required_packages.items():
        try:
            __import__(package)
            print(f"✅ {package} is installed")
        except ImportError:
            print(f"❌ {package} is NOT installed")
            missing_packages.append(pip_name)
    
    if missing_packages:
        print(f"\n⚠️  Missing packages: {', '.join(missing_packages)}")
        print("\nInstall them with:")
        print(f"pip install {' '.join(missing_packages)}")
        
        response = input("\nInstall missing packages now? (y/n): ")
        if response.lower() == 'y':
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing_packages)
            print("\n✅ Packages installed successfully!")
        else:
            print("\n⚠️  Please install missing packages manually")
            return False
    else:
        print("\n✅ All dependencies are installed!")
    
    return True


def initialize_knowledge_base():
    """Initialize knowledge base and create sample documents."""
    print_step(3, "Initializing Knowledge Base")
    
    try:
        # Import after dependencies are checked
        from geodash.services.knowledge_base_rag import KnowledgeBaseManager
        
        print("Initializing Knowledge Base Manager...")
        kb = KnowledgeBaseManager()
        
        # Check if documents already exist
        existing_docs = kb.get_all_documents()
        
        if existing_docs:
            print(f"\n⚠️  Found {len(existing_docs)} existing documents")
            response = input("Recreate sample documents? (y/n): ")
            if response.lower() != 'y':
                print("Keeping existing documents...")
                return True
        
        # Create sample documents
        print("\nCreating sample documents...")
        count = kb.create_sample_knowledge_base()
        print(f"✅ Created {count} sample documents")
        
        # Index documents
        print("\nIndexing documents into vector database...")
        indexed = kb.index_directory(kb.docs_dir)
        print(f"✅ Indexed {indexed} documents")
        
        # Display created documents
        print("\n📚 Documents created:")
        for doc_id, metadata in kb.get_all_documents().items():
            print(f"   📄 {metadata.get('filename', doc_id)}")
            print(f"      Category: {metadata.get('category', 'N/A')}")
            print(f"      Chunks: {metadata.get('chunks', 0)}")
        
        print("\n✅ Knowledge Base initialized successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error initializing Knowledge Base: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False


def test_knowledge_base():
    """Test knowledge base search functionality."""
    print_step(4, "Testing Knowledge Base")
    
    try:
        from geodash.services.knowledge_base_rag import KnowledgeBaseManager
        
        kb = KnowledgeBaseManager()
        
        if not kb.collection:
            print("⚠️  Vector database not initialized (ChromaDB not available)")
            print("Search functionality will be limited")
            return True
        
        # Test search
        print("\nTesting search with query: 'optimal drilling depth'")
        results = kb.search("optimal drilling depth", n_results=3)
        
        if results:
            print(f"\n✅ Search successful! Found {len(results)} results:")
            for i, result in enumerate(results, 1):
                print(f"\n{i}. Source: {result['metadata'].get('filename', 'Unknown')}")
                print(f"   Preview: {result['content'][:150]}...")
                print(f"   Relevance: {1 - result['distance']:.2%}")
        else:
            print("\n⚠️  No results found. This might indicate an indexing issue.")
            return False
        
        print("\n✅ Knowledge Base is working correctly!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error testing Knowledge Base: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_api_key():
    """Check if OpenRouter API key is configured."""
    print_step(5, "Checking API Configuration")
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    if api_key:
        print(f"✅ OpenRouter API key is configured")
        print(f"   Key: {api_key[:15]}...{api_key[-4:]}")
    else:
        print("⚠️  OpenRouter API key not found")
        print("\nTo configure your API key:")
        print("1. Get free key from: https://openrouter.ai/keys")
        print("2. Set environment variable:")
        print("   export OPENROUTER_API_KEY='your-key-here'")
        print("\nOr configure it in the Streamlit app interface")
    
    return True


def verify_file_structure():
    """Verify all necessary files exist."""
    print_step(6, "Verifying file structure")
    
    required_files = [
        "geodash/services/knowledge_base_rag.py",
        "geodash/services/openrouter_chatbot.py",
        "geodash/services/__init__.py",
    ]
    
    optional_files = [
        "geodash/knowledge_base/documents/groundwater_basics.md",
        "geodash/knowledge_base/documents/drilling_guidelines.md",
        "geodash/knowledge_base/documents/regional_geology.md",
        "geodash/knowledge_base/documents/faq.md",
        "geodash/knowledge_base/metadata.json",
    ]
    
    print("\nRequired files:")
    all_required_exist = True
    for file_path in required_files:
        exists = Path(file_path).exists()
        status = "✅" if exists else "❌"
        print(f"   {status} {file_path}")
        if not exists:
            all_required_exist = False
    
    print("\nKnowledge base files:")
    for file_path in optional_files:
        exists = Path(file_path).exists()
        status = "✅" if exists else "⚠️ "
        print(f"   {status} {file_path}")
    
    if not all_required_exist:
        print("\n❌ Some required files are missing!")
        print("Make sure you have copied:")
        print("   - knowledge_base_rag.py")
        print("   - openrouter_chatbot.py")
        print("to geodash/services/")
        return False
    
    print("\n✅ File structure verified!")
    return True


def display_next_steps():
    """Display next steps after setup."""
    print_step(7, "Setup Complete!")
    
    print("""
✅ Knowledge Base system is ready!

📋 NEXT STEPS:

1. Start the Streamlit app:
   streamlit run app.py

2. Navigate to "AI Assistant" page

3. If not already configured, add your OpenRouter API key:
   - Get free key from: https://openrouter.ai/keys
   - You get $1 free credit (~1000 messages)

4. Start chatting! The AI will use your knowledge base automatically.

📚 KNOWLEDGE BASE FEATURES:

✓ 4 comprehensive documents pre-loaded:
  - Groundwater basics
  - Drilling guidelines  
  - Regional geology (Dan Chang)
  - FAQ (20+ questions)

✓ Vector search with semantic understanding
✓ Source attribution in responses
✓ Automatic context retrieval
✓ Support for PDF, TXT, MD, JSON files

💡 TIPS:

- Add your own documents to geodash/knowledge_base/documents/
- Upload reports to geodash/knowledge_base/reports/
- Use the sidebar to manage and refresh the knowledge base
- Ask specific questions for best results

📖 EXAMPLE QUESTIONS:

- "What is the optimal drilling depth for Dan Chang?"
- "How much does a 120m well cost?"
- "When is the best season for drilling?"
- "What are the geological characteristics of this region?"

🔧 TROUBLESHOOTING:

If you encounter issues:
1. Check logs in terminal
2. Verify ChromaDB is installed: pip list | grep chromadb
3. Ensure all files are in correct locations
4. Try rerunning this setup script

📚 For more help, see: KNOWLEDGE_BASE_SETUP.md

Happy drilling! 🏔️💧
""")


def main():
    """Main setup function."""
    print("""
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║   Knowledge Base & RAG Setup for Badan Dashboard          ║
║   Automated initialization script                         ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
""")
    
    steps = [
        ("Create directories", create_directory_structure),
        ("Check dependencies", check_dependencies),
        ("Initialize Knowledge Base", initialize_knowledge_base),
        ("Test functionality", test_knowledge_base),
        ("Check API configuration", check_api_key),
        ("Verify file structure", verify_file_structure),
    ]
    
    # Track success
    all_successful = True
    
    # Execute steps
    for step_name, step_func in steps:
        try:
            if not step_func():
                all_successful = False
                print(f"\n⚠️  {step_name} completed with warnings")
        except Exception as e:
            all_successful = False
            print(f"\n❌ {step_name} failed: {e}")
            import traceback
            traceback.print_exc()
    
    # Display results
    print("\n" + "="*60)
    if all_successful:
        print("🎉 SETUP COMPLETED SUCCESSFULLY!")
    else:
        print("⚠️  SETUP COMPLETED WITH WARNINGS")
        print("Some features may not work as expected")
    print("="*60)
    
    # Show next steps
    display_next_steps()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)