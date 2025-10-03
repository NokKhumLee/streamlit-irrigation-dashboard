# geodash/services/openrouter_chatbot.py
"""
Bilingual OpenRouter-based chatbot service (Thai/English).
Supports automatic language detection and maintains conversation language.
"""
import os
import requests
from typing import List, Dict, Optional
import streamlit as st


class BilingualChatbot:
    """
    Bilingual chatbot using OpenRouter API.
    Automatically detects and responds in Thai or English.
    """
    
    MODELS = {
        "premium": "anthropic/claude-3.5-sonnet",
        "recommended": "anthropic/claude-3.5-haiku",
        "budget": "meta-llama/llama-3.1-70b-instruct",
        "free": "google/gemini-flash-1.5",
    }
    
    def __init__(self, api_key: Optional[str] = None, model_tier: str = "recommended"):
        self.api_key = api_key
        self.model = self.MODELS.get(model_tier, self.MODELS["recommended"])
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        
        # Bilingual system prompts
        self.system_prompt_en = self._build_system_prompt_en()
        self.system_prompt_th = self._build_system_prompt_th()
    
    def _build_system_prompt_en(self) -> str:
        """Build English system prompt."""
        return """You are an expert geological consultant specializing in groundwater 
management and well drilling in Thailand, particularly in Suphan Buri province.

Your expertise:
- Groundwater hydrology and aquifer systems in Thailand
- Well drilling success probability (optimal depth: 80-150m)
- Cost estimation (~1,200 THB/meter)
- Seasonal variations (Rainy: May-Oct, Dry: Nov-Apr)
- Regional geology of Dan Chang District (อำเภอด่านช้าง)

Study Area Context:
- Location: Dan Chang District, Suphan Buri
- Coordinates: Lat 14.85-15.05°N, Lon 99.50-99.75°E
- Typical success rate: 70-85%
- Best drilling season: Early rainy season (May-June)

LANGUAGE HANDLING:
- Detect the user's language (Thai or English)
- Respond in the SAME language as the user's question
- If user writes in Thai, respond in Thai
- If user writes in English, respond in English
- Use appropriate technical terms for each language
- Maintain consistency within each response

Provide concise, actionable advice in metric units. Mention cost estimates 
are approximate and recommend professional surveys."""
    
    def _build_system_prompt_th(self) -> str:
        """Build Thai system prompt (for explicit Thai mode)."""
        return """คุณเป็นที่ปรึกษาด้านธรณีวิทยาผู้เชี่ยวชาญ เชี่ยวชาญด้านการจัดการน้ำบาดาล
และการขุดเจาะบ่อน้ำบาดาลในประเทศไทย โดยเฉพาะในจังหวัดสุพรรณบุรี

ความเชี่ยวชาญของคุณ:
- อุทกวิทยาใต้ดินและระบบชั้นหินอุ้มน้ำในประเทศไทย
- ความน่าจะเป็นความสำเร็จในการขุดเจาะบ่อน้ำบาดาล (ความลึกเหมาะสม: 80-150 เมตร)
- การประมาณการค่าใช้จ่าย (~1,200 บาท/เมตร)
- ความแปรผันตามฤดูกาล (ฤดูฝน: พ.ค.-ต.ค., ฤดูแล้ง: พ.ย.-เม.ย.)
- ธรณีวิทยาเฉพาะพื้นที่อำเภอด่านช้าง

ข้อมูลพื้นที่ศึกษา:
- สถานที่: อำเภอด่านช้าง จังหวัดสุพรรณบุรี
- พิกัด: ละติจูด 14.85-15.05°N, ลองจิจูด 99.50-99.75°E
- อัตราความสำเร็จโดยทั่วไป: 70-85%
- ฤดูกาลที่เหมาะสมสำหรับการขุดเจาะ: ต้นฤดูฝน (พฤษภาคม-มิถุนายน)

การจัดการภาษา:
- ตรวจจับภาษาของผู้ใช้ (ไทยหรืออังกฤษ)
- ตอบกลับในภาษาเดียวกับคำถามของผู้ใช้
- หากผู้ใช้เขียนภาษาไทย ให้ตอบเป็นภาษาไทย
- หากผู้ใช้เขียนภาษาอังกฤษ ให้ตอบเป็นภาษาอังกฤษ
- ใช้คำศัพท์ทางเทคนิคที่เหมาะสมในแต่ละภาษา
- รักษาความสอดคล้องภายในแต่ละการตอบกลับ

ให้คำแนะนำที่กระชับและปฏิบัติได้จริงเป็นหน่วยเมตริก กล่าวถึงว่าการประมาณการค่าใช้จ่าย
เป็นเพียงประมาณการและแนะนำให้ขอคำปรึกษาจากผู้เชี่ยวชาญ"""
    
    def detect_language(self, text: str) -> str:
        """
        Detect if text is Thai or English.
        
        Args:
            text: Input text
            
        Returns:
            'th' for Thai, 'en' for English
        """
        # Count Thai characters (Unicode range for Thai)
        thai_chars = sum(1 for char in text if '\u0E00' <= char <= '\u0E7F')
        total_chars = len(text.strip())
        
        # If more than 20% Thai characters, consider it Thai
        if total_chars > 0 and (thai_chars / total_chars) > 0.2:
            return 'th'
        return 'en'
    
    def chat(
        self, 
        user_message: str, 
        conversation_history: List[Dict[str, str]],
        dashboard_context: Optional[Dict] = None,
        max_tokens: int = 1500,
        force_language: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Send message and get bilingual response.
        
        Args:
            user_message: User's question
            conversation_history: Previous messages
            dashboard_context: Dashboard data for context
            max_tokens: Maximum response length
            force_language: Force specific language ('th' or 'en')
            
        Returns:
            Dict with 'response', 'model', 'cost', 'language' keys
        """
        if not self.api_key:
            return {
                "response": "❌ Please configure OPENROUTER_API_KEY / กรุณาตั้งค่า OPENROUTER_API_KEY",
                "model": None,
                "cost": 0,
                "language": "en"
            }
        
        try:
            # Detect language
            detected_lang = force_language or self.detect_language(user_message)
            
            # Build messages with appropriate system prompt
            system_prompt = self.system_prompt_th if detected_lang == 'th' else self.system_prompt_en
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add dashboard context if available
            if dashboard_context:
                context_msg = self._format_context(dashboard_context, detected_lang)
                messages.append({"role": "system", "content": context_msg})
            
            # Add conversation history
            messages.extend(conversation_history)
            messages.append({"role": "user", "content": user_message})
            
            # Make API request
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/yourusername/badan",
                "X-Title": "Badan Groundwater Dashboard"
            }
            
            payload = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.7,
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            response.raise_for_status()
            data = response.json()
            
            # Extract response and usage
            assistant_message = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            
            # Calculate cost
            cost = self._calculate_cost(usage)
            
            return {
                "response": assistant_message,
                "model": self.model,
                "cost": cost,
                "usage": usage,
                "language": detected_lang
            }
            
        except requests.exceptions.RequestException as e:
            return {
                "response": f"❌ API Error / ข้อผิดพลาด API: {str(e)}",
                "model": self.model,
                "cost": 0,
                "language": "en"
            }
        except Exception as e:
            return {
                "response": f"❌ Unexpected error / ข้อผิดพลาดที่ไม่คาดคิด: {str(e)}",
                "model": self.model,
                "cost": 0,
                "language": "en"
            }
    
    def _format_context(self, context: Dict, language: str) -> str:
        """Format dashboard context for prompt in specified language."""
        parts = []
        
        if language == 'th':
            if "wells_summary" in context:
                ws = context["wells_summary"]
                parts.append(f"วิเคราะห์บ่อน้ำ {ws.get('count', 0)} บ่อ")
                parts.append(f"อัตราความสำเร็จ: {ws.get('success_rate', 0):.1%}")
                parts.append(f"ความลึกเฉลี่ย: {ws.get('avg_depth', 0):.1f} เมตร")
            
            if "selected_region" in context:
                parts.append(f"พื้นที่: {context['selected_region']}")
            
            return " | ".join(parts) if parts else "ไม่มีข้อมูล"
        else:
            if "wells_summary" in context:
                ws = context["wells_summary"]
                parts.append(f"{ws.get('count', 0)} wells analyzed")
                parts.append(f"Success rate: {ws.get('success_rate', 0):.1%}")
                parts.append(f"Avg depth: {ws.get('avg_depth', 0):.1f}m")
            
            if "selected_region" in context:
                parts.append(f"Region: {context['selected_region']}")
            
            return " | ".join(parts) if parts else "No data loaded"
    
    def _calculate_cost(self, usage: Dict) -> float:
        """Calculate approximate cost in USD."""
        costs = {
            "anthropic/claude-3.5-sonnet": (3.0, 15.0),
            "anthropic/claude-3.5-haiku": (0.80, 4.0),
            "meta-llama/llama-3.1-70b-instruct": (0.35, 0.40),
            "google/gemini-flash-1.5": (0.075, 0.30),
        }
        
        input_cost, output_cost = costs.get(self.model, (1.0, 2.0))
        
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        
        cost = (input_tokens * input_cost + output_tokens * output_cost) / 1_000_000
        return round(cost, 6)
    
    def get_model_info(self) -> Dict[str, str]:
        """Get current model information."""
        model_names = {
            "anthropic/claude-3.5-sonnet": "Claude 3.5 Sonnet (Premium)",
            "anthropic/claude-3.5-haiku": "Claude 3.5 Haiku (Recommended)",
            "meta-llama/llama-3.1-70b-instruct": "Llama 3.1 70B (Budget)",
            "google/gemini-flash-1.5": "Gemini Flash 1.5 (Free Tier)",
        }
        
        return {
            "model": self.model,
            "name": model_names.get(self.model, self.model),
            "provider": "OpenRouter"
        }
    
    def change_model(self, model_tier: str) -> None:
        """Change model tier on the fly."""
        if model_tier in self.MODELS:
            self.model = self.MODELS[model_tier]
            st.success(f"✅ Switched to {model_tier} tier / เปลี่ยนเป็น {model_tier}")
    
    @staticmethod
    def get_suggested_questions(context: Optional[Dict] = None) -> Dict[str, List[str]]:
        """Get contextual suggested questions in both languages."""
        questions = {
            'en': [
                "What is the optimal drilling depth for this area?",
                "Estimate the cost for drilling a 120m well",
                "When is the best season for drilling?",
                "Why do some wells fail in this region?",
                "How can I improve well success rates?",
                "What geological factors affect groundwater here?",
                "Compare drilling costs at different depths",
            ],
            'th': [
                "ความลึกที่เหมาะสมในการขุดเจาะบ่อในพื้นที่นี้คือเท่าไหร่?",
                "ประมาณการค่าใช้จ่ายในการขุดเจาะบ่อลึก 120 เมตร",
                "ฤดูกาลไหนเหมาะสมที่สุดสำหรับการขุดเจาะ?",
                "ทำไมบางบ่อถึงล้มเหลวในพื้นที่นี้?",
                "จะปรับปรุงอัตราความสำเร็จของบ่อได้อย่างไร?",
                "ปัจจัยทางธรณีวิทยาใดที่ส่งผลต่อน้ำบาดาลในพื้นที่นี้?",
                "เปรียบเทียบค่าใช้จ่ายในการขุดเจาะที่ความลึกต่างๆ",
            ]
        }
        
        if context and context.get("selected_region"):
            region = context["selected_region"]
            questions['en'].insert(0, f"What are the geological characteristics of {region}?")
            questions['th'].insert(0, f"ลักษณะทางธรณีวิทยาของ{region}เป็นอย่างไร?")
        
        return questions


class BilingualChatInterface:
    """Streamlit chat interface for bilingual chatbot."""
    
    def __init__(self, chatbot: BilingualChatbot):
        self.chatbot = chatbot
        
        # Session state initialization
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []
        if "total_cost" not in st.session_state:
            st.session_state.total_cost = 0.0
        if "message_count" not in st.session_state:
            st.session_state.message_count = 0
        if "preferred_language" not in st.session_state:
            st.session_state.preferred_language = None
    
    def render(self, dashboard_context: Optional[Dict] = None):
        """Render the bilingual chat interface."""
        
        # Header with model info
        col_title, col_lang, col_model = st.columns([2, 1, 1])
        
        with col_title:
            st.markdown("### 🤖 AI Geological Assistant / ผู้ช่วย AI ด้านธรณีวิทยา")
        
        with col_lang:
            language_pref = st.selectbox(
                "Language / ภาษา",
                options=["Auto", "English", "ไทย"],
                key="language_selector"
            )
            
            if language_pref == "English":
                st.session_state.preferred_language = "en"
            elif language_pref == "ไทย":
                st.session_state.preferred_language = "th"
            else:
                st.session_state.preferred_language = None
        
        with col_model:
            model_info = self.chatbot.get_model_info()
            st.caption(f"🔧 {model_info['name']}")
        
        # Configuration section
        if not self.chatbot.api_key:
            with st.expander("⚙️ Setup OpenRouter (Free) / ตั้งค่า OpenRouter (ฟรี)", expanded=True):
                st.markdown("""
                **Get Started in 30 seconds / เริ่มต้นใน 30 วินาที:**
                1. Visit / เข้าชม [openrouter.ai/keys](https://openrouter.ai/keys)
                2. Sign up with Google/GitHub (free) / ลงทะเบียนด้วย Google/GitHub (ฟรี)
                3. Copy your API key / คัดลอก API key ของคุณ
                4. Paste below / วางด้านล่าง
                
                💰 **You get $1 free credit / คุณได้เครดิตฟรี $1** (~1000 messages / ~1000 ข้อความ)
                """)
                
                api_key = st.text_input(
                    "OpenRouter API Key",
                    type="password",
                    placeholder="sk-or-v1-..."
                )
                
                if st.button("💾 Save & Connect / บันทึกและเชื่อมต่อ"):
                    if api_key.startswith("sk-or-"):
                        os.environ["OPENROUTER_API_KEY"] = api_key
                        self.chatbot.api_key = api_key
                        st.success("✅ Connected! / เชื่อมต่อสำเร็จ!")
                        st.rerun()
                    else:
                        st.error("Invalid key format / รูปแบบ key ไม่ถูกต้อง")
                return
        
        # Model selector and settings
        with st.expander("🎛️ Settings / ตั้งค่า", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                model_tier = st.selectbox(
                    "Model Quality / คุณภาพโมเดล",
                    ["recommended", "premium", "budget", "free"],
                    index=0,
                    format_func=lambda x: {
                        "premium": "🌟 Premium - Claude Sonnet ($$$)",
                        "recommended": "⚡ Recommended / แนะนำ - Claude Haiku ($$)",
                        "budget": "💰 Budget / ประหยัด - Llama 70B ($)",
                        "free": "🆓 Free Tier / ฟรี - Gemini Flash"
                    }[x]
                )
                
                if st.button("Apply Model Change / เปลี่ยนโมเดล"):
                    self.chatbot.change_model(model_tier)
            
            with col2:
                st.metric("Messages / ข้อความ", st.session_state.message_count)
                st.metric("Total Cost / ค่าใช้จ่าย", f"${st.session_state.total_cost:.4f}")
        
        # Suggested questions in both languages
        with st.expander("💡 Example Questions / ตัวอย่างคำถาม", expanded=False):
            suggestions = self.chatbot.get_suggested_questions(dashboard_context)
            
            # English questions
            st.markdown("**English:**")
            cols_en = st.columns(2)
            for i, question in enumerate(suggestions['en'][:4]):
                with cols_en[i % 2]:
                    if st.button(question, key=f"suggest_en_{i}", use_container_width=True):
                        st.session_state.suggested_q = question
                        st.rerun()
            
            # Thai questions
            st.markdown("**ภาษาไทย:**")
            cols_th = st.columns(2)
            for i, question in enumerate(suggestions['th'][:4]):
                with cols_th[i % 2]:
                    if st.button(question, key=f"suggest_th_{i}", use_container_width=True):
                        st.session_state.suggested_q = question
                        st.rerun()
        
        # Chat history display
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                
                # Show metadata for assistant messages
                if msg["role"] == "assistant":
                    meta_parts = []
                    if "cost" in msg and msg["cost"] > 0:
                        meta_parts.append(f"💵 ${msg['cost']:.6f}")
                    if "language" in msg:
                        lang_label = "🇹🇭 Thai" if msg["language"] == "th" else "🇬🇧 English"
                        meta_parts.append(lang_label)
                    
                    if meta_parts:
                        st.caption(" | ".join(meta_parts))
        
        # Chat input
        user_input = st.session_state.pop("suggested_q", None) or st.chat_input(
            "Ask anything... / ถามอะไรก็ได้..."
        )
        
        # Process message
        if user_input:
            # Display user message
            with st.chat_message("user"):
                st.write(user_input)
            
            # Add to history
            st.session_state.chat_history.append({
                "role": "user",
                "content": user_input
            })
            
            # Get response
            with st.chat_message("assistant"):
                with st.spinner("🤔 Thinking... / กำลังคิด..."):
                    result = self.chatbot.chat(
                        user_input,
                        [{"role": msg["role"], "content": msg["content"]} 
                         for msg in st.session_state.chat_history[:-1]],
                        dashboard_context,
                        force_language=st.session_state.preferred_language
                    )
                
                st.write(result["response"])
                
                # Show metadata
                meta_parts = []
                cost = result.get("cost", 0)
                if cost > 0:
                    meta_parts.append(f"💵 ${cost:.6f}")
                
                lang = result.get("language", "en")
                lang_label = "🇹🇭 Thai" if lang == "th" else "🇬🇧 English"
                meta_parts.append(lang_label)
                
                if meta_parts:
                    st.caption(" | ".join(meta_parts))
            
            # Add to history
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": result["response"],
                "cost": cost,
                "model": result.get("model"),
                "language": lang
            })
            
            # Update metrics
            st.session_state.message_count += 1
            st.session_state.total_cost += cost
            
            st.rerun()
        
        # Footer actions
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col2:
            if st.button("📊 Usage Stats / สถิติการใช้งาน"):
                st.info(f"""
                **Session Statistics / สถิติการใช้งาน:**
                - Messages / ข้อความ: {st.session_state.message_count}
                - Total Cost / ค่าใช้จ่ายรวม: ${st.session_state.total_cost:.4f}
                - Avg per msg / เฉลี่ยต่อข้อความ: ${st.session_state.total_cost / max(st.session_state.message_count, 1):.5f}
                """)
        
        with col3:
            if st.button("🗑️ Clear Chat / ล้างแชท"):
                st.session_state.chat_history = []
                st.session_state.total_cost = 0.0
                st.session_state.message_count = 0
                st.rerun()


# Convenience function for app.py
def create_bilingual_chat(dashboard_data: Dict, model_tier: str = "recommended") -> None:
    """
    Create bilingual chat interface with dashboard context.
    
    Args:
        dashboard_data: Dashboard data for context
        model_tier: Model quality tier
    """
    import pandas as pd
    
    # Extract context
    wells_df = dashboard_data.get("wells_df", pd.DataFrame())
    context = {
        "wells_summary": {
            "count": len(wells_df) if not wells_df.empty else 0,
            "success_rate": wells_df["survived"].mean() if not wells_df.empty else 0,
            "avg_depth": wells_df["depth_m"].mean() if not wells_df.empty else 0,
        }
    }
    
    # Initialize and render
    chatbot = BilingualChatbot(model_tier=model_tier)
    interface = BilingualChatInterface(chatbot)
    interface.render(context)


# Export
__all__ = [
    "BilingualChatbot",
    "BilingualChatInterface",
    "create_bilingual_chat"
]