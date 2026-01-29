#!/usr/bin/env python3
"""
Google Calendar API Client for AI Agent
Uses service account authentication (same as Google Sheets)
"""

import os
import json
from datetime import datetime, timedelta
from pathlib import Path

# Google API
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Config
SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = Path.home() / '.config/google-sheets-mcp/service-account.json'


def get_calendar_service():
    """Get Google Calendar API service."""
    if not SERVICE_ACCOUNT_FILE.exists():
        raise FileNotFoundError(f"Service account key not found: {SERVICE_ACCOUNT_FILE}")
    
    credentials = service_account.Credentials.from_service_account_file(
        str(SERVICE_ACCOUNT_FILE),
        scopes=SCOPES
    )
    
    return build('calendar', 'v3', credentials=credentials)


def list_calendars():
    """List all calendars accessible to the service account."""
    service = get_calendar_service()
    
    print("📅 Calendars accessible to service account:")
    print("-" * 50)
    
    # Get calendar list
    page_token = None
    while True:
        calendar_list = service.calendarList().list(pageToken=page_token).execute()
        
        for calendar_list_entry in calendar_list['items']:
            cal_id = calendar_list_entry['id']
            cal_name = calendar_list_entry.get('summary', 'Unknown')
            primary = " (PRIMARY)" if calendar_list_entry.get('primary') else ""
            print(f"  • {cal_name}")
            print(f"    ID: {cal_id}{primary}")
            print()
        
        page_token = calendar_list.get('nextPageToken')
        if not page_token:
            break
    
    return calendar_list['items']


def create_event(calendar_id, summary, description, start_date, end_date=None,
                 start_time=None, end_time=None, recurrence=None, reminders=None):
    """
    Create a calendar event.
    
    Args:
        calendar_id: Calendar ID (use 'primary' for default)
        summary: Event title
        description: Event description
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD), defaults to start_date
        start_time: Start time (HH:MM), optional for all-day events
        end_time: End time (HH:MM), optional for all-day events
        recurrence: List of recurrence rules (e.g., ['RRULE:FREQ=DAILY;COUNT=5'])
        reminders: Dict with reminder settings
    
    Returns:
        Created event object
    """
    service = get_calendar_service()
    
    # Build event body
    event = {
        'summary': summary,
        'description': description,
    }
    
    # Set start/end time
    if start_time:
        # Timed event
        start_dt = f"{start_date}T{start_time}:00+07:00"
        end_dt = f"{end_date or start_date}T{end_time or start_time}:00+07:00"
        
        event['start'] = {
            'dateTime': start_dt,
            'timeZone': 'Asia/Bangkok',
        }
        event['end'] = {
            'dateTime': end_dt,
            'timeZone': 'Asia/Bangkok',
        }
    else:
        # All-day event
        event['start'] = {'date': start_date}
        event['end'] = {'date': end_date or start_date}
    
    # Add recurrence if specified
    if recurrence:
        event['recurrence'] = recurrence
    
    # Add reminders
    if reminders:
        event['reminders'] = reminders
    else:
        # Default reminders
        event['reminders'] = {
            'useDefault': False,
            'overrides': [
                {'method': 'popup', 'minutes': 60},  # 1 hour before
                {'method': 'popup', 'minutes': 1440},  # 1 day before
            ],
        }
    
    # Create event
    try:
        event = service.events().insert(calendarId=calendar_id, body=event).execute()
        print(f"✅ Event created: {event.get('htmlLink')}")
        return event
    except HttpError as e:
        print(f"❌ Error creating event: {e}")
        raise


