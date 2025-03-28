from urllib.request import Request
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import time
import os
import datetime
from datetime import timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from dateutil import tz
import chromedriver_autoinstaller

calendarId = 'f600105dc5bba4859808b1f5b8a5f3b00a2c802cbbd999a10689147dd615fb11@group.calendar.google.com'
today = datetime.datetime.now().strftime("%d-%m-%Y")


# Settings for Selenium
options = webdriver.ChromeOptions()
options.add_argument('--headless')  # Run in headless mode
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')



# Create a webdriver instance
chromedriver_autoinstaller.install()
driver = webdriver.Chrome(options=options)


# Function to authenticate and get the Google Calendar service
def google_calendar_service():
    SCOPES = ['https://www.googleapis.com/auth/calendar']

    creds = None
    # Verifica se esiste il file con le credenziali salvate
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    
    # Se non ci sono credenziali valide o è necessario il login
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Questo blocco si assicura che flow venga sempre creato se necessario
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        
        # Salva le credenziali per usi futuri
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    service = build('calendar', 'v3', credentials=creds)
    
    return service

# Function to create an event in the calendar
def create_event(service, event_title , start_date_time, end_date_time, location):
    event = {
        'summary': event_title,
        'location': location,
        'start': {
            'dateTime': start_date_time,
            'timeZone': 'Europe/Rome',
        },
        'end': {
            'dateTime': end_date_time,
            'timeZone': 'Europe/Rome',
        },
    }
    event = service.events().insert(calendarId=calendarId, body=event).execute()
    # print(f"Event created: {event['htmlLink']}")
    
