# geodash/services/openrouter_chatbot.py
"""
OpenRouter-based chatbot service - Budget-friendly LLM integration.
Supports multiple models with unified API.
"""
import os
import requests
from typing import List, Dict, Optional
import streamlit as st


class OpenRouterChatbot:
    """
    Budget-friendly chatbot using OpenRouter API.
    Access to 100+ models including Claude, GPT-4, Llama, Gemini.
    """
    
    # Model recommendations by budget tier
    MODELS = {
        "premium": "anthropic/claude-3.5-sonnet",  # $3/$15 - Best quality
        "recommended": "anthropic/claude-3.5-haiku",  # $0.80/$4 - Best value
        "budget": "meta-llama/llama-3.1-70b-instruct",  # $0.35/$0.40 - Cheap
        "free": "google/gemini-flash-1.5",  # $0.075/$0.30 - Very cheap
    }
    
    def __init__(self, api_key: Optional[str] = None, model_tier: str = "recommended"):
        """
        Initialize OpenRouter chatbot.
        
        Args:
            api_key: OpenRouter API key (required - no fallback to env vars)
            model_tier: "premium", "recommended", "budget", or "free"
        """
        # SECURITY: Only accept explicitly passed API key, don't read from environment
        self.api_key = api_key
        self.model = self.MODELS.get(model_tier, self.MODELS["recommended"])
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        
        if not self.api_key:
            # Don't show warning here - let the calling code handle UI
            pass
        
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """Build geological domain system prompt."""
        return """You are an expert geological consultant specializing in groundwater 
management and well drilling in Thailand, particularly in Suphan Buri province.

Your expertise:
- Groundwater hydrology and aquifer systems in Thailand
- Well drilling success probability (optimal depth: 80-150m)
- Cost estimation (~1,200 THB/meter)
- Seasonal variations (Rainy: May-Oct, Dry: Nov-Apr)
- Regional geology of Dan Chang District

Study Area Context:
- Location: Dan Chang District (อำเภอด่านช้าง), Suphan Buri
- Coordinates: Lat 14.85-15.05°N, Lon 99.50-99.75°E
- Typical success rate: 70-85%
- Best drilling season: Early rainy season (May-June)

Provide concise, actionable advice in metric units. Mention cost estimates 
are approximate and recommend professional surveys."""
    
    def chat(
        self, 
        user_message: str, 
        conversation_history: List[Dict[str, str]],
        dashboard_context: Optional[Dict] = None,
        max_tokens: int = 1500
    ) -> Dict[str, any]:
        """
        Send message and get response via OpenRouter.
        
        Args:
            user_message: User's question
            conversation_history: Previous messages
            dashboard_context: Dashboard data for context
            max_tokens: Maximum response length
            
        Returns:
            Dict with 'response', 'model', 'cost' keys
        """
        if not self.api_key:
            return {
                "response": "❌ Please configure OPENROUTER_API_KEY",
                "model": None,
                "cost": 0
            }
        
        try:
            # Build messages
            messages = [{"role": "system", "content": self.system_prompt}]
            
            # Add dashboard context if available
            if dashboard_context:
                context_msg = self._format_context(dashboard_context)
                messages.append({"role": "system", "content": f"Current data: {context_msg}"})
            
            # Add conversation history
            messages.extend(conversation_history)
            messages.append({"role": "user", "content": user_message})
            
            # Make API request
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/yourusername/badan",  # Optional
                "X-Title": "Badan Groundwater Dashboard"  # Optional
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
            
            # Calculate approximate cost
            cost = self._calculate_cost(usage)
            
            return {
                "response": assistant_message,
                "model": self.model,
                "cost": cost,
                "usage": usage
            }
            
        except requests.exceptions.RequestException as e:
            return {
                "response": f"❌ API Error: {str(e)}",
                "model": self.model,
                "cost": 0
            }
        except Exception as e:
            return {
                "response": f"❌ Unexpected error: {str(e)}",
                "model": self.model,
                "cost": 0
            }
    
    def _format_context(self, context: Dict) -> str:
        """Format dashboard context for prompt."""
        parts = []
        
        if "wells_summary" in context:
            ws = context["wells_summary"]
            parts.append(f"{ws.get('count', 0)} wells analyzed")
            parts.append(f"Success rate: {ws.get('success_rate', 0):.1%}")
            parts.append(f"Avg depth: {ws.get('avg_depth', 0):.1f}m")
        
        if "selected_region" in context:
            parts.append(f"Region: {context['selected_region']}")
        
        return " | ".join(parts) if parts else "No data loaded"
    
    def _calculate_cost(self, usage: Dict) -> float:
        """
        Calculate approximate cost in USD.
        
        Args:
            usage: Usage dict with prompt_tokens and completion_tokens
            
        Returns:
            Estimated cost in USD
        """
        # Approximate costs per 1M tokens (may vary by model)
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
            st.success(f"✅ Switched to {model_tier} tier")
    
    @staticmethod
    def get_suggested_questions(context: Optional[Dict] = None) -> List[str]:
        """Get contextual suggested questions."""
        questions = [
            "What is the optimal drilling depth for this area?",
            "Estimate the cost for drilling a 120m well",
            "When is the best season for drilling?",
            "Why do some wells fail in this region?",
            "How can I improve well success rates?",
            "What geological factors affect groundwater here?",
            "Compare drilling costs at different depths",
        ]
        
        if context and context.get("selected_region"):
            region = context["selected_region"]
            questions.insert(0, f"What are the geological characteristics of {region}?")
        
        return questions


