import os
import json
import logging
from typing import Dict, Optional, Any
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

class AuthManager:
    def __init__(self, credentials_dir: str = "credentials"):
        self.credentials_dir = Path(credentials_dir)
        self.credentials_dir.mkdir(exist_ok=True)
        
        # File paths
        self.google_credentials_path = self.credentials_dir / "google_credentials.json"
        self.gmail_token_path = self.credentials_dir / "gmail_token.json"
        self.calendar_token_path = self.credentials_dir / "calendar_token.json"
        
        # Scopes for different services
        self.gmail_scopes = [
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/gmail.send'
        ]
        
        self.calendar_scopes = [
            'https://www.googleapis.com/auth/calendar.readonly'
        ]
        
        self.drive_scopes = [
            'https://www.googleapis.com/auth/drive.readonly'
        ]
    
    def setup_google_credentials(self, credentials_json_path: str) -> bool:
        """Copy Google credentials to the credentials directory"""
        try:
            source_path = Path(credentials_json_path)
            if not source_path.exists():
                logging.error(f"Credentials file not found: {credentials_json_path}")
                return False
            
            # Copy to credentials directory
            import shutil
            shutil.copy2(source_path, self.google_credentials_path)
            
            logging.info("Google credentials set up successfully")
            return True
            
        except Exception as e:
            logging.error(f"Failed to setup Google credentials: {e}")
            return False
    
    def authenticate_gmail(self, force_refresh: bool = False) -> Optional[Any]:
        """Authenticate Gmail API and return service object"""
        try:
            creds = self._get_or_refresh_credentials(
                self.gmail_token_path,
                self.gmail_scopes,
                force_refresh
            )
            
            if creds:
                service = build('gmail', 'v1', credentials=creds)
                logging.info("Gmail authentication successful")
                return service
            
            return None
            
        except Exception as e:
            logging.error(f"Gmail authentication failed: {e}")
            return None
    
    def authenticate_calendar(self, force_refresh: bool = False) -> Optional[Any]:
        """Authenticate Google Calendar API and return service object"""
        try:
            creds = self._get_or_refresh_credentials(
                self.calendar_token_path,
                self.calendar_scopes,
                force_refresh
            )
            
            if creds:
                service = build('calendar', 'v3', credentials=creds)
                logging.info("Calendar authentication successful")
                return service
            
            return None
            
        except Exception as e:
            logging.error(f"Calendar authentication failed: {e}")
            return None
    
    def authenticate_drive(self, force_refresh: bool = False) -> Optional[Any]:
        """Authenticate Google Drive API and return service object"""
        try:
            # Use same token as calendar for simplicity, but with drive scopes
            drive_token_path = self.credentials_dir / "drive_token.json"
            
            creds = self._get_or_refresh_credentials(
                drive_token_path,
                self.drive_scopes,
                force_refresh
            )
            
            if creds:
                service = build('drive', 'v3', credentials=creds)
                logging.info("Drive authentication successful")
                return service
            
            return None
            
        except Exception as e:
            logging.error(f"Drive authentication failed: {e}")
            return None
    
    def _get_or_refresh_credentials(self, token_path: Path, scopes: list, force_refresh: bool = False) -> Optional[Credentials]:
        """Get or refresh credentials for a specific service"""
        creds = None
        
        # Load existing token if not forcing refresh
        if not force_refresh and token_path.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(token_path), scopes)
            except Exception as e:
                logging.warning(f"Failed to load existing token from {token_path}: {e}")
        
        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    logging.info(f"Refreshed credentials for {token_path.name}")
                except Exception as e:
                    logging.error(f"Failed to refresh credentials: {e}")
                    creds = None
            
            # If refresh failed or no existing creds, get new ones
            if not creds:
                creds = self._get_new_credentials(scopes)
            
            # Save credentials
            if creds:
                try:
                    with open(token_path, 'w') as token_file:
                        token_file.write(creds.to_json())
                    logging.info(f"Saved credentials to {token_path}")
                except Exception as e:
                    logging.error(f"Failed to save credentials: {e}")
        
        return creds
    
    def _get_new_credentials(self, scopes: list) -> Optional[Credentials]:
        """Get new credentials through OAuth flow"""
        try:
            if not self.google_credentials_path.exists():
                logging.error("Google credentials file not found. Run setup_google_credentials() first.")
                return None
            
            flow = Flow.from_client_secrets_file(
                str(self.google_credentials_path),
                scopes=scopes
            )
            flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
            
            # Get authorization URL
            auth_url, _ = flow.authorization_url(prompt='consent')
            
            print(f"\nPlease visit this URL to authorize the application:")
            print(f"{auth_url}")
            print("\nAfter authorization, you'll get a code. Paste it below:")
            
            auth_code = input('Enter the authorization code: ').strip()
            
            if not auth_code:
                logging.error("No authorization code provided")
                return None
            
            # Exchange code for credentials
            flow.fetch_token(code=auth_code)
            
            logging.info("Successfully obtained new credentials")
            return flow.credentials
            
        except Exception as e:
            logging.error(f"Failed to get new credentials: {e}")
            return None
    
    def validate_all_credentials(self) -> Dict[str, bool]:
        """Validate all stored credentials"""
        results = {
            'gmail': False,
            'calendar': False,
            'drive': False
        }
        
        # Test Gmail
        try:
            gmail_service = self.authenticate_gmail()
            if gmail_service:
                # Test with a simple API call
                profile = gmail_service.users().getProfile(userId='me').execute()
                if profile:
                    results['gmail'] = True
        except Exception as e:
            logging.warning(f"Gmail validation failed: {e}")
        
        # Test Calendar
        try:
            calendar_service = self.authenticate_calendar()
            if calendar_service:
                # Test with a simple API call
                calendar_list = calendar_service.calendarList().list(maxResults=1).execute()
                if calendar_list:
                    results['calendar'] = True
        except Exception as e:
            logging.warning(f"Calendar validation failed: {e}")
        
        # Test Drive
        try:
            drive_service = self.authenticate_drive()
            if drive_service:
                # Test with a simple API call
                about = drive_service.about().get(fields='user').execute()
                if about:
                    results['drive'] = True
        except Exception as e:
            logging.warning(f"Drive validation failed: {e}")
        
        return results
    
    def revoke_credentials(self, service: str = 'all') -> bool:
        """Revoke and delete stored credentials"""
        try:
            if service in ['gmail', 'all']:
                if self.gmail_token_path.exists():
                    self.gmail_token_path.unlink()
                    logging.info("Gmail credentials revoked")
            
            if service in ['calendar', 'all']:
                if self.calendar_token_path.exists():
                    self.calendar_token_path.unlink()
                    logging.info("Calendar credentials revoked")
            
            if service in ['drive', 'all']:
                drive_token_path = self.credentials_dir / "drive_token.json"
                if drive_token_path.exists():
                    drive_token_path.unlink()
                    logging.info("Drive credentials revoked")
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to revoke credentials: {e}")
            return False
    
    def get_credential_status(self) -> Dict[str, Dict[str, Any]]:
        """Get detailed status of all credentials"""
        status = {}
        
        for service, token_path in [
            ('gmail', self.gmail_token_path),
            ('calendar', self.calendar_token_path),
            ('drive', self.credentials_dir / "drive_token.json")
        ]:
            service_status = {
                'exists': token_path.exists(),
                'valid': False,
                'expires_at': None,
                'scopes': []
            }
            
            if token_path.exists():
                try:
                    with open(token_path, 'r') as f:
                        token_data = json.load(f)
                    
                    # Get scopes
                    if service == 'gmail':
                        scopes = self.gmail_scopes
                    elif service == 'calendar':
                        scopes = self.calendar_scopes
                    else:
                        scopes = self.drive_scopes
                    
                    creds = Credentials.from_authorized_user_file(str(token_path), scopes)
                    
                    service_status['valid'] = creds.valid
                    service_status['expires_at'] = creds.expiry.isoformat() if creds.expiry else None
                    service_status['scopes'] = scopes
                    
                except Exception as e:
                    logging.warning(f"Failed to read {service} credentials: {e}")
            
            status[service] = service_status
        
        return status

