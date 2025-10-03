# geodash/pages/ai_assistant.py - UPDATED for bilingual support
"""
AI Assistant page - Bilingual RAG-enabled chatbot (Thai/English).
"""
from typing import Dict
import streamlit as st
import requests

from geodash.services.knowledge_base_rag import (
    KnowledgeBaseManager,
    BilingualRAGChatbot,
    KnowledgeBaseUI,
)


def validate_openrouter_key(api_key: str) -> tuple[bool, str]:
    """Validate OpenRouter API key."""
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
            return True, "✅ API key validated successfully! / ตรวจสอบ API key สำเร็จ!"
        elif response.status_code == 401:
            return False, "❌ Invalid API key / API key ไม่ถูกต้อง"
        elif response.status_code == 402:
            return True, "⚠️ API key valid but no credits / API key ถูกต้องแต่ไม่มีเครดิต"
        else:
            return False, f"❌ Error validating key / ข้อผิดพลาดในการตรวจสอบ: {response.status_code}"
    
    except requests.exceptions.Timeout:
        return False, "❌ Connection timeout / หมดเวลาการเชื่อมต่อ"
    except Exception as e:
        return False, f"❌ Validation error / ข้อผิดพลาด: {str(e)}"


def render_api_key_form() -> bool:
    """Render bilingual API key configuration form."""
    st.info("🔐 **Secure API Key Required / ต้องการ API Key**")
    
    with st.form("api_key_form"):
        st.markdown("#### 🔑 Enter API Key / ใส่ API Key")
        
        api_key_input = st.text_input(
            "OpenRouter API Key",
            type="password",
            placeholder="sk-or-v1-...",
            help="Your key is stored in memory only / คีย์ของคุณจะถูกเก็บในหน่วยความจำเท่านั้น"
        )
        
        col_submit, col_demo = st.columns(2)
        
        with col_submit:
            submit = st.form_submit_button("🔐 Connect / เชื่อมต่อ", type="primary", use_container_width=True)
        
        with col_demo:
            demo = st.form_submit_button("👀 View Demo / ดูตัวอย่าง", use_container_width=True)
        
        if submit and api_key_input:
            if api_key_input.startswith("sk-or-"):
                with st.spinner("🔍 Validating API key / กำลังตรวจสอบ API key..."):
                    is_valid, message = validate_openrouter_key(api_key_input)
                    
                    if is_valid:
                        st.session_state.openrouter_api_key = api_key_input
                        st.session_state.api_key_validated = True
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
            else:
                st.error("❌ Invalid key format / รูปแบบคีย์ไม่ถูกต้อง")
        
        if demo:
            st.session_state.demo_mode = True
            st.rerun()
    
    # Demo mode
    if st.session_state.get("demo_mode"):
        st.info("**👀 Demo Mode / โหมดตัวอย่าง**")
        
        # English demo
        st.markdown("**English Example:**")
        with st.chat_message("user"):
            st.write("What is the optimal drilling depth for Dan Chang?")
        
        with st.chat_message("assistant"):
            st.write("""
            For Dan Chang District, the optimal drilling depth is 90-120m in eastern areas 
            and 120-150m in western areas, with success rates of 80-85%.
            """)
            st.caption("🇬🇧 English | 📚 Sources: regional_geology.md")
        
        # Thai demo
        st.markdown("**Thai Example / ตัวอย่างภาษาไทย:**")
        with st.chat_message("user"):
            st.write("ความลึกที่เหมาะสมในการขุดเจาะบ่อในพื้นที่ด่านช้างคือเท่าไหร่?")
        
        with st.chat_message("assistant"):
            st.write("""
            สำหรับอำเภอด่านช้าง ความลึกที่เหมาะสมในการขุดเจาะบ่อคือ 90-120 เมตรในพื้นที่ทางตะวันออก 
            และ 120-150 เมตรในพื้นที่ทางตะวันตก โดยมีอัตราความสำเร็จ 80-85%
            """)
            st.caption("🇹🇭 Thai / ไทย | 📚 Sources / แหล่งที่มา: regional_geology.md")
        
        if st.button("🔙 Back / กลับ"):
            st.session_state.demo_mode = False
            st.rerun()
    
    return False


