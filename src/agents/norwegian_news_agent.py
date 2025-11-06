from typing import Dict, Optional
from .base_agent import BaseAgent

class NorwegianNewsAgent(BaseAgent):
    def __init__(self, api_key: str):
        system_prompt = """
You are a Norwegian news analyst with deep understanding of:
- Trondheim/Trøndelag local context
- Norwegian politics, culture and society
- Parenting and family policy
- Education system changes
- Environmental issues in Norway
- football in Norway (Eliteserien, Norwegian teams in Europe))
- Tech industry in Norway

TASK: Analyze Norwegian news articles and identify the most relevant items for:
- Parent of boys aged 5 and 8 in Trondheim
- Professional developer interested in AI/ML
- Someone interested in critical thinking and societal issues

For each relevant article, provide:
1. Relevance score (1-10)
2. Two-sentence summary
3. Why it matters to this person
4. Any actionable insights

Return as JSON with articles sorted by relevance.
Only include articles scoring 6+.
        """
        super().__init__("NorwegianNews", system_prompt, api_key)
    
    def _format_input(self, data: Dict, context: Optional[Dict]) -> str:
        articles = data.get('articles', [])
        formatted = "NORWEGIAN NEWS ARTICLES TO ANALYZE:\n\n"
        for i, article in enumerate(articles[:15]):  # Limit for token efficiency
            formatted += f"Article {i+1}:\n"
            formatted += f"Title: {article.get('title', 'No title')}\n"
            formatted += f"Source: {article.get('source', 'Unknown')}\n"
            formatted += f"Summary: {article.get('description', 'No description')}\n\n"
        return formatted
    
    def _parse_response(self, response: str) -> Dict:
        try:
            # Try to extract JSON from response
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end != -1:
                return json.loads(response[start:end])
        except:
            pass
        return {"analysis": response, "structured": False}