import json
from datetime import datetime
from typing import Dict, List, Any, Optional

class JSONFormatter:
    def __init__(self, indent: int = 2):
        self.indent = indent
    
    def format_digest(self, digest_data: Dict[str, Any]) -> str:
        """Format the complete morning digest as structured JSON"""
        
        # Create structured output
        structured_digest = {
            "metadata": self._create_metadata(digest_data),
            "summary": self._create_summary(digest_data),
            "sections": self._create_sections(digest_data),
            "raw_data": self._create_raw_data_summary(digest_data)
        }
        
        return json.dumps(structured_digest, indent=self.indent, ensure_ascii=False, default=str)
    
    def _create_metadata(self, digest_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create metadata section"""
        timestamp = digest_data.get('timestamp', datetime.now().isoformat())
        
        return {
            "generated_at": timestamp,
            "version": "1.0",
            "location": "Trondheim, Norway",
            "timezone": "Europe/Oslo",
            "language": "no",
            "agent_count": len(digest_data.get('agent_results', {})),
            "format": "morning_digest"
        }
    
    def _create_summary(self, digest_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create high-level summary"""
        agent_results = digest_data.get('agent_results', {})
        
        summary = {
            "total_items": 0,
            "priority_items": 0,
            "categories": {},
            "data_sources": list(agent_results.keys()),
            "status": "success" if agent_results else "partial"
        }
        
        # Count items from different sources
        if 'calendar_intelligence' in agent_results:
            cal_data = agent_results['calendar_intelligence']
            if isinstance(cal_data, dict) and 'summary' in cal_data:
                summary['total_items'] += cal_data['summary'].get('today_count', 0)
                summary['priority_items'] += cal_data['summary'].get('priority_count', 0)
                summary['categories']['calendar'] = cal_data['summary'].get('today_count', 0)
        
        if 'newsletter_intelligence' in agent_results:
            news_data = agent_results['newsletter_intelligence']
            if isinstance(news_data, dict) and 'categories' in news_data:
                newsletter_count = sum(news_data['categories'].values())
                summary['total_items'] += newsletter_count
                summary['categories']['newsletters'] = newsletter_count
        
        return summary
    
    def _create_sections(self, digest_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create structured sections"""
        agent_results = digest_data.get('agent_results', {})
        sections = {}
        
        # Priority section
        if self._has_priority_content(agent_results):
            sections['priority'] = self._format_priority_section_json(agent_results)
        
        # Calendar section
        if 'calendar_intelligence' in agent_results:
            sections['calendar'] = self._format_calendar_section_json(agent_results['calendar_intelligence'])
        
        # News section
        if 'norwegian_news' in agent_results:
            sections['news'] = self._format_news_section_json(agent_results['norwegian_news'])
        
        # Tech section
        if 'tech_intelligence' in agent_results:
            sections['tech'] = self._format_tech_section_json(agent_results['tech_intelligence'])
        
        # Newsletter section
        if 'newsletter_intelligence' in agent_results:
            sections['newsletters'] = self._format_newsletter_section_json(agent_results['newsletter_intelligence'])
        
        # Weather section
        if 'weather' in agent_results:
            sections['weather'] = self._format_weather_section_json(agent_results['weather'])
        
        return sections
    
    def _has_priority_content(self, agent_results: Dict) -> bool:
        """Check if there's priority content"""
        return any(key in agent_results for key in ['calendar_intelligence', 'norwegian_news', 'tech_intelligence'])
    
    def _format_priority_section_json(self, agent_results: Dict) -> Dict[str, Any]:
        """Format priority section as JSON"""
        priority_section = {
            "title": "Prioritet i dag",
            "items": [],
            "count": 0
        }
        
        # Extract priority calendar events
        calendar_data = agent_results.get('calendar_intelligence', {})
        if isinstance(calendar_data, dict):
            today_events = calendar_data.get('today_events', [])
            priority_events = [e for e in today_events if e.get('priority') == 'high']
            
            for event in priority_events[:5]:
                priority_item = {
                    "type": "calendar_event",
                    "title": event.get('title', 'Uten tittel'),
                    "time": event.get('start_datetime', '').strftime('%H:%M') if event.get('start_datetime') else None,
                    "location": event.get('location', ''),
                    "priority": event.get('priority', 'medium'),
                    "category": event.get('category', 'other')
                }
                priority_section['items'].append(priority_item)
        
        priority_section['count'] = len(priority_section['items'])
        return priority_section
    
    def _format_calendar_section_json(self, calendar_data: Dict) -> Dict[str, Any]:
        """Format calendar section as JSON"""
        calendar_section = {
            "title": "Kalender",
            "summary": {},
            "today_events": [],
            "recommendations": [],
            "next_important": None
        }
        
        if isinstance(calendar_data, dict):
            # Summary statistics
            if 'summary' in calendar_data:
                summary = calendar_data['summary']
                calendar_section['summary'] = {
                    "today_count": summary.get('today_count', 0),
                    "week_count": summary.get('week_count', 0),
                    "priority_count": summary.get('priority_count', 0),
                    "family_count": summary.get('family_count', 0),
                    "work_count": summary.get('work_count', 0),
                    "overview": summary.get('today_overview', ''),
                    "free_time": summary.get('free_time_today', {})
                }
                
                # Next important event
                next_important = summary.get('next_important')
                if next_important:
                    calendar_section['next_important'] = {
                        "title": next_important['title'],
                        "date": next_important['date'],
                        "time": next_important['start_time'],
                        "priority": next_important['priority']
                    }
            
            # Today's events
            today_events = calendar_data.get('today_events', [])
            for event in today_events:
                event_json = {
                    "title": event.get('title', ''),
                    "start_time": event.get('start_datetime', '').strftime('%H:%M') if event.get('start_datetime') else None,
                    "end_time": event.get('end_datetime', '').strftime('%H:%M') if event.get('end_datetime') else None,
                    "location": event.get('location', ''),
                    "priority": event.get('priority', 'low'),
                    "category": event.get('category', 'other'),
                    "duration_minutes": event.get('duration_minutes', 0),
                    "attendees": event.get('attendees', 0),
                    "preparation_needed": event.get('preparation_needed', {})
                }
                calendar_section['today_events'].append(event_json)
            
            # Recommendations
            calendar_section['recommendations'] = calendar_data.get('recommendations', [])
        
        return calendar_section
    
    def _format_news_section_json(self, news_data: Dict) -> Dict[str, Any]:
        """Format news section as JSON"""
        news_section = {
            "title": "Nyheter",
            "articles": [],
            "analysis": None,
            "sources": []
        }
        
        if isinstance(news_data, dict):
            if 'analysis' in news_data:
                news_section['analysis'] = news_data['analysis']
                
                # Try to extract articles if structured
                if isinstance(news_data['analysis'], dict) and 'articles' in news_data['analysis']:
                    for article in news_data['analysis']['articles']:
                        article_json = {
                            "title": article.get('title', ''),
                            "summary": article.get('summary', ''),
                            "source": article.get('source', ''),
                            "relevance_score": article.get('relevance_score', 0),
                            "category": article.get('category', 'general'),
                            "url": article.get('url', '')
                        }
                        news_section['articles'].append(article_json)
                        
                        # Track sources
                        source = article.get('source', '')
                        if source and source not in news_section['sources']:
                            news_section['sources'].append(source)
        
        return news_section
    
    def _format_tech_section_json(self, tech_data: Dict) -> Dict[str, Any]:
        """Format tech section as JSON"""
        tech_section = {
            "title": "Tech & Karriere",
            "insights": [],
            "analysis": None,
            "learning_opportunities": [],
            "career_relevant": []
        }
        
        if isinstance(tech_data, dict):
            if 'analysis' in tech_data:
                tech_section['analysis'] = tech_data['analysis']
                
                # Try to extract structured insights
                if isinstance(tech_data['analysis'], dict):
                    if 'insights' in tech_data['analysis']:
                        for insight in tech_data['analysis']['insights']:
                            insight_json = {
                                "title": insight.get('title', ''),
                                "summary": insight.get('summary', ''),
                                "relevance": insight.get('relevance', ''),
                                "category": insight.get('category', 'general'),
                                "actionable": insight.get('actionable', False)
                            }
                            tech_section['insights'].append(insight_json)
                    
                    if 'learning_opportunities' in tech_data['analysis']:
                        tech_section['learning_opportunities'] = tech_data['analysis']['learning_opportunities']
                    
                    if 'career_relevant' in tech_data['analysis']:
                        tech_section['career_relevant'] = tech_data['analysis']['career_relevant']
        
        return tech_section
    
    def _format_newsletter_section_json(self, newsletter_data: Dict) -> Dict[str, Any]:
        """Format newsletter section as JSON"""
        newsletter_section = {
            "title": "Newsletter-høydepunkter",
            "categories": {},
            "highlights": [],
            "learning_opportunities": [],
            "special_offers": [],
            "events": [],
            "analysis": None
        }
        
        if isinstance(newsletter_data, dict):
            # Categories count
            newsletter_section['categories'] = newsletter_data.get('categories', {})
            
            # Analysis
            if 'analysis' in newsletter_data:
                newsletter_section['analysis'] = newsletter_data['analysis']
                
                # Try to extract structured data from categories
                categories = newsletter_data.get('categories', {})
                
                if 'learning_opportunities' in categories:
                    newsletter_section['learning_opportunities'] = categories['learning_opportunities']
                
                if 'special_offers' in categories:
                    newsletter_section['special_offers'] = categories['special_offers']
                
                if 'cultural_events' in categories:
                    newsletter_section['events'] = categories['cultural_events']
        
        return newsletter_section
    
    def _format_weather_section_json(self, weather_data: Dict) -> Dict[str, Any]:
        """Format weather section as JSON"""
        weather_section = {
            "title": "Været i Trondheim",
            "current": {},
            "today_forecast": {},
            "clothing_advice": None,
            "location": "Trondheim, Norway"
        }
        
        if isinstance(weather_data, dict):
            # Current weather
            current = weather_data.get('current', {})
            if current:
                weather_section['current'] = {
                    "temperature": current.get('temperature'),
                    "feels_like": current.get('feels_like'),
                    "description": current.get('description'),
                    "humidity": current.get('humidity'),
                    "wind_speed": current.get('wind_speed'),
                    "wind_direction": current.get('wind_direction'),
                    "visibility": current.get('visibility')
                }
                weather_section['clothing_advice'] = current.get('clothing_advice')
            
            # Today's forecast
            today_forecast = weather_data.get('today_forecast', {})
            if today_forecast:
                weather_section['today_forecast'] = {
                    "summary": today_forecast.get('summary'),
                    "hourly": today_forecast.get('hourly', [])
                }
        
        return weather_section
    
    def _create_raw_data_summary(self, digest_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create summary of raw data availability"""
        agent_results = digest_data.get('agent_results', {})
        
        raw_summary = {
            "agents_executed": list(agent_results.keys()),
            "successful_agents": [],
            "failed_agents": [],
            "data_quality": {}
        }
        
        for agent_name, result in agent_results.items():
            if isinstance(result, dict) and 'error' not in result:
                raw_summary['successful_agents'].append(agent_name)
                
                # Assess data quality
                if 'analysis' in result:
                    raw_summary['data_quality'][agent_name] = "good"
                else:
                    raw_summary['data_quality'][agent_name] = "partial"
            else:
                raw_summary['failed_agents'].append(agent_name)
                raw_summary['data_quality'][agent_name] = "failed"
        
        return raw_summary

# Example usage
def main():
    formatter = JSONFormatter(indent=2)
    
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
                'today_events': [
                    {
                        'title': 'Standup meeting',
                        'start_datetime': datetime.now().replace(hour=9, minute=0),
                        'priority': 'high',
                        'category': 'work'
                    }
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
                }
            }
        },
        'timestamp': datetime.now().isoformat()
    }
    
    json_output = formatter.format_digest(sample_data)
    
    # Save to file for testing
    with open('test_digest.json', 'w', encoding='utf-8') as f:
        f.write(json_output)
    
    print("JSON digest saved to test_digest.json")
    print("\nPreview:")
    
    # Pretty print first few lines
    lines = json_output.split('\n')
    for line in lines[:20]:
        print(line)
    print("...")

if __name__ == "__main__":
    main()