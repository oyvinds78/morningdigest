from datetime import datetime
from typing import Dict, List, Any, Optional
import textwrap

class TextFormatter:
    def __init__(self, width: int = 80):
        self.width = width
        self.wrapper = textwrap.TextWrapper(width=width, initial_indent='  ', subsequent_indent='  ')
    
    def format(self, digest_data: Dict[str, Any]) -> str:
        """Format method alias for consistency"""
        return self.format_digest(digest_data)
    
    def format_digest(self, digest_data: Dict[str, Any]) -> str:
        """Format the complete morning digest as plain text"""
        
        # Extract data
        final_digest = digest_data.get('digest', {})
        agent_results = digest_data.get('agent_results', {})
        timestamp = digest_data.get('timestamp', datetime.now().isoformat())
        
        # Build text sections
        sections = []
        
        # Header
        sections.append(self._format_header())
        
        # Priority Today
        if self._has_priority_content(agent_results):
            sections.append(self._format_priority_section(agent_results))
        
        # Calendar
        if 'calendar_intelligence' in agent_results:
            sections.append(self._format_calendar_section(agent_results['calendar_intelligence']))
        
        # News
        if 'norwegian_news' in agent_results:
            sections.append(self._format_news_section(agent_results['norwegian_news']))
        
        # Tech Intelligence
        if 'tech_intelligence' in agent_results:
            sections.append(self._format_tech_section(agent_results['tech_intelligence']))
        
        # Newsletter Insights
        if 'newsletter_intelligence' in agent_results:
            sections.append(self._format_newsletter_section(agent_results['newsletter_intelligence']))
        
        # Weather
        if 'weather' in agent_results:
            sections.append(self._format_weather_section(agent_results['weather']))
        
        # Footer
        sections.append(self._format_footer(timestamp))
        
        return '\n\n'.join(sections)
    
    def _format_header(self) -> str:
        """Format the header"""
        date_str = datetime.now().strftime("%A, %d. %B %Y")
        
        header = "=" * self.width + "\n"
        header += "DIN MORGENOPPDATERING".center(self.width) + "\n"
        header += date_str.center(self.width) + "\n"
        header += "=" * self.width
        
        return header
    
    def _has_priority_content(self, agent_results: Dict) -> bool:
        """Check if there's priority content"""
        priority_indicators = [
            'calendar_intelligence',
            'norwegian_news', 
            'tech_intelligence'
        ]
        return any(key in agent_results for key in priority_indicators)
    
    def _format_priority_section(self, agent_results: Dict) -> str:
        """Format priority section"""
        content = "🔥 PRIORITET I DAG\n"
        content += "-" * 20 + "\n"
        
        priority_items = []
        
        # Extract priority calendar events
        calendar_data = agent_results.get('calendar_intelligence', {})
        if isinstance(calendar_data, dict):
            today_events = calendar_data.get('today_events', [])
            priority_events = [e for e in today_events if e.get('priority') == 'high']
            
            for event in priority_events[:3]:
                time_str = event.get('start_datetime', '').strftime('%H:%M') if event.get('start_datetime') else 'Tid ikke satt'
                priority_items.append(f"📅 {time_str} - {event.get('title', 'Uten tittel')}")
                if event.get('location'):
                    priority_items.append(f"   📍 {event['location']}")
        
        if not priority_items:
            content += "Ingen høyprioritetssaker for i dag 🎉\n"
        else:
            content += '\n'.join(priority_items) + "\n"
        
        return content
    
    def _format_calendar_section(self, calendar_data: Dict) -> str:
        """Format calendar section"""
        content = "📅 KALENDER\n"
        content += "-" * 15 + "\n"
        
        if isinstance(calendar_data, dict) and 'summary' in calendar_data:
            summary = calendar_data['summary']
            
            # Stats
            content += f"I dag: {summary.get('today_count', 0)} avtaler\n"
            content += f"Denne uken: {summary.get('week_count', 0)} avtaler\n"
            content += f"Prioritet: {summary.get('priority_count', 0)} avtaler\n\n"
            
            # Today's overview
            if summary.get('today_overview'):
                content += f"Oversikt: {summary['today_overview']}\n\n"
            
            # Next important event
            next_important = summary.get('next_important')
            if next_important:
                content += "⭐ NESTE VIKTIGE AVTALE:\n"
                content += f"   {next_important['title']}\n"
                content += f"   {next_important['date']} kl. {next_important['start_time']}\n\n"
            
            # Recommendations
            recommendations = calendar_data.get('recommendations', [])
            if recommendations:
                content += "💡 ANBEFALINGER:\n"
                for rec in recommendations[:3]:
                    wrapped = self.wrapper.fill(f"• {rec}")
                    content += wrapped + "\n"
        
        else:
            content += "Kunne ikke hente kalenderdata\n"
        
        return content
    
    def _format_news_section(self, news_data: Dict) -> str:
        """Format news section"""
        content = "📰 NYHETER\n"
        content += "-" * 12 + "\n"
        
        if isinstance(news_data, dict) and 'analysis' in news_data:
            analysis = news_data['analysis']
            
            if isinstance(analysis, str):
                # Wrap long text
                paragraphs = analysis.split('\n\n')
                for paragraph in paragraphs[:5]:
                    if paragraph.strip():
                        wrapped = textwrap.fill(paragraph.strip(), width=self.width)
                        content += wrapped + "\n\n"
            
            elif isinstance(analysis, dict):
                if 'articles' in analysis:
                    for i, article in enumerate(analysis['articles'][:5], 1):
                        content += f"{i}. {article.get('title', 'Uten tittel')}\n"
                        if article.get('summary'):
                            wrapped = textwrap.fill(article['summary'], width=self.width-3, initial_indent='   ')
                            content += wrapped + "\n"
                        content += f"   Kilde: {article.get('source', 'Ukjent')}\n\n"
        
        else:
            content += "Ingen nyhetsanalyse tilgjengelig\n"
        
        return content
    
    def _format_tech_section(self, tech_data: Dict) -> str:
        """Format tech section"""
        content = "💻 TECH & KARRIERE\n"
        content += "-" * 20 + "\n"
        
        if isinstance(tech_data, dict) and 'analysis' in tech_data:
            analysis = tech_data['analysis']
            
            if isinstance(analysis, str):
                paragraphs = analysis.split('\n\n')
                for paragraph in paragraphs[:4]:
                    if paragraph.strip():
                        wrapped = textwrap.fill(paragraph.strip(), width=self.width)
                        content += wrapped + "\n\n"
            
            elif isinstance(analysis, dict):
                if 'insights' in analysis:
                    for i, insight in enumerate(analysis['insights'][:3], 1):
                        content += f"{i}. {insight.get('title', 'Tech Insight')}\n"
                        if insight.get('summary'):
                            wrapped = textwrap.fill(insight['summary'], width=self.width-3, initial_indent='   ')
                            content += wrapped + "\n"
                        if insight.get('relevance'):
                            content += f"   Relevans: {insight['relevance']}\n"
                        content += "\n"
        
        else:
            content += "Ingen tech-analyse tilgjengelig\n"
        
        return content
    
    def _format_newsletter_section(self, newsletter_data: Dict) -> str:
        """Format newsletter section"""
        content = "📧 NEWSLETTER-HØYDEPUNKTER\n"
        content += "-" * 30 + "\n"
        
        if isinstance(newsletter_data, dict):
            # Show categories
            categories = newsletter_data.get('categories', {})
            if categories:
                content += "Kategorier:\n"
                for category, count in list(categories.items())[:5]:
                    if count > 0:
                        clean_category = category.replace('_', ' ').title()
                        content += f"  • {clean_category}: {count}\n"
                content += "\n"
            
            # Show analysis
            if 'analysis' in newsletter_data:
                analysis = newsletter_data['analysis']
                
                if isinstance(analysis, str):
                    paragraphs = analysis.split('\n\n')
                    for paragraph in paragraphs[:4]:
                        if paragraph.strip():
                            wrapped = textwrap.fill(paragraph.strip(), width=self.width)
                            content += wrapped + "\n\n"
        
        else:
            content += "Ingen newsletter-analyse tilgjengelig\n"
        
        return content
    
    def _format_weather_section(self, weather_data: Dict) -> str:
        """Format weather section"""
        content = "🌤️ VÆRET I TRONDHEIM\n"
        content += "-" * 22 + "\n"
        
        if isinstance(weather_data, dict):
            current = weather_data.get('current', {})
            today_forecast = weather_data.get('today_forecast', {})
            
            if current:
                content += f"Nå: {current.get('temperature', 'N/A')}°C - {current.get('description', 'Ingen beskrivelse')}\n"
                content += f"Føles som: {current.get('feels_like', 'N/A')}°C\n"
                content += f"Vind: {current.get('wind_speed', 'N/A')} m/s\n"
                content += f"Luftfuktighet: {current.get('humidity', 'N/A')}%\n"
                
                if current.get('clothing_advice'):
                    content += f"\nKlesråd: {current['clothing_advice']}\n"
                
                content += "\n"
            
            # Today's summary
            if today_forecast and 'summary' in today_forecast:
                content += f"I dag: {today_forecast['summary']}\n"
        
        else:
            content += "Værdata ikke tilgjengelig\n"
        
        return content
    
    def _format_footer(self, timestamp: str) -> str:
        """Format footer"""
        footer = "-" * self.width + "\n"
        footer += "Generert av din personlige AI-assistent".center(self.width) + "\n"
        
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            time_str = dt.strftime("%H:%M")
            footer += f"Sendt {time_str}".center(self.width)
        except:
            footer += "Automatisk generert".center(self.width)
        
        return footer

