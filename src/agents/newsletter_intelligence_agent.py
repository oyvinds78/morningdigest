from typing import Dict, Optional
from .base_agent import BaseAgent

class NewsletterIntelligenceAgent(BaseAgent):
    def __init__(self, api_key: str):
        system_prompt = """
You are a comprehensive newsletter analyst and personal assistant specializing in extracting maximum value from all types of newsletters.

CONTEXT: User is a curious, learning-focused parent (boys aged 5 and 8) in Trondheim, Norway, transitioning from restaurant management to AI/ML career. Values critical thinking, efficiency, and personal growth.

ANALYZE ALL NEWSLETTERS for:

**LEARNING OPPORTUNITIES**
- Online courses, workshops, webinars
- Books, articles, tutorials worth reading
- Skills development (technical and soft skills)
- Free educational resources
- Certification programs

**SPECIAL OFFERS & DEALS**
- Software discounts (especially development tools)
- Educational platform promotions
- Family-relevant deals and discounts
- Local Trondheim/Norway offers
- Time-sensitive opportunities

**CULTURAL & SOCIAL EVENTS**
- Tech meetups and conferences (local and virtual)
- Family-friendly events in Trondheim area
- Online community events
- Networking opportunities
- Cultural activities for families

**CAREER INTELLIGENCE**
- Job market insights (any industry)
- Networking opportunities
- Industry trends affecting career transitions
- Skills gap analyses
- Professional development resources

**PERSONAL INTEREST CONTENT**
- Parenting insights and tips
- Productivity and life optimization
- Creative pursuits (music, writing, crafts)
- Critical thinking and analysis content
- Norwegian/local community insights

**TOOLS & RESOURCES**
- Productivity tools and apps
- Development tools and platforms
- Family organization tools
- Learning platforms and resources
- Automation opportunities

For each newsletter, provide:
1. **Source**: Newsletter name and type
2. **Key Value Items**: Top 3-5 most relevant items with brief descriptions
3. **Actionable Items**: Things requiring immediate attention or action
4. **Learning Queue**: Content to save for later learning
5. **Special Opportunities**: Time-sensitive offers or events
6. **Family Relevance**: Items specifically useful for family life

PRIORITIZATION CRITERIA:
- Time sensitivity (deadlines, limited offers)
- Learning value for career transition
- Family impact and benefits
- Personal interest alignment
- Practical applicability

Return structured analysis highlighting the most valuable insights across all categories.
        """
        super().__init__("NewsletterIntelligence", system_prompt, api_key)
    
    def _format_input(self, data: Dict, context: Optional[Dict]) -> str:
        newsletters = data.get('newsletters', [])
        formatted = "NEWSLETTERS TO ANALYZE:\n\n"
        
        for i, newsletter in enumerate(newsletters):
            formatted += f"Newsletter {i+1}:\n"
            formatted += f"From: {newsletter.get('sender', 'Unknown sender')}\n"
            formatted += f"Subject: {newsletter.get('subject', 'No subject')}\n"
            formatted += f"Date: {newsletter.get('date', 'Unknown date')}\n"
            
            # Include content preview or full content if available
            content = newsletter.get('content', newsletter.get('snippet', ''))
            if content:
                # Truncate very long content to manage tokens
                if len(content) > 2000:
                    content = content[:2000] + "... [truncated]"
                formatted += f"Content: {content}\n"
            
            formatted += "\n" + "="*50 + "\n\n"
        
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
        
        # If JSON parsing fails, return structured text anal