# Function to delete an event from the calendar
def delete_event(service, event_title, start_datetime):
    # Define the time window for searching the existing event
    time_min = (datetime.datetime.fromisoformat(start_datetime) - datetime.timedelta(minutes=5)).isoformat() 
    time_max = (datetime.datetime.fromisoformat(start_datetime) + datetime.timedelta(minutes=5)).isoformat() 
    
    try:
        # Use the Google Calendar API to search for events within the time window
        events_result = service.events().list(
            calendarId=calendarId,  # Replace with your actual calendar ID
            timeMin=time_min,
            timeMax=time_max,
            # q = event_title, 
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
    except Exception as e:
        print("Error:", e)
        return
    
    event = events_result.get('items', [None])[0]  # Ottieni il primo evento o None se non esiste

    # Stampa l'evento trovato
    if event:
        print(f"Event found: {event}")
        if event['summary'].lower() == event_title.lower():
            service.events().delete(calendarId=calendarId, eventId=event['id']).execute()
            print(f"Event '{event_title}' deleted successfully.")
        else:
            print(f"No matching event found with title {event_title} at the specified time.")
    else:
        print(f"No event found with title {event_title} at the specified time.")
    
# Function to convert the extracted date and time into ISO 8601 format with Europe/Rome timezone
def convert_to_iso8601(date_str, time_str):
    # Define the format of the extracted date
    date_format = "%d-%m-%Y"  # Adjust this according to the extracted date format
    date = datetime.datetime.strptime(date_str, date_format)

    # Split the time string (e.g., '10:30 - 12:30') and parse each time
    start_time_str, end_time_str = time_str.split(" - ")
    time_format = "%H:%M"

    # Parse the start and end times
    start_time = datetime.datetime.strptime(start_time_str.strip(), time_format).time()
    end_time = datetime.datetime.strptime(end_time_str.strip(), time_format).time()

    # Combine the date and time to create full datetime objects
    start_datetime = datetime.datetime.combine(date, start_time)
    end_datetime = datetime.datetime.combine(date, end_time)

    # Set the timezone to Europe/Rome
    to_zone = tz.gettz('Europe/Rome')

    # Convert the datetime to the Europe/Rome timezone
    start_datetime = start_datetime.replace(tzinfo=to_zone)
    end_datetime = end_datetime.replace(tzinfo=to_zone)

    # Convert the datetime to ISO 8601 format
    iso8601_start = start_datetime.isoformat()
    iso8601_end = end_datetime.isoformat()

    return iso8601_start, iso8601_end

# Function to check if an event with the same title and start time already exists
def manage_event(service, event_title, start_datetime, end_datetime, location):
    # Define the time window for searching existing events (a few minutes around the event start time)
    time_min = (datetime.datetime.fromisoformat(start_datetime) - datetime.timedelta(minutes=5)).isoformat() 
    time_max = (datetime.datetime.fromisoformat(start_datetime) + datetime.timedelta(minutes=5)).isoformat() 
    
    # Use the Google Calendar API to search for events within the time window
    events_result = service.events().list(
        calendarId=calendarId,  # Replace with your actual calendar ID
        timeMin=time_min,
        timeMax=time_max,
        # q = event_title,  # if i use event title does'nt find equal events
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    event = next(iter(events_result.get('items', [])), None)
    
    if not event:
        if "annullato" not in event_title.lower():
            # Create event if no matching events are found
            print(f"Event not found, creating a new event... {event_title}")
            create_event(service, event_title, start_datetime, end_datetime, location)
    else:
        print(f"Event found: {event['summary']}")
        if event['summary'].lower() != event_title.lower():
            if "annullato" not in event_title.lower():
                # Create event if it doesn't match and is not marked as canceled
                print(f"Creating a new event... {event_title}")
                create_event(service, event_title, start_datetime, end_datetime, location)
        elif 'annullato' in event['summary'].lower():
            # Delete the event if it is marked as canceled
            delete_event(service, event['summary'], event['start']['dateTime'])


# Main function for scraping and creating events
def scrape_and_create_events():

    service = google_calendar_service()

    tomorrow_date = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%d-%m-%Y")
    url = f"https://gestioneorari.didattica.unimib.it/PortaleStudentiUnimib/index.php?view=easycourse&form-type=corso&include=corso&txtcurr=&anno=2024&scuola=&corso=E3101Q&anno2%5B%5D=GGG+T2%7C2&visualizzazione_orario=cal&date={tomorrow_date}&periodo_didattico=&_lang=it&list=1&week_grid_type=-1&ar_codes_=EC498980%7CEC498978%7CEC498979%7CEC498984%7CEC498983%7CEC499183%7CEC499196%7CEC499195%7CEC499730&ar_select_=true%7Ctrue%7Ctrue%7Cfalse%7Cfalse%7Ctrue%7Ctrue%7Ctrue%7Cfalse&col_cells=0&empty_box=0&only_grid=0&highlighted_date=0&all_events=0&faculty_group=0#"
    driver.get(url)
    time.sleep(20)  # Wait for the page to load

    # Extract data with Selenium and XPath
    row_number = 2
    # while True:
    count = 0
    while count < 10:
        try:
            # find title
            xpath = f"//*[@id='schedule']/div[2]/div[1]/div[{row_number}]/div[6]"
            title_element = driver.find_element(By.XPATH, xpath)
            title = title_element.text
            # print(f"Found title: {title}")
            
            
            # find location
            xpath = f"//*[@id='schedule']/div[2]/div[1]/div[{row_number}]/div[9]"   
            location_element = driver.find_element(By.XPATH, xpath)
            location = location_element.text
            # print(f"Found class: {class_name}")
            
            # find date
            xpath = f"//*[@id='schedule']/div[2]/div[1]/div[{row_number}]/div[4]/a"
            date_element = driver.find_element(By.XPATH, xpath)
            date = date_element.text
            # print(f"Found date: {date}")
            
            # find time
            xpath = f"//*[@id='schedule']/div[2]/div[1]/div[{row_number}]/div[5]"
            time_element = driver.find_element(By.XPATH, xpath)
            hour = time_element.text
            # print(f"Found time: {hour}")
            
            # Combine and convert the date and time to ISO 8601 format
            event_start_datetime, event_end_datetime = convert_to_iso8601(date, hour)
            # print(f"Event start datetime (ISO 8601): {event_start_datetime}")
            # print(f"Event end datetime (ISO 8601): {event_end_datetime}")
            
            manage_event(service, title, event_start_datetime, event_end_datetime, location)
            
            #only if need to delete all the next today events
            # delete_event(service, title, event_start_datetime)
      
            
            count += 1
            row_number += 1
        except Exception as e:
            print("No more elements found or error:", e)
            break
           
if __name__ == "__main__":
    scrape_and_create_events()
    driver.quit()
