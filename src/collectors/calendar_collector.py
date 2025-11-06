import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json
import logging

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import os

class CalendarCollector:
    def __init__(self, credentials_path: str, token_path: str = "calendar_token.json"):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None
        self.scopes = ['https://www.googleapis.com/auth/calendar.readonly']
    
    def authenticate(self):
        """Handle Google Calendar API authentication"""
        creds = None
        
        # Load existing token
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, self.scopes)
        
        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = Flow.from_client_secrets_file(self.credentials_path, self.scopes)
                flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
                
                auth_url, _ = flow.authorization_url(prompt='consent')
                print(f'Please visit this URL to authorize calendar access: {auth_url}')
                
                auth_code = input('Enter the authorization code: ')
                flow.fetch_token(code=auth_code)
                creds = flow.credentials
            
            # Save credentials
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())
        
        self.service = build('calendar', 'v3', credentials=creds)
    
    async def collect_calendar_data(self, days_ahead: int = 7) -> Dict[str, Any]:
        """Collect calendar events for today and the specified days ahead"""
        if not self.service:
            self.authenticate()
        
        try:
            # Time range: today through next week
            now = datetime.now()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = today_start + timedelta(days=days_ahead)
            
            # Get calendars
            calendar_list = self.service.calendarList().list().execute()
            calendars = calendar_list.get('items', [])
            
            all_events = []
            
            # Collect events from all calendars
            for calendar in calendars:
                if calendar.get('accessRole') in ['reader', 'writer', 'owner']:
                    calendar_events = await self._get_calendar_events(
                        calendar['id'], 
                        calendar.get('summary', 'Unknown Calendar'),
                        today_start, 
                        end_time
                    )
                    all_events.extend(calendar_events)
            
            # Sort events by start time
            all_events.sort(key=lambda x: x.get('start_datetime', datetime.min))
            
            # Categorize events
            categorized = self._categorize_events(all_events)
            
            return {
                'today_events': categorized['today'],
                'this_week_events': categorized['this_week'],
                'priority_events': categorized['priority'],
                'family_events': categorized['family'],
                'work_events': categorized['work'],
                'learning_events': categorized['learning'],
                'personal_events': categorized['personal'],
                'summary': self._create_summary(categorized),
                'recommendations': self._create_recommendations(categorized),
                'collection_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            logging.error(f"Calendar collection failed: {e}")
            return {'error': f'Calendar collection failed: {str(e)}'}
    
    async def _get_calendar_events(self, calendar_id: str, calendar_name: str, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Get events from a specific calendar"""
        try:
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=start_time.isoformat() + 'Z',
                timeMax=end_time.isoformat() + 'Z',
                singleEvents=True,
                orderBy='startTime',
                maxResults=100
            ).execute()
            
            events = events_result.get('items', [])
            formatted_events = []
            
            for event in events:
                formatted_event = self._format_event(event, calendar_id, calendar_name)
                if formatted_event:
                    formatted_events.append(formatted_event)
            
            return formatted_events
            
        except Exception as e:
            logging.error(f"Error fetching events from calendar {calendar_name}: {e}")
            return []
    
    def _format_event(self, event: Dict, calendar_id: str, calendar_name: str) -> Optional[Dict]:
        """Format a calendar event"""
        try:
            # Handle different event time formats
            start = event.get('start', {})
            end = event.get('end', {})
            
            if 'dateTime' in start:
                start_dt = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end['dateTime'].replace('Z', '+00:00'))
                all_day = False
            elif 'date' in start:
                start_dt = datetime.fromisoformat(start['date'])
                end_dt = datetime.fromisoformat(end['date'])
                all_day = True
            else:
                return None
            
            # Extract attendees information
            attendees = event.get('attendees', [])
            attendee_emails = [att.get('email', '') for att in attendees]
            attendee_count = len(attendees)
            
            return {
                'id': event.get('id', ''),
                'title': event.get('summary', 'No title'),
                'description': event.get('description', ''),
                'location': event.get('location', ''),
                'start_datetime': start_dt,
                'end_datetime': end_dt,
                'all_day': all_day,
                'calendar_id': calendar_id,
                'calendar_name': calendar_name,
                'duration_minutes': (end_dt - start_dt).total_seconds() / 60 if not all_day else 0,
                'attendees': attendee_count,
                'attendee_emails': attendee_emails,
                'status': event.get('status', 'confirmed'),
                'priority': self._calculate_priority(event, calendar_name),
                'category': self._categorize_single_event(event, calendar_name),
                'preparation_needed': self._assess_preparation_needed(event),
                'family_impact': self._assess_family_impact(event),
                'travel_time': self._estimate_travel_time(event.get('location', '')),
                'is_recurring': 'recurringEventId' in event,
                'created': event.get('created', ''),
                'html_link': event.get('htmlLink', '')
            }
            
        except Exception as e:
            logging.error(f"Error formatting event: {e}")
            return None
    
    def _calculate_priority(self, event: Dict, calendar_name: str) -> str:
        """Calculate event priority based on various factors"""
        title = event.get('summary', '').lower()
        description = event.get('description', '').lower()
        attendees = event.get('attendees', [])
        location = event.get('location', '').lower()
        
        # High priority indicators
        high_priority_keywords = [
            'urgent', 'important', 'deadline', 'interview', 'presentation', 
            'demo', 'client', 'boss', 'direktør', 'leder', 'meeting with',
            'hastesak', 'viktig', 'frist'
        ]
        
        # Family priority indicators (always high priority)
        family_keywords = [
            'familie', 'barn', 'skole', 'barnehage', 'kids', 'children',
            'parent', 'family', 'doctor', 'lege', 'tannlege', 'sykehus',
            'parent-teacher', 'foreldremøte', 'aktivitet'
        ]
        
        # Work priority indicators
        work_keywords = [
            'work', 'jobb', 'meeting', 'møte', 'conference', 'konferanse',
            'training', 'opplæring', 'course', 'kurs', 'workshop',
            'standup', 'planning', 'review', 'retrospective'
        ]
        
        # Learning/Career priority indicators
        learning_keywords = [
            'course', 'kurs', 'webinar', 'training', 'certification',
            'learning', 'workshop', 'seminar', 'conference', 'networking'
        ]
        
        content = f"{title} {description} {location}"
        
        # Calendar-based priority
        calendar_priority_boost = 0
        if 'work' in calendar_name.lower() or 'job' in calendar_name.lower():
            calendar_priority_boost = 0.5
        elif 'family' in calendar_name.lower() or 'personal' in calendar_name.lower():
            calendar_priority_boost = 0.3
        
        # Check for high priority
        if any(keyword in content for keyword in high_priority_keywords):
            return 'high'
        
        # Family always high priority
        if any(keyword in content for keyword in family_keywords):
            return 'high'
        
        # Check for work priority
        if any(keyword in content for keyword in work_keywords):
            priority_score = 1.0 + calendar_priority_boost
            return 'high' if priority_score > 1.3 else 'medium'
        
        # Learning/career events
        if any(keyword in content for keyword in learning_keywords):
            return 'medium'
        
        # Multiple attendees = higher priority
        if len(attendees) > 3:
            return 'medium'
        
        # External location = medium priority
        if location and location not in ['home', 'hjemme']:
            return 'medium'
        
        return 'low'
    
    def _categorize_single_event(self, event: Dict, calendar_name: str) -> str:
        """Categorize a single event"""
        title = event.get('summary', '').lower()
        description = event.get('description', '').lower()
        location = event.get('location', '').lower()
        content = f"{title} {description} {location}"
        
        # Family categories
        family_indicators = [
            'familie', 'barn', 'skole', 'barnehage', 'lege', 'tannlege',
            'family', 'kids', 'children', 'parent', 'doctor', 'dentist',
            'aktivitet', 'trening', 'sport', 'fotball', 'svømming'
        ]
        if any(word in content for word in family_indicators):
            return 'family'
        
        # Work categories
        work_indicators = [
            'møte', 'meeting', 'jobb', 'work', 'presentasjon', 'demo',
            'standup', 'planning', 'review', 'client', 'kunde', 'prosjekt',
            'project', 'deadline', 'frist'
        ]
        if any(word in content for word in work_indicators):
            return 'work'
        
        # Learning categories
        learning_indicators = [
            'kurs', 'course', 'training', 'webinar', 'workshop', 'learning',
            'seminar', 'conference', 'certification', 'opplæring'
        ]
        if any(word in content for word in learning_indicators):
            return 'learning'
        
        # Personal health/maintenance
        personal_indicators = [
            'sport', 'trening', 'gym', 'hobby', 'personal', 'frisør',
            'haircut', 'massage', 'yoga', 'meditation', 'løp', 'run'
        ]
        if any(word in content for word in personal_indicators):
            return 'personal'
        
        # Social events
        social_indicators = [
            'dinner', 'middag', 'party', 'fest', 'kaffe', 'coffee',
            'drinks', 'beer', 'øl', 'visit', 'besøk', 'friends', 'venner'
        ]
        if any(word in content for word in social_indicators):
            return 'social'
        
        # Calendar-based categorization
        if 'work' in calendar_name.lower():
            return 'work'
        elif 'family' in calendar_name.lower():
            return 'family'
        elif 'personal' in calendar_name.lower():
            return 'personal'
        
        return 'other'
    
    def _assess_preparation_needed(self, event: Dict) -> Dict[str, Any]:
        """Assess what preparation might be needed for an event"""
        title = event.get('summary', '').lower()
        description = event.get('description', '').lower()
        location = event.get('location', '')
        attendees = event.get('attendees', [])
        content = f"{title} {description}"
        
        preparation = {
            'materials_needed': False,
            'presentation_prep': False,
            'travel_prep': False,
            'childcare_needed': False,
            'documents_needed': False,
            'suggestions': []
        }
        
        # Presentation preparation
        if any(word in content for word in ['presentation', 'presentasjon', 'demo', 'pitch']):
            preparation['presentation_prep'] = True
            preparation['suggestions'].append("Prepare presentation materials")
        
        # Materials needed
        if any(word in content for word in ['meeting', 'møte', 'workshop', 'training']):
            preparation['materials_needed'] = True
            preparation['suggestions'].append("Bring notebook and pen")
        
        # Travel preparation
        if location and location.lower() not in ['home', 'hjemme', 'office', 'kontor']:
            preparation['travel_prep'] = True
            preparation['suggestions'].append(f"Plan travel to {location}")
        
        # Childcare consideration
        if len(attendees) > 0 and any(word in content for word in ['evening', 'kveld', 'dinner', 'middag']):
            preparation['childcare_needed'] = True
            preparation['suggestions'].append("Arrange childcare")
        
        # Document preparation
        if any(word in content for word in ['interview', 'intervju', 'appointment', 'avtale', 'legal', 'juridisk']):
            preparation['documents_needed'] = True
            preparation['suggestions'].append("Gather necessary documents")
        
        return preparation
    
    def _assess_family_impact(self, event: Dict) -> str:
        """Assess how the event impacts family time"""
        start_dt = event['start_datetime']
        duration = event.get('duration_minutes', 0)
        
        # Time-based assessment
        hour = start_dt.hour
        
        # Early morning (before 8 AM)
        if hour < 8:
            return 'early_start'
        
        # During typical work hours (8 AM - 5 PM)
        elif 8 <= hour <= 17:
            return 'work_hours'
        
        # Evening family time (5 PM - 8 PM)
        elif 17 < hour <= 20:
            return 'family_time'
        
        # Late evening (after 8 PM)
        elif hour > 20:
            return 'late_evening'
        
        # Weekend considerations
        if start_dt.weekday() >= 5:  # Saturday = 5, Sunday = 6
            if duration > 180:  # More than 3 hours
                return 'weekend_commitment'
            else:
                return 'weekend_minor'
        
        return 'normal'
    
    def _estimate_travel_time(self, location: str) -> int:
        """Estimate travel time in minutes based on location"""
        if not location:
            return 0
        
        location_lower = location.lower()
        
        # Home/no travel needed
        if any(word in location_lower for word in ['home', 'hjemme', 'huset']):
            return 0
        
        # Virtual meetings
        if any(word in location_lower for word in ['zoom', 'teams', 'meet', 'virtual', 'online']):
            return 0
        
        # Trondheim city center
        if any(word in location_lower for word in ['sentrum', 'midtbyen', 'city center', 'downtown']):
            return 30
        
        # NTNU/Universities
        if any(word in location_lower for word in ['ntnu', 'university', 'universitet', 'campus']):
            return 25
        
        # Nearby municipalities
        if any(word in location_lower for word in ['malvik', 'melhus', 'klæbu', 'selbu']):
            return 45
        
        # Default for unknown locations in Trondheim area
        return 20
    
    def _categorize_events(self, events: List[Dict]) -> Dict[str, List[Dict]]:
        """Categorize events by time and type"""
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        week_end = today_start + timedelta(days=7)
        
        categorized = {
            'today': [],
            'this_week': [],
            'priority': [],
            'family': [],
            'work': [],
            'learning': [],
            'personal': [],
            'social': []
        }
        
        for event in events:
            start_dt = event['start_datetime']
            category = event['category']
            priority = event['priority']
            
            # Time-based categorization
            if today_start <= start_dt < today_end:
                categorized['today'].append(event)
            elif today_end <= start_dt < week_end:
                categorized['this_week'].append(event)
            
            # Priority-based categorization
            if priority == 'high':
                categorized['priority'].append(event)
            
            # Type-based categorization
            if category in categorized:
                categorized[category].append(event)
        
        return categorized
    
    def _create_summary(self, categorized: Dict) -> Dict[str, Any]:
        """Create a summary of calendar events"""
        today_events = categorized['today']
        
        return {
            'today_count': len(today_events),
            'week_count': len(categorized['this_week']),
            'priority_count': len(categorized['priority']),
            'family_count': len(categorized['family']),
            'work_count': len(categorized['work']),
            'learning_count': len(categorized['learning']),
            'next_important': self._get_next_important_event(categorized['priority']),
            'today_overview': self._create_today_overview(today_events),
            'busiest_day': self._find_busiest_day(categorized['this_week']),
            'free_time_today': self._calculate_free_time_today(today_events)
        }
    
    def _create_recommendations(self, categorized: Dict) -> List[str]:
        """Create actionable recommendations based on calendar"""
        recommendations = []
        today_events = categorized['today']
        
        # Check for busy day
        if len(today_events) > 4:
            recommendations.append("Busy day ahead - consider preparing lunch and snacks")
        
        # Check for early meetings
        early_meetings = [e for e in today_events if e['start_datetime'].hour < 9]
        if early_meetings:
            recommendations.append("Early meeting today - prepare everything the night before")
        
        # Check for evening commitments
        evening_events = [e for e in today_events if e['start_datetime'].hour > 17]
        if evening_events:
            recommendations.append("Evening commitment - arrange childcare and dinner plans")
        
        # Check for high-priority events
        priority_today = [e for e in today_events if e['priority'] == 'high']
        if priority_today:
            recommendations.append("Important events today - review preparation needs")
        
        # Check for travel time
        travel_events = [e for e in today_events if e['travel_time'] > 20]
        if travel_events:
            recommendations.append("Events with travel time - plan departure accordingly")
        
        # Learning opportunities
        if categorized['learning']:
            recommendations.append("Learning opportunities this week - block preparation time")
        
        return recommendations[:5]  # Limit to top 5 recommendations
    
    def _get_next_important_event(self, priority_events: List[Dict]) -> Optional[Dict]:
        """Get the next important event"""
        if not priority_events:
            return None
        
        now = datetime.now()
        future_events = [e for e in priority_events if e['start_datetime'] > now]
        
        if future_events:
            next_event = min(future_events, key=lambda x: x['start_datetime'])
            return {
                'title': next_event['title'],
                'start_time': next_event['start_datetime'].strftime('%H:%M'),
                'date': next_event['start_datetime'].strftime('%A, %d %B'),
                'priority': next_event['priority'],
                'category': next_event['category'],
                'preparation_needed': bool(next_event['preparation_needed']['suggestions'])
            }
        
        return None
    
    def _create_today_overview(self, today_events: List[Dict]) -> str:
        """Create a text overview of today's events"""
        if not today_events:
            return "Ingen planlagte avtaler i dag"
        
        overview_parts = []
        
        # Count by category
        work_count = len([e for e in today_events if e['category'] == 'work'])
        family_count = len([e for e in today_events if e['category'] == 'family'])
        personal_count = len([e for e in today_events if e['category'] == 'personal'])
        
        if work_count:
            overview_parts.append(f"{work_count} jobbmøte{'r' if work_count > 1 else ''}")
        if family_count:
            overview_parts.append(f"{family_count} familieaktivitet{'er' if family_count > 1 else ''}")
        if personal_count:
            overview_parts.append(f"{personal_count} personlig avtale{'r' if personal_count > 1 else ''}")
        
        base_overview = f"{len(today_events)} avtale{'r' if len(today_events) > 1 else ''} i dag"
        
        if overview_parts:
            base_overview += f": {', '.join(overview_parts)}"
        
        # Add timing info
        if today_events:
            first_event = min(today_events, key=lambda x: x['start_datetime'])
            last_event = max(today_events, key=lambda x: x['start_datetime'])
            
            start_time = first_event['start_datetime'].strftime('%H:%M')
            end_time = last_event['end_datetime'].strftime('%H:%M')
            
            base_overview += f" (fra {start_time} til {end_time})"
        
        return base_overview
    
    def _find_busiest_day(self, week_events: List[Dict]) -> Optional[Dict]:
        """Find the busiest day this week"""
        if not week_events:
            return None
        
        day_counts = {}
        for event in week_events:
            date_key = event['start_datetime'].strftime('%Y-%m-%d')
            day_name = event['start_datetime'].strftime('%A')
            
            if date_key not in day_counts:
                day_counts[date_key] = {'name': day_name, 'count': 0, 'date': date_key}
            day_counts[date_key]['count'] += 1
        
        if day_counts:
            busiest = max(day_counts.values(), key=lambda x: x['count'])
            return busiest if busiest['count'] > 2 else None
        
        return None
    
    def _calculate_free_time_today(self, today_events: List[Dict]) -> Dict[str, Any]:
        """Calculate free time slots today"""
        if not today_events:
            return {'total_free_hours': 8, 'longest_break': '8+ hours', 'morning_free': True}
        
        # Sort events by start time
        sorted_events = sorted(today_events, key=lambda x: x['start_datetime'])
        
        now = datetime.now()
        work_day_start = now.replace(hour=8, minute=0, second=0, microsecond=0)
        work_day_end = now.replace(hour=18, minute=0, second=0, microsecond=0)
        
        free_periods = []
        current_time = max(now, work_day_start)
        
        for event in sorted_events:
            event_start = event['start_datetime']
            
            # Skip past events
            if event_start < now:
                continue
            
            # Add free period before this event
            if current_time < event_start:
                free_minutes = (event_start - current_time).total_seconds() / 60
                if free_minutes > 30:  # Only count significant free time
                    free_periods.append(free_minutes)
            
            current_time = max(current_time, event['end_datetime'])
        
        # Add remaining free time until end of work day
        if current_time < work_day_end:
            remaining_minutes = (work_day_end - current_time).total_seconds() / 60
            if remaining_minutes > 30:
                free_periods.append(remaining_minutes)
        
        total_free_minutes = sum(free_periods)
        longest_break = max(free_periods) if free_periods else 0
        
        return {
            'total_free_hours': round(total_free_minutes / 60, 1),
            'longest_break': f"{int(longest_break // 60)}h {int(longest_break % 60)}m" if longest_break > 60 else f"{int(longest_break)}m",
            'morning_free': len([e for e in today_events if e['start_datetime'].hour < 10]) == 0,
            'free_periods_count': len(free_periods)
        }

# Example usage
async def main():
    collector = CalendarCollector("path/to/credentials.json")
    calendar_data = await collector.collect_calendar_data(days_ahead=7)
    
    if 'error' not in calendar_data:
        print("Calendar Summary:")
        print(f"Today: {calendar_data['summary']['today_count']} events")
        print(f"This week: {calendar_data['summary']['week_count']} events")
        print(f"Priority events: {calendar_data['summary']['priority_count']}")
        
        print("\nToday's overview:", calendar_data['summary']['today_overview'])
        
        if calendar_data['recommendations']:
            print("\nRecommendations:")
            for rec in calendar_data['recommendations']:
                print(f"- {rec}")
        
        print("\nNext important event:")
        next_important = calendar_data['summary']['next_important']
        if next_important:
            print(f"- {next_important['title']} on {next_important['date']} at {next_important['start_time']}")
        else:
            print("- No high-priority events scheduled")
    else:
        print("Error:", calendar_data['error'])

if __name__ == "__main__":
    asyncio.run(main())