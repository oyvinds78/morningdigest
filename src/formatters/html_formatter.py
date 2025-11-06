from datetime import datetime
from typing import Dict, List, Any, Optional
import json

class HTMLFormatter:
    def __init__(self, template_path: str = "config/email_template.html"):
        self.template_path = template_path
        self.base_template = self._get_base_template()
    
    def format_digest(self, digest_data: Dict[str, Any]) -> str:
        """Format the complete morning digest as HTML"""
        
        # Extract data from digest
        final_digest = digest_data.get('digest', {})
        agent_results = digest_data.get('agent_results', {})
        timestamp = digest_data.get('timestamp', datetime.now().isoformat())
        
        # Build HTML sections
        html_content = self._build_html_digest(final_digest, agent_results, timestamp)
        
        return self.base_template.format(
            title="Din morgenoppdatering",
            date=datetime.now().strftime("%A, %d. %B %Y"),
            content=html_content
        )
    
    def _get_base_template(self) -> str:
        """Get the base HTML email template"""
        try:
            with open(self.template_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return self._get_default_template()
    
    def _get_default_template(self) -> str:
        """Default HTML email template"""
        return """
<!DOCTYPE html>
<html lang="no">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background: white;
            border-radius: 10px;
            padding: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            border-bottom: 2px solid #e0e0e0;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .header h1 {{
            color: #2c3e50;
            margin: 0;
            font-size: 28px;
        }}
        .header .date {{
            color: #7f8c8d;
            font-size: 16px;
            margin-top: 5px;
        }}
        .section {{
            margin-bottom: 30px;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #3498db;
            background-color: #f8f9fa;
        }}
        .section h2 {{
            color: #2c3e50;
            margin-top: 0;
            margin-bottom: 15px;
            font-size: 20px;
        }}
        .priority {{
            border-left-color: #e74c3c;
        }}
        .news {{
            border-left-color: #3498db;
        }}
        .tech {{
            border-left-color: #9b59b6;
        }}
        .calendar {{
            border-left-color: #f39c12;
        }}
        .learning {{
            border-left-color: #27ae60;
        }}
        .weather {{
            border-left-color: #16a085;
        }}
        .item {{
            margin-bottom: 15px;
            padding: 15px;
            background: white;
            border-radius: 5px;
            border: 1px solid #e0e0e0;
        }}
        .item h3 {{
            margin: 0 0 8px 0;
            color: #2c3e50;
            font-size: 16px;
        }}
        .item p {{
            margin: 5px 0;
            color: #555;
        }}
        .source {{
            color: #7f8c8d;
            font-size: 12px;
            font-style: italic;
        }}
        .time {{
            color: #e74c3c;
            font-weight: bold;
        }}
        .tag {{
            display: inline-block;
            background: #ecf0f1;
            color: #2c3e50;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 11px;
            margin: 2px;
        }}
        .weather-summary {{
            text-align: center;
            font-size: 18px;
            color: #2c3e50;
            margin-bottom: 15px;
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e0e0e0;
            color: #7f8c8d;
            font-size: 12px;
        }}
        a {{
            color: #3498db;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 10px;
            margin-bottom: 20px;
        }}
        .stat {{
            text-align: center;
            padding: 10px;
            background: white;
            border-radius: 5px;
            border: 1px solid #e0e0e0;
        }}
        .stat-number {{
            font-size: 24px;
            font-weight: bold;
            color: #3498db;
        }}
        .stat-label {{
            font-size: 12px;
            color: #7f8c8d;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{title}</h1>
            <div class="date">{date}</div>
        </div>
        {content}
        <div class="footer">
            Generert av din personlige AI-assistent<br>
            <small>📧 Sendt {date}</small>
        </div>
    </div>
</body>
</html>
        """
    
    def _build_html_digest(self, final_digest: Dict, agent_results: Dict, timestamp: str) -> str:
        """Build the main HTML content"""
        sections = []
        
        # Priority Today section
        if self._has_priority_content(agent_results):
            sections.append(self._format_priority_section(agent_results))
        
        # Calendar section
        if 'calendar_intelligence' in agent_results:
            sections.append(self._format_calendar_section(agent_results['calendar_intelligence']))
        
        # News section
        if 'norwegian_news' in agent_results:
            sections.append(self._format_news_section(agent_results['norwegian_news']))
        
        # Tech Intelligence section
        if 'tech_intelligence' in agent_results:
            sections.append(self._format_tech_section(agent_results['tech_intelligence']))
        
        # Newsletter Insights section
        if 'newsletter_intelligence' in agent_results:
            sections.append(self._format_newsletter_section(agent_results['newsletter_intelligence']))
        
        # Weather section (should be last)
        if 'weather' in agent_results:
            sections.append(self._format_weather_section(agent_results['weather']))
        
        return '\n'.join(sections)
    
    def _has_priority_content(self, agent_results: Dict) -> bool:
        """Check if there's any priority content to display"""
        priority_indicators = [
            'calendar_intelligence',
            'norwegian_news', 
            'tech_intelligence'
        ]
        return any(key in agent_results for key in priority_indicators)
    
    def _format_priority_section(self, agent_results: Dict) -> str:
        """Format the priority items section"""
        content = '<div class="section priority">\n'
        content += '<h2>🔥 Prioritet i dag</h2>\n'
        
        priority_items = []
        
        # Extract high-priority calendar events
        calendar_data = agent_results.get('calendar_intelligence', {})
        if isinstance(calendar_data, dict):
            today_events = calendar_data.get('today_events', [])
            priority_events = [e for e in today_events if e.get('priority') == 'high']
            
            for event in priority_events[:3]:  # Top 3 priority events
                priority_items.append(f"""
                <div class="item">
                    <h3>📅 {event.get('title', 'Uten tittel')}</h3>
                    <p class="time">{event.get('start_datetime', '').strftime('%H:%M') if event.get('start_datetime') else 'Tid ikke satt'}</p>
                    {f'<p>{event.get("location", "")}</p>' if event.get('location') else ''}
                </div>
                """)
        
        # Add high-relevance news
        news_data = agent_results.get('norwegian_news', {})
        if isinstance(news_data, dict) and 'analysis' in news_data:
            # Try to extract high-priority news items from analysis
            priority_items.append(f"""
            <div class="item">
                <h3>📰 Viktige nyheter</h3>
                <p>Sjekk nyhetsseksjonen for dagens viktigste saker</p>
            </div>
            """)
        
        if not priority_items:
            content += '<p>Ingen høyprioritetssaker funnet for i dag 🎉</p>'
        else:
            content += '\n'.join(priority_items)
        
        content += '</div>\n'
        return content
    
    def _format_calendar_section(self, calendar_data: Dict) -> str:
        """Format calendar section"""
        content = '<div class="section calendar">\n'
        content += '<h2>📅 Kalender</h2>\n'
        
        if isinstance(calendar_data, dict) and 'summary' in calendar_data:
            summary = calendar_data['summary']
            
            # Stats
            content += '<div class="stats">\n'
            content += f"""
            <div class="stat">
                <div class="stat-number">{summary.get('today_count', 0)}</div>
                <div class="stat-label">I dag</div>
            </div>
            <div class="stat">
                <div class="stat-number">{summary.get('week_count', 0)}</div>
                <div class="stat-label">Denne uken</div>
            </div>
            <div class="stat">
                <div class="stat-number">{summary.get('priority_count', 0)}</div>
                <div class="stat-label">Prioritet</div>
            </div>
            """
            content += '</div>\n'
            
            # Today's overview
            if summary.get('today_overview'):
                content += f'<p><strong>I dag:</strong> {summary["today_overview"]}</p>\n'
            
            # Next important event
            next_important = summary.get('next_important')
            if next_important:
                content += f"""
                <div class="item">
                    <h3>⭐ Neste viktige avtale</h3>
                    <p><strong>{next_important['title']}</strong></p>
                    <p class="time">{next_important['date']} kl. {next_important['start_time']}</p>
                </div>
                """
            
            # Recommendations
            recommendations = calendar_data.get('recommendations', [])
            if recommendations:
                content += '<h3>💡 Anbefalinger</h3>\n'
                for rec in recommendations[:3]:
                    content += f'<p>• {rec}</p>\n'
        
        else:
            content += '<p>Kunne ikke hente kalenderdata</p>\n'
        
        content += '</div>\n'
        return content
    
    def _format_news_section(self, news_data: Dict) -> str:
        """Format news section"""
        content = '<div class="section news">\n'
        content += '<h2>📰 Nyheter</h2>\n'
        
        if isinstance(news_data, dict) and 'analysis' in news_data:
            # Try to parse structured news analysis
            analysis = news_data['analysis']
            
            if isinstance(analysis, str):
                # If it's a text analysis, format it nicely
                paragraphs = analysis.split('\n\n')
                for paragraph in paragraphs[:5]:  # Limit to first 5 paragraphs
                    if paragraph.strip():
                        content += f'<p>{paragraph.strip()}</p>\n'
            
            elif isinstance(analysis, dict):
                # If it's structured data, format accordingly
                if 'articles' in analysis:
                    for article in analysis['articles'][:5]:
                        content += f"""
                        <div class="item">
                            <h3>{article.get('title', 'Uten tittel')}</h3>
                            <p>{article.get('summary', 'Ingen sammendrag')}</p>
                            <div class="source">{article.get('source', 'Ukjent kilde')}</div>
                        </div>
                        """
        
        else:
            content += '<p>Ingen nyhetsanalyse tilgjengelig</p>\n'
        
        content += '</div>\n'
        return content
    
    def _format_tech_section(self, tech_data: Dict) -> str:
        """Format tech intelligence section"""
        content = '<div class="section tech">\n'
        content += '<h2>💻 Tech & Karriere</h2>\n'
        
        if isinstance(tech_data, dict) and 'analysis' in tech_data:
            analysis = tech_data['analysis']
            
            if isinstance(analysis, str):
                # Format text analysis
                paragraphs = analysis.split('\n\n')
                for paragraph in paragraphs[:4]:
                    if paragraph.strip():
                        content += f'<p>{paragraph.strip()}</p>\n'
            
            elif isinstance(analysis, dict):
                # Format structured tech analysis
                if 'insights' in analysis:
                    for insight in analysis['insights'][:3]:
                        content += f"""
                        <div class="item">
                            <h3>{insight.get('title', 'Tech Insight')}</h3>
                            <p>{insight.get('summary', '')}</p>
                            {f'<div class="source">Relevans: {insight.get("relevance", "")}</div>' if insight.get('relevance') else ''}
                        </div>
                        """
        
        else:
            content += '<p>Ingen tech-analyse tilgjengelig</p>\n'
        
        content += '</div>\n'
        return content
    
    def _format_newsletter_section(self, newsletter_data: Dict) -> str:
        """Format newsletter insights section"""
        content = '<div class="section learning">\n'
        content += '<h2>📧 Newsletter-høydepunkter</h2>\n'
        
        if isinstance(newsletter_data, dict):
            # Show categories if available
            categories = newsletter_data.get('categories', {})
            if categories:
                content += '<div class="stats">\n'
                for category, count in list(categories.items())[:4]:
                    if count > 0:
                        content += f"""
                        <div class="stat">
                            <div class="stat-number">{count}</div>
                            <div class="stat-label">{category.replace('_', ' ').title()}</div>
                        </div>
                        """
                content += '</div>\n'
            
            # Show analysis
            if 'analysis' in newsletter_data:
                analysis = newsletter_data['analysis']
                
                if isinstance(analysis, str):
                    paragraphs = analysis.split('\n\n')
                    for paragraph in paragraphs[:4]:
                        if paragraph.strip():
                            content += f'<p>{paragraph.strip()}</p>\n'
        
        else:
            content += '<p>Ingen newsletter-analyse tilgjengelig</p>\n'
        
        content += '</div>\n'
        return content
    
    def _format_weather_section(self, weather_data: Dict) -> str:
        """Format weather section"""
        content = '<div class="section weather">\n'
        content += '<h2>🌤️ Været i Trondheim</h2>\n'
        
        if isinstance(weather_data, dict):
            current = weather_data.get('current', {})
            today_forecast = weather_data.get('today_forecast', {})
            
            if current:
                content += f"""
                <div class="weather-summary">
                    {current.get('temperature', 'N/A')}°C - {current.get('description', 'Ingen beskrivelse')}
                </div>
                """
                
                content += f"""
                <div class="item">
                    <h3>Nå</h3>
                    <p><strong>Temperatur:</strong> {current.get('temperature', 'N/A')}°C (føles som {current.get('feels_like', 'N/A')}°C)</p>
                    <p><strong>Vind:</strong> {current.get('wind_speed', 'N/A')} m/s</p>
                    <p><strong>Luftfuktighet:</strong> {current.get('humidity', 'N/A')}%</p>
                    {f'<p><strong>Klesråd:</strong> {current.get("clothing_advice", "")}</p>' if current.get('clothing_advice') else ''}
                </div>
                """
            
            # Today's summary
            if today_forecast and 'summary' in today_forecast:
                content += f"""
                <div class="item">
                    <h3>I dag</h3>
                    <p>{today_forecast['summary']}</p>
                </div>
                """
        
        else:
            content += '<p>Værdata ikke tilgjengelig</p>\n'
        
        content += '</div>\n'
        return content

# Example usage
def main():
    formatter = HTMLFormatter()
    
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
                }
            }
        },
        'timestamp': datetime.now().isoformat()
    }
    
    html_output = formatter.format_digest(sample_data)
    
    # Save to file for testing
    with open('test_digest.html', 'w', encoding='utf-8') as f:
        f.write(html_output)
    
    print("HTML digest saved to test_digest.html")

if __name__ == "__main__":
    main()