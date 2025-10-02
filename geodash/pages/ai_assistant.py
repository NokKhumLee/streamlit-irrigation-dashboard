"""
AI Assistant page - RAG-enabled chatbot with secure API key management.
"""
from typing import Dict
import streamlit as st
import requests

from geodash.services.knowledge_base_rag import (
    KnowledgeBaseManager,
    RAGChatbot,
    KnowledgeBaseUI,
)


def validate_openrouter_key(api_key: str) -> tuple[bool, str]:
    """
    Validate OpenRouter API key by making a test call.
    
    Args:
        api_key: API key to validate
        
    Returns:
        Tuple of (is_valid, message)
    """
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        test_payload = {
            "model": "anthropic/claude-3.5-haiku",
            "messages": [{"role": "user", "content": "test"}],
            "max_tokens": 10
        }
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=test_payload,
            timeout=10
        )
        
        if response.status_code == 200:
            return True, "✅ API key validated successfully!"
        elif response.status_code == 401:
            return False, "❌ Invalid API key. Please check and try again."
        elif response.status_code == 402:
            return True, "⚠️ API key valid but no credits remaining. Please add credits."
        else:
            return False, f"❌ Error validating key: {response.status_code}"
    
    except requests.exceptions.Timeout:
        return False, "❌ Connection timeout. Please check your internet."
    except Exception as e:
        return False, f"❌ Validation error: {str(e)}"


def render_api_key_form() -> bool:
    """
    Render API key configuration form.
    
    Returns:
        True if key was configured, False otherwise
    """
    st.info("🔐 **Secure API Key Required**")
    
    with st.form("api_key_form"):
        st.markdown("#### 🔑 Enter API Key")
        
        api_key_input = st.text_input(
            "OpenRouter API Key",
            type="password",
            placeholder="sk-or-v1-...",
            help="Your key is stored in memory only"
        )
        
        col_submit, col_demo = st.columns(2)
        
        with col_submit:
            submit = st.form_submit_button("🔐 Connect", type="primary", use_container_width=True)
        
        with col_demo:
            demo = st.form_submit_button("👀 View Demo", use_container_width=True)
        
        if submit and api_key_input:
            if api_key_input.startswith("sk-or-"):
                with st.spinner("🔍 Validating API key..."):
                    is_valid, message = validate_openrouter_key(api_key_input)
                    
                    if is_valid:
                        st.session_state.openrouter_api_key = api_key_input
                        st.session_state.api_key_validated = True
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
            else:
                st.error("❌ Invalid key format. Should start with 'sk-or-v1-'")
        
        if demo:
            st.session_state.demo_mode = True
            st.rerun()
    
    # Show demo mode if requested
    if st.session_state.get("demo_mode"):
        st.info("**👀 Demo Mode** - Example conversation:")
        
        with st.chat_message("user"):
            st.write("What is the optimal drilling depth for Dan Chang?")
        
        with st.chat_message("assistant"):
            st.write("""
            For Dan Chang District, the optimal drilling depth is 90-120m in eastern areas 
            and 120-150m in western areas, with success rates of 80-85%.
            """)
            with st.expander("📚 Sources"):
                st.caption("📄 regional_geology.md")
        
        if st.button("🔙 Back"):
            st.session_state.demo_mode = False
            st.rerun()
    
    return False


