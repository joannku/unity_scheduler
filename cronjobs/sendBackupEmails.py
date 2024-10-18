import sys
import os

# Add the parent directory (or any specific directory) to PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.OutlookEmailer import OutlookEmailer
from datetime import datetime

# Load creds
creds = 'admin/creds.json'
emailer = OutlookEmailer(creds)

# Define the directory to search for CSV files
directory = "/data/jkuc/unity_scheduler/data/local"

# Function to find all CSV files within the directory, including subdirectories
def find_csv_files(directory):
    csv_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".csv"):
                csv_files.append(os.path.join(root, file))
    return csv_files

# Get list of all CSV files to attach
attachments = find_csv_files(directory)

# Get today's date for the email subject
today = datetime.today().strftime('%Y-%m-%d')
time = datetime.today().strftime('%H:%M:%S')
today_string = f"Backup csv report for {today}, {time}"
print("Attachments being sent:", attachments)

# Send the email
emailer.send_email_from_outlook(
    sender='unity-project@ucl.ac.uk',
    recepients=['unity-project@ucl.ac.uk'],
    subject=f"UNITY Server Backup report for {today}",
    email_body=today_string,
    attachments_paths=attachments,
    code="BackupReport"
)
