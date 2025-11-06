import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json
import logging
import re
import base64
from email.mime.text import MIMEText

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import os

class GmailCollector:
    def __init__(self, credentials_path: str, token_path: str = "gmail_token.json"):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None
        self.scopes = [
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/gmail.send'
        ]
    
    def authenticate(self):
        """Handle Gmail API authentication"""
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
                print(f'Please visit this URL to authorize Gmail access: {auth_url}')
                
                auth_code = input('Enter the authorization code: ')
                flow.fetch_token(code=auth_code)
                creds = flow.credentials
            
            # Save credentials
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())
        
        self.service = build('gmail', 'v1', credentials=creds)
    
    async def collect_newsletters(self, hours_back: int = 24) -> Dict[str, Any]:
        """Collect newsletters from the last 24 hours"""
        if not self.service:
            self.authenticate()
        
        try:
            # Calculate time range
            since_time = datetime.now() - timedelta(hours=hours_back)
            since_timestamp = int(since_time.timestamp())
            
            # Enhanced newsletter detection query
            queries = [
                f'after:{since_timestamp} (unsubscribe OR newsletter OR digest OR "weekly update" OR "daily briefing")',
                f'after:{since_timestamp} from:(substack.com OR medium.com OR mailchimp OR constantcontact)',
                f'after:{since_timestamp} subject:(newsletter OR digest OR roundup OR briefing OR update OR highlights)'
            ]
            
            all_newsletters = []
            seen_message_ids = set()
            
            for query in queries:
                messages = await self._get_messages(query)
                for message in messages:
                    if message['id'] not in seen_message_ids:
                        newsletter_data = await self._extract_newsletter_content(message)
                        if newsletter_data:
                            all_newsletters.append(newsletter_data)
                            seen_message_ids.add(message['id'])
            
            # Sort by newsletter score and recency
            all_newsletters.sort(key=lambda x: (x.get('newsletter_score', 0), x.get('timestamp', 0)), reverse=True)
            
            return {
                'newsletters': all_newsletters,
                'count': len(all_newsletters),
                'collection_time': datetime.now().isoformat(),
                'categories': self._categorize_newsletters(all_newsletters)
            }
            
        except Exception as e:
            logging.error(f"Gmail newsletter collection failed: {e}")
            return {'error': f'Failed to collect newsletters: {str(e)}'}
    
    async def _get_messages(self, query: str) -> List[Dict]:
        """Get messages matching the query"""
        try:
            result = self.service.users().messages().list(userId='me', q=query, maxResults=50).execute()
            messages = result.get('messages', [])
            
            # Get next page if available (up to 100 total messages)
            if 'nextPageToken' in result and len(messages) < 100:
                next_result = self.service.users().messages().list(
                    userId='me', 
                    q=query, 
                    pageToken=result['nextPageToken'],
                    maxResults=50
                ).execute()
                messages.extend(next_result.get('messages', []))
            
            return messages
            
        except Exception as e:
            logging.error(f"Error getting messages: {e}")
            return []
    
    async def _extract_newsletter_content(self, message: Dict) -> Optional[Dict]:
        """Extract content from potential newsletter message"""
        try:
            msg_id = message['id']
            msg_detail = self.service.users().messages().get(
                userId='me', 
                id=msg_id,
                format='full'
            ).execute()
            
            # Extract headers
            headers = {h['name']: h['value'] for h in msg_detail['payload']['headers']}
            
            sender = headers.get('From', '')
            subject = headers.get('Subject', '')
            date_header = headers.get('Date', '')
            
            # Extract content
            content = self._extract_message_content(msg_detail['payload'])
            
            # Calculate newsletter likelihood
            newsletter_score = self._calculate_newsletter_score(sender, subject, content)
            
            if newsletter_score > 0.4:  # Lower threshold to capture more newsletters
                return {
                    'sender': self._clean_sender(sender),
                    'sender_email': self._extract_email(sender),
                    'subject': subject,
                    'date': date_header,
                    'timestamp': self._parse_email_date(date_header),
                    'content': self._clean_content(content),
                    'snippet': msg_detail.get('snippet', ''),
                    'newsletter_score': newsletter_score,
                    'message_id': msg_id,
                    'category': self._categorize_newsletter(sender, subject, content),
                    'key_topics': self._extract_key_topics(content),
                    'has_offers': self._detect_offers(content),
                    'has_events': self._detect_events(content)
                }
            
            return None
            
        except Exception as e:
            logging.error(f"Error extracting newsletter content: {e}")
            return None
    
    def _extract_message_content(self, payload: Dict) -> str:
        """Extract text content from email payload"""
        content = ""
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data', '')
                    if data:
                        content += base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                elif part['mimeType'] == 'text/html':
                    data = part['body'].get('data', '')
                    if data:
                        html_content = base64.urlsafe_b