def render_ai_assistant(data: Dict) -> None:
    """
    Render the AI Assistant page with secure API key management.
    
    Args:
        data: Complete dashboard data
    """
    
    # Initialize session state
    if "openrouter_api_key" not in st.session_state:
        st.session_state.openrouter_api_key = None
    if "api_key_validated" not in st.session_state:
        st.session_state.api_key_validated = False
    
    # Initialize knowledge base
    if "kb_manager" not in st.session_state:
        st.session_state.kb_manager = KnowledgeBaseManager()
        
        if not st.session_state.kb_manager.get_all_documents():
            with st.spinner("📚 Initializing knowledge base..."):
                st.session_state.kb_manager.create_sample_knowledge_base()
                indexed = st.session_state.kb_manager.index_directory(
                    st.session_state.kb_manager.docs_dir
                )
    
    kb = st.session_state.kb_manager
    
    # Render KB management in sidebar
    kb_ui = KnowledgeBaseUI(kb)
    kb_ui.render_management_panel()
    
    # Check if API key configured
    if not st.session_state.openrouter_api_key:
        render_api_key_form()
        return
    
    # Show API status in sidebar
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 🔐 API Status")
        masked_key = st.session_state.openrouter_api_key[:15] + "..." + st.session_state.openrouter_api_key[-4:]
        st.success("✅ Connected")
        st.caption(f"Key: {masked_key}")
        
        if st.button("🔄 Change Key", use_container_width=True):
            st.session_state.openrouter_api_key = None
            st.session_state.rag_chatbot = None
            st.rerun()
        
        if st.button("🚪 Disconnect", use_container_width=True):
            st.session_state.openrouter_api_key = None
            st.session_state.rag_chat_history = []
            st.session_state.rag_chatbot = None
            st.rerun()
    
    # Initialize chatbot
    if "rag_chatbot" not in st.session_state:
        st.session_state.rag_chatbot = RAGChatbot(kb, st.session_state.openrouter_api_key)
        st.session_state.rag_chat_history = []
        st.session_state.rag_total_cost = 0.0
        st.session_state.rag_message_count = 0
    
    rag_bot = st.session_state.rag_chatbot
    
    # Dashboard stats
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    docs = kb.get_all_documents()
    
    with col1:
        st.metric("📚 Documents", len(docs))
    with col2:
        st.metric("💬 Messages", st.session_state.rag_message_count)
    with col3:
        st.metric("💵 Cost", f"${st.session_state.rag_total_cost:.4f}")
    with col4:
        avg = st.session_state.rag_total_cost / max(st.session_state.rag_message_count, 1)
        st.metric("📊 Avg/Msg", f"${avg:.5f}")
    
    st.markdown("---")
    
    # Settings and suggestions
    with st.expander("⚙️ Settings & Suggestions"):
        col_s, col_q = st.columns([1, 2])
        
        with col_s:
            n_context = st.slider("Context Docs", 1, 10, 3)
        
        with col_q:
            st.markdown("**💡 Try asking:**")
            suggestions = [
                "What's the optimal drilling depth for Dan Chang?",
                "How much does a 120m well cost?",
                "When is the best season for drilling?",
            ]
            for i, q in enumerate(suggestions):
                if st.button(q, key=f"suggest_{i}", use_container_width=True):
                    st.session_state.suggested_q = q
                    st.rerun()
    
    # Chat display
    for msg in st.session_state.rag_chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if msg["role"] == "assistant" and msg.get("sources"):
                with st.expander("📚 Sources"):
                    for src in msg["sources"]:
                        st.caption(f"📄 {src}")
    
    # Chat input
    user_input = st.session_state.pop("suggested_q", None) or st.chat_input("Ask anything...")
    
    if user_input:
        # User message
        st.session_state.rag_chat_history.append({"role": "user", "content": user_input})
        
        # Get response
        with st.spinner("🔍 Searching..."):
            result = rag_bot.chat_with_context(
                user_input,
                st.session_state.rag_chat_history[:-1],
                n_context_docs=n_context if 'n_context' in locals() else 3
            )
        
        # Assistant message
        st.session_state.rag_chat_history.append({
            "role": "assistant",
            "content": result["response"],
            "sources": result.get("sources", []),
            "cost": result.get("cost", 0)
        })
        
        st.session_state.rag_message_count += 1
        st.session_state.rag_total_cost += result.get("cost", 0)
        st.rerun()
    
    # Welcome message
    if not st.session_state.rag_chat_history:
        st.info("""
        **👋 Welcome! I can help with:**
        - 🏔️ Optimal drilling depths
        - 💰 Cost estimation
        - 📋 Best practices
        - 🌍 Regional geology
        """)