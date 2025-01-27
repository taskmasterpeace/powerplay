from typing import List, Dict, Any
import os
from dotenv import load_dotenv
from langchain_community.chat_models import ChatOpenAI
from langchain.schema.messages import SystemMessage, HumanMessage

class LangChainService:
    """Handles real-time processing of text chunks using LangChain"""
    
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key not found in environment variables")
            
        self.llm = ChatOpenAI(
            temperature=0.7,
            openai_api_key=self.api_key
        )
        self.context_window = []
        self.max_context_chunks = 5
        
    def process_chunk(self, chunk: str, template: Dict[str, str]) -> str:
        """
        Process a chunk of text using LangChain
        
        Args:
            chunk: Text chunk to process
            template: Dictionary containing system and user prompts
            
        Returns:
            Processed response
        """
        # Add chunk to context window
        self.context_window.append(chunk)
        if len(self.context_window) > self.max_context_chunks:
            self.context_window.pop(0)
            
        # Create messages for the chat model
        messages = [
            SystemMessage(content=template["system"]),
            HumanMessage(content=f"{template['user']}\n\nContext (previous chunks):\n"
                                f"{' '.join(self.context_window[:-1])}\n\n"
                                f"Current chunk:\n{chunk}")
        ]
        
        # Get response from LLM
        response = self.llm(messages)
        return response.content
        
    def get_available_templates(self) -> List[Dict[str, str]]:
        """Get list of available templates"""
        return [
            {
                "name": "Meeting Summary",
                "system": "You are an AI assistant helping summarize meetings.",
                "user": "Provide a concise summary of the key points discussed:"
            },
            {
                "name": "Action Items",
                "system": "You are an AI assistant tracking action items.",
                "user": "List all action items and assignments mentioned:"
            },
            {
                "name": "Decision Tracking",
                "system": "You are an AI assistant tracking decisions.",
                "user": "List all decisions made during this discussion:"
            }
        ]
