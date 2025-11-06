import json
import asyncio
from anthropic import Anthropic
from typing import Dict, Any, Optional

class BaseAgent:
    def __init__(self, name: str, system_prompt: str, api_key: str):
        self.name = name
        self.system_prompt = system_prompt
        self.client = Anthropic(api_key=api_key)
        
    async def process(self, data: Dict[str, Any], context: Optional[Dict] = None) -> Dict[str, Any]:
        """Process data and return structured results"""
        try:
            response = await self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                system=self.system_prompt,
                messages=[{
                    "role": "user", 
                    "content": self._format_input(data, context)
                }]
            )
            return self._parse_response(response.content[0].text)
        except Exception as e:
            return {"error": f"{self.name} failed: {str(e)}", "data": data}
    
    def _format_input(self, data: Dict, context: Optional[Dict]) -> str:
        """Override in subclasses for agent-specific formatting"""
        return json.dumps(data, indent=2)
    
    def _parse_response(self, response: str) -> Dict:
        """Override in subclasses for structured output parsing"""
        return {"analysis": response}