def list_events(calendar_id, days=7):
    """List upcoming events."""
    service = get_calendar_service()
    
    now = datetime.utcnow()
    time_min = now.isoformat() + 'Z'
    time_max = (now + timedelta(days=days)).isoformat() + 'Z'
    
    events_result = service.events().list(
        calendarId=calendar_id,
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    
    events = events_result.get('items', [])
    
    if not events:
        print('No upcoming events found.')
        return []
    
    print(f"📅 Upcoming events (next {days} days):")
    print("-" * 50)
    
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        summary = event.get('summary', 'No title')
        print(f"  • {start}: {summary}")
    
    return events


def delete_event(calendar_id, event_id):
    """Delete an event by ID."""
    service = get_calendar_service()
    
    try:
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        print(f"✅ Event deleted: {event_id}")
    except HttpError as e:
        print(f"❌ Error deleting event: {e}")
        raise


# Default calendars to read from
DEFAULT_CALENDARS = [
    ('iicfounder@gmail.com', 'ส่วนตัว'),
    ('boat@ngs.in.th', 'NGS'),
    ('warawut@gritthailand.com', 'Grit Thailand'),
]


def list_all_events(days=1):
    """List events from all configured calendars."""
    from datetime import datetime, timedelta
    
    service = get_calendar_service()
    now = datetime.utcnow()
    time_min = now.isoformat() + 'Z'
    time_max = (now + timedelta(days=days)).isoformat() + 'Z'
    
    print(f'📅 ตารางนัดหมาย ({days} วัน)')
    print('=' * 70)
    
    all_events = []
    
    for cal_id, cal_name in DEFAULT_CALENDARS:
        try:
            events_result = service.events().list(
                calendarId=cal_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            if events:
                print(f'\n🗓️  {cal_name} ({cal_id}):')
                print('-' * 70)
                
                for event in events:
                    start = event['start'].get('dateTime', event['start'].get('date'))
                    summary = event.get('summary', 'ไม่มีชื่อ')
                    
                    # Format time
                    if 'T' in start:
                        # Has time
                        dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                        time_str = dt.strftime('%H:%M')
                        date_str = dt.strftime('%Y-%m-%d')
                    else:
                        # All day
                        time_str = 'ทั้งวัน'
                        date_str = start
                    
                    print(f'   {date_str} {time_str} | {summary}')
                    all_events.append({
                        'calendar': cal_name,
                        'date': date_str,
                        'time': time_str,
                        'summary': summary
                    })
            
        except Exception as e:
            print(f'\n❌ {cal_name}: {str(e)[:80]}')
    
    if not all_events:
        print('\nไม่มีนัดหมาย')
    
    print()
    return all_events


def main():
    """CLI for calendar operations."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Google Calendar CLI')
    subparsers = parser.add_subparsers(dest='command')
    
    # List calendars
    subparsers.add_parser('list-calendars', help='List accessible calendars')
    
    # List events (single calendar)
    list_parser = subparsers.add_parser('list-events', help='List upcoming events')
    list_parser.add_argument('--calendar', default='primary', help='Calendar ID')
    list_parser.add_argument('--days', type=int, default=7, help='Number of days')
    
    # List all events (all calendars)
    list_all_parser = subparsers.add_parser('today', help='Show today events from all calendars')
    list_all_parser.add_argument('--days', type=int, default=1, help='Number of days')
    
    # Create event
    create_parser = subparsers.add_parser('create', help='Create an event')
    create_parser.add_argument('--calendar', default='primary', help='Calendar ID')
    create_parser.add_argument('--title', required=True, help='Event title')
    create_parser.add_argument('--desc', default='', help='Event description')
    create_parser.add_argument('--date', required=True, help='Start date (YYYY-MM-DD)')
    create_parser.add_argument('--end-date', help='End date (YYYY-MM-DD)')
    create_parser.add_argument('--start-time', help='Start time (HH:MM)')
    create_parser.add_argument('--end-time', help='End time (HH:MM)')
    create_parser.add_argument('--recurring', action='store_true', help='Daily recurring')
    
    args = parser.parse_args()
    
    if args.command == 'list-calendars':
        list_calendars()
    elif args.command == 'list-events':
        list_events(args.calendar, args.days)
    elif args.command == 'today':
        list_all_events(args.days)
    elif args.command == 'create':
        recurrence = ['RRULE:FREQ=DAILY'] if args.recurring else None
        create_event(
            calendar_id=args.calendar,
            summary=args.title,
            description=args.desc,
            start_date=args.date,
            end_date=args.end_date,
            start_time=args.start_time,
            end_time=args.end_time,
            recurrence=recurrence
        )
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