class OpenRouterChatInterface:
    """Streamlit chat interface for OpenRouter chatbot."""
    
    def __init__(self, chatbot: OpenRouterChatbot):
        self.chatbot = chatbot
        
        # Session state initialization
        if "or_chat_history" not in st.session_state:
            st.session_state.or_chat_history = []
        if "or_total_cost" not in st.session_state:
            st.session_state.or_total_cost = 0.0
        if "or_message_count" not in st.session_state:
            st.session_state.or_message_count = 0
    
    def render(self, dashboard_context: Optional[Dict] = None):
        """Render the chat interface with OpenRouter."""
        
        # Header with model info
        col_title, col_model = st.columns([3, 1])
        
        with col_title:
            st.markdown("### 🤖 AI Geological Assistant")
        
        with col_model:
            model_info = self.chatbot.get_model_info()
            st.caption(f"🔧 {model_info['name']}")
        
        # Configuration section
        if not self.chatbot.api_key:
            with st.expander("⚙️ Setup OpenRouter (Free)", expanded=True):
                st.markdown("""
                **Get Started in 30 seconds:**
                1. Visit [openrouter.ai/keys](https://openrouter.ai/keys)
                2. Sign up with Google/GitHub (free)
                3. Copy your API key
                4. Paste below
                
                💰 **You get $1 free credit** (~1000 messages with Haiku model)
                """)
                
                api_key = st.text_input(
                    "OpenRouter API Key", 
                    type="password",
                    placeholder="sk-or-v1-..."
                )
                
                if st.button("💾 Save & Connect"):
                    if api_key.startswith("sk-or-"):
                        os.environ["OPENROUTER_API_KEY"] = api_key
                        self.chatbot.api_key = api_key
                        st.success("✅ Connected! You can now chat.")
                        st.rerun()
                    else:
                        st.error("Invalid key format. Should start with 'sk-or-'")
                return
        
        # Model selector
        with st.expander("🎛️ Settings", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                model_tier = st.selectbox(
                    "Model Quality",
                    ["recommended", "premium", "budget", "free"],
                    index=0,
                    format_func=lambda x: {
                        "premium": "🌟 Premium - Claude Sonnet ($$$)",
                        "recommended": "⚡ Recommended - Claude Haiku ($$)",
                        "budget": "💰 Budget - Llama 70B ($)",
                        "free": "🆓 Free Tier - Gemini Flash"
                    }[x]
                )
                
                if st.button("Apply Model Change"):
                    self.chatbot.change_model(model_tier)
            
            with col2:
                st.metric("Messages Sent", st.session_state.or_message_count)
                st.metric("Total Cost", f"${st.session_state.or_total_cost:.4f}")
        
        # Suggested questions
        with st.expander("💡 Example Questions", expanded=False):
            suggestions = self.chatbot.get_suggested_questions(dashboard_context)
            cols = st.columns(2)
            
            for i, question in enumerate(suggestions):
                with cols[i % 2]:
                    if st.button(question, key=f"suggest_{i}", use_container_width=True):
                        st.session_state.suggested_q = question
                        st.rerun()
        
        # Chat history display
        for msg in st.session_state.or_chat_history:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                
                # Show cost for assistant messages
                if msg["role"] == "assistant" and "cost" in msg:
                    st.caption(f"💵 ${msg['cost']:.6f}")
        
        # Handle suggested question
        user_input = None
        if hasattr(st.session_state, "suggested_q"):
            user_input = st.session_state.suggested_q
            del st.session_state.suggested_q
        else:
            user_input = st.chat_input("Ask about geology, wells, costs, or best practices...")
        
        # Process message
        if user_input:
            # Display user message
            with st.chat_message("user"):
                st.write(user_input)
            
            # Add to history
            st.session_state.or_chat_history.append({
                "role": "user",
                "content": user_input
            })
            
            # Get response
            with st.chat_message("assistant"):
                with st.spinner("🤔 Thinking..."):
                    result = self.chatbot.chat(
                        user_input,
                        [{"role": msg["role"], "content": msg["content"]} 
                         for msg in st.session_state.or_chat_history[:-1]],
                        dashboard_context
                    )
                
                st.write(result["response"])
                
                # Show cost
                cost = result.get("cost", 0)
                if cost > 0:
                    st.caption(f"💵 ${cost:.6f} | Model: {result.get('model', 'N/A')}")
            
            # Add to history
            st.session_state.or_chat_history.append({
                "role": "assistant",
                "content": result["response"],
                "cost": cost,
                "model": result.get("model")
            })
            
            # Update metrics
            st.session_state.or_message_count += 1
            st.session_state.or_total_cost += cost
            
            st.rerun()
        
        # Footer actions
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col2:
            if st.button("📊 Usage Stats"):
                st.info(f"""
                **Session Statistics:**
                - Messages: {st.session_state.or_message_count}
                - Total Cost: ${st.session_state.or_total_cost:.4f}
                - Avg per msg: ${st.session_state.or_total_cost / max(st.session_state.or_message_count, 1):.5f}
                """)
        
        with col3:
            if st.button("🗑️ Clear Chat"):
                st.session_state.or_chat_history = []
                st.session_state.or_total_cost = 0.0
                st.session_state.or_message_count = 0
                st.rerun()


# Convenience function for app.py
def create_openrouter_chat(dashboard_data: Dict, model_tier: str = "recommended") -> None:
    """
    Create OpenRouter chat interface with dashboard context.
    
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
    chatbot = OpenRouterChatbot(model_tier=model_tier)
    interface = OpenRouterChatInterface(chatbot)
    interface.render(context)


# Example usage
if __name__ == "__main__":
    # Test the chatbot
    chatbot = OpenRouterChatbot(model_tier="recommended")
    result = chatbot.chat(
        "What's the optimal drilling depth?",
        [],
        {"wells_summary": {"count": 50, "success_rate": 0.75, "avg_depth": 120}}
    )
    print(f"Response: {result['response']}")
    print(f"Cost: ${result['cost']:.6f}")