# Example usage
def main():
    formatter = TextFormatter(width=80)
    
    # Example digest data
    sample_data = {
        'digest': {'analysis': 'This is the main digest'},
        'agent_results': {
            'calendar_intelligence': {
                'summary': {
                    'today_count': 3,
                    'week_count': 12,
                    'priority_count': 2,
                    'today_overview': '3 møter i dag: 2 jobbmøter, 1 familieaktivitet'
                },
                'recommendations': [
                    "Busy day ahead - consider preparing lunch and snacks",
                    "Early meeting today - prepare everything the night before"
                ]
            },
            'weather': {
                'current': {
                    'temperature': 8,
                    'description': 'Delvis skyet',
                    'feels_like': 6,
                    'wind_speed': 3.2,
                    'humidity': 75,
                    'clothing_advice': 'Mellomtykk jakke eller genser'
                },
                'today_forecast': {
                    'summary': 'Temperatur: 5°C til 10°C, liten sjanse for regn (15%)'
                }
            }
        },
        'timestamp': datetime.now().isoformat()
    }
    
    text_output = formatter.format_digest(sample_data)
    
    # Save to file for testing
    with open('test_digest.txt', 'w', encoding='utf-8') as f:
        f.write(text_output)
    
    print("Text digest saved to test_digest.txt")
    print("\nPreview:")
    print(text_output[:500] + "...")

if __name__ == "__main__":
    main()