def render_ai_assistant(data: Dict) -> None:
    """
    Render the bilingual AI Assistant page.
    
    Args:
        data: Complete dashboard data
    """
    
    # Initialize session state
    if "openrouter_api_key" not in st.session_state:
        st.session_state.openrouter_api_key = None
    if "api_key_validated" not in st.session_state:
        st.session_state.api_key_validated = False
    if "preferred_language" not in st.session_state:
        st.session_state.preferred_language = None
    
    # Initialize knowledge base
    if "kb_manager" not in st.session_state:
        st.session_state.kb_manager = KnowledgeBaseManager()
        
        if not st.session_state.kb_manager.get_all_documents():
            with st.spinner("📚 Initializing knowledge base / กำลังเตรียมฐานความรู้..."):
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
        st.markdown("### 🔐 API Status / สถานะ API")
        masked_key = st.session_state.openrouter_api_key[:15] + "..." + st.session_state.openrouter_api_key[-4:]
        st.success("✅ Connected / เชื่อมต่อแล้ว")
        st.caption(f"Key: {masked_key}")
        
        # Language selector
        st.markdown("---")
        st.markdown("### 🌐 Language / ภาษา")
        language_pref = st.selectbox(
            "Preference / ตั้งค่า",
            options=["Auto Detect / ตรวจจับอัตโนมัติ", "English / อังกฤษ", "Thai / ไทย"],
            key="language_selector"
        )
        
        if "English" in language_pref:
            st.session_state.preferred_language = "en"
        elif "Thai" in language_pref or "ไทย" in language_pref:
            st.session_state.preferred_language = "th"
        else:
            st.session_state.preferred_language = None
        
        if st.button("🔄 Change Key / เปลี่ยนคีย์", use_container_width=True):
            st.session_state.openrouter_api_key = None
            st.session_state.rag_chatbot = None
            st.rerun()
        
        if st.button("🚪 Disconnect / ตัดการเชื่อมต่อ", use_container_width=True):
            st.session_state.openrouter_api_key = None
            st.session_state.rag_chat_history = []
            st.session_state.rag_chatbot = None
            st.rerun()
    
    # Initialize chatbot
    if "rag_chatbot" not in st.session_state:
        st.session_state.rag_chatbot = BilingualRAGChatbot(kb, st.session_state.openrouter_api_key)
        st.session_state.rag_chat_history = []
        st.session_state.rag_total_cost = 0.0
        st.session_state.rag_message_count = 0
    
    rag_bot = st.session_state.rag_chatbot
    
    # Dashboard stats
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    docs = kb.get_all_documents()
    
    with col1:
        st.metric("📚 Documents / เอกสาร", len(docs))
    with col2:
        st.metric("💬 Messages / ข้อความ", st.session_state.rag_message_count)
    with col3:
        st.metric("💵 Cost / ค่าใช้จ่าย", f"${st.session_state.rag_total_cost:.4f}")
    with col4:
        avg = st.session_state.rag_total_cost / max(st.session_state.rag_message_count, 1)
        st.metric("📊 Avg/Msg / เฉลี่ย", f"${avg:.5f}")
    
    st.markdown("---")
    
    # Settings and suggestions
    with st.expander("⚙️ Settings & Suggestions / ตั้งค่าและคำแนะนำ"):
        col_s, col_q = st.columns([1, 2])
        
        with col_s:
            n_context = st.slider("Context Docs / เอกสารบริบท", 1, 10, 3)
        
        with col_q:
            st.markdown("**💡 Try asking / ลองถาม:**")
            
            # English questions
            st.markdown("**English:**")
            suggestions_en = [
                "What's the optimal drilling depth for Dan Chang?",
                "How much does a 120m well cost?",
                "When is the best season for drilling?",
            ]
            for i, q in enumerate(suggestions_en):
                if st.button(q, key=f"suggest_en_{i}", use_container_width=True):
                    st.session_state.suggested_q = q
                    st.rerun()
            
            # Thai questions
            st.markdown("**ภาษาไทย:**")
            suggestions_th = [
                "ความลึกที่เหมาะสมในการขุดเจาะบ่อคือเท่าไหร่?",
                "ค่าใช้จ่ายในการขุดเจาะบ่อลึก 120 เมตรเท่าไหร่?",
                "ฤดูกาลไหนเหมาะสมที่สุดสำหรับการขุดเจาะ?",
            ]
            for i, q in enumerate(suggestions_th):
                if st.button(q, key=f"suggest_th_{i}", use_container_width=True):
                    st.session_state.suggested_q = q
                    st.rerun()
    
    # Chat display
    for msg in st.session_state.rag_chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if msg["role"] == "assistant":
                # Show metadata
                meta_parts = []
                
                if msg.get("sources"):
                    with st.expander("📚 Sources / แหล่งที่มา"):
                        for src in msg["sources"]:
                            st.caption(f"📄 {src}")
                
                if msg.get("cost", 0) > 0:
                    meta_parts.append(f"💵 ${msg['cost']:.6f}")
                
                if msg.get("language"):
                    lang_label = "🇹🇭 Thai / ไทย" if msg["language"] == "th" else "🇬🇧 English / อังกฤษ"
                    meta_parts.append(lang_label)
                
                if meta_parts:
                    st.caption(" | ".join(meta_parts))
    
    # Chat input
    user_input = st.session_state.pop("suggested_q", None) or st.chat_input(
        "Ask anything... / ถามอะไรก็ได้..."
    )
    
    if user_input:
        # User message
        with st.chat_message("user"):
            st.write(user_input)
        
        st.session_state.rag_chat_history.append({"role": "user", "content": user_input})
        
        # Get response
        with st.chat_message("assistant"):
            with st.spinner("🔍 Searching... / กำลังค้นหา..."):
                result = rag_bot.chat_with_context(
                    user_input,
                    [{"role": msg["role"], "content": msg["content"]} 
                     for msg in st.session_state.rag_chat_history[:-1]],
                    n_context_docs=n_context if 'n_context' in locals() else 3,
                    force_language=st.session_state.preferred_language
                )
            
            st.write(result["response"])
            
            # Show metadata
            meta_parts = []
            
            if result.get("sources"):
                with st.expander("📚 Sources / แหล่งที่มา"):
                    for src in result["sources"]:
                        st.caption(f"📄 {src}")
            
            if result.get("cost", 0) > 0:
                meta_parts.append(f"💵 ${result['cost']:.6f}")
            
            if result.get("language"):
                lang_label = "🇹🇭 Thai / ไทย" if result["language"] == "th" else "🇬🇧 English / อังกฤษ"
                meta_parts.append(lang_label)
            
            if meta_parts:
                st.caption(" | ".join(meta_parts))
        
        # Add to history
        st.session_state.rag_chat_history.append({
            "role": "assistant",
            "content": result["response"],
            "sources": result.get("sources", []),
            "cost": result.get("cost", 0),
            "language": result.get("language", "en")
        })
        
        st.session_state.rag_message_count += 1
        st.session_state.rag_total_cost += result.get("cost", 0)
        st.rerun()
    
    # Welcome message
    if not st.session_state.rag_chat_history:
        st.info("""
        **👋 Welcome! I can help with: / ยินดีต้อนรับ! ฉันช่วยเรื่อง:**
        
        **English:**
        - 🏔️ Optimal drilling depths
        - 💰 Cost estimation
        - 📋 Best practices
        - 🌍 Regional geology
        
        **ภาษาไทย:**
        - 🏔️ ความลึกที่เหมาะสมในการขุดเจาะ
        - 💰 การประมาณการค่าใช้จ่าย
        - 📋 แนวทางปฏิบัติที่ดี
        - 🌍 ธรณีวิทยาเฉพาะพื้นที่
        """)
        
        st.markdown("---")
        st.markdown("**🎯 Language Detection / การตรวจจับภาษา:**")
        st.info("""
        The AI automatically detects your language and responds accordingly:
        - Type in **English** → Get English response
        - พิมพ์เป็น**ภาษาไทย** → ได้คำตอบเป็นภาษาไทย
        
        You can also force a specific language using the dropdown in the sidebar.
        คุณสามารถเลือกภาษาเฉพาะได้ที่แถบด้านข้าง
        """)