# Example usage and setup script
def main():
    """Interactive setup script for authentication"""
    auth_manager = AuthManager()
    
    print("=== Morning Digest Authentication Setup ===\n")
    
    # Check if Google credentials exist
    if not auth_manager.google_credentials_path.exists():
        print("Google credentials not found.")
        print("Please download the credentials.json file from Google Cloud Console")
        print("and provide the path to it:")
        
        credentials_path = input("Path to credentials.json: ").strip()
        
        if not auth_manager.setup_google_credentials(credentials_path):
            print("Failed to setup Google credentials. Exiting.")
            return
        
        print("✓ Google credentials setup complete\n")
    
    # Check current status
    print("Checking current authentication status...")
    status = auth_manager.get_credential_status()
    
    for service, info in status.items():
        status_text = "✓ Valid" if info['valid'] else "✗ Invalid/Missing"
        print(f"{service.title()}: {status_text}")
    
    print()
    
    # Setup each service
    services_to_setup = []
    
    for service, info in status.items():
        if not info['valid']:
            setup = input(f"Setup {service} authentication? (y/n): ").strip().lower()
            if setup == 'y':
                services_to_setup.append(service)
    
    # Authenticate services
    for service in services_to_setup:
        print(f"\n--- Setting up {service.title()} ---")
        
        if service == 'gmail':
            gmail_service = auth_manager.authenticate_gmail(force_refresh=True)
            if gmail_service:
                print(f"✓ {service.title()} authentication successful")
            else:
                print(f"✗ {service.title()} authentication failed")
        
        elif service == 'calendar':
            calendar_service = auth_manager.authenticate_calendar(force_refresh=True)
            if calendar_service:
                print(f"✓ {service.title()} authentication successful")
            else:
                print(f"✗ {service.title()} authentication failed")
        
        elif service == 'drive':
            drive_service = auth_manager.authenticate_drive(force_refresh=True)
            if drive_service:
                print(f"✓ {service.title()} authentication successful")
            else:
                print(f"✗ {service.title()} authentication failed")
    
    # Final validation
    print("\n--- Final Validation ---")
    validation_results = auth_manager.validate_all_credentials()
    
    all_valid = True
    for service, is_valid in validation_results.items():
        status_text = "✓ Working" if is_valid else "✗ Not working"
        print(f"{service.title()}: {status_text}")
        if not is_valid:
            all_valid = False
    
    if all_valid:
        print("\n🎉 All services authenticated successfully!")
        print("You can now run the morning digest automation.")
    else:
        print("\n⚠️  Some services failed authentication.")
        print("Please check the logs and try again.")

if __name__ == "__main__":
    main()