import json
import pandas as pd
import logging
import os
import shutil
import re
import filecmp
import csv
import webbrowser
from datetime import datetime, timedelta
from O365 import Account, FileSystemTokenBackend, Message
from oauth2client.service_account import ServiceAccountCredentials
import time
import numpy as np
import textwrap

class OutlookEmailer:

    def __init__(self, creds_path):
        """
        Initialize the OutlookEmailer by loading credentials from the given file.
        
        :param creds_path: Path to the credentials JSON file.
        """
        self.creds_dict = self._load_creds(creds_path)

    def _load_creds(self, path):
        """
        Load credentials from the provided file path.
        
        :param path: Path to the credentials JSON file.
        :return: A dictionary containing the credentials.
        """
        with open(path) as file:
            creds_data = json.load(file)

        return {
            'description': creds_data["outlook_description"],
            'client_secret': creds_data["outlook_client_secret"],
            'application_id': creds_data["outlook_application_id"],
            'shared_mailbox': creds_data["outlook_shared_mailbox"],
            'personal_mailbox': creds_data["outlook_personal_mailbox"],
            'tenant_id': creds_data["outlook_tenant_id"]
        }
    
    def _fold_lines(self, ics_content):
        """
        Fold long lines according to ICS file format rules.
        Lines longer than 75 characters should be wrapped with a space on the following line.
        """
        lines = ics_content.splitlines()
        folded_lines = []
        
        for line in lines:
            while len(line) > 75:
                # Split the line at 75 characters and fold it to the next line
                folded_lines.append(line[:75])
                line = ' ' + line[75:]
            folded_lines.append(line)
        
        return '\r\n'.join(folded_lines)


    def get_creds(self, creds_file_path):
        """
        Get credentials by loading them from a specified path.
        
        :param creds_file_path: Path to the credentials JSON file.
        :return: A dictionary containing the credentials.
        """
        return self._load_creds(creds_file_path)

    def load_attachments(self, folder_path='attachments'):
        files = os.listdir(folder_path)
        return {os.path.splitext(file)[0]: os.path.join(folder_path, file) for file in files}

    def authenticate_outlook(self, mailbox='personal'):
        credentials = (self.creds_dict['application_id'], self.creds_dict['client_secret'])
        token_backend = FileSystemTokenBackend(token_path='.', token_filename='o365_token.txt')

        # Determine which mailbox to use
        if mailbox == 'shared':
            main_resource = self.creds_dict['shared_mailbox']
        else:
            main_resource = self.creds_dict['personal_mailbox']
        
        # Create an Account object with the chosen mailbox
        account = Account(credentials, token_backend=token_backend, main_resource=main_resource)

        # Add 'Mail.Send' to the scopes
        scopes = ['User.Read', 'Mail.Read', 'Mail.Send', 'Mail.Read.Shared', 'Mail.Send.Shared']

        # Try to load the token from the file
        if not account.is_authenticated:
            # Get the authorization URL
            url, _ = account.con.get_authorization_url(requested_scopes=scopes)

            # Open the URL in a web browser
            webbrowser.open(url)

            # Prompt the user to manually copy the authentication URL
            print("Please manually copy the authentication URL from the web browser and paste it below.")
            auth_url = input("Authentication URL: ")

            # Authenticate with the provided URL and scopes
            if account.authenticate(url=auth_url, scopes=scopes):
                # Save the token to the file
                "Authentication successful. Token saved to 'o365_token.txt'."
            else:
                print("Authentication failed.")
                return None

        return account


    def send_email_from_outlook(self, sender, recepients, subject, email_body, attachments_paths, code=None):

        account = self.authenticate_outlook(self.creds_dict)

        if account is not None and account.is_authenticated:
            print('Outlook email authentication successful.')

            m = account.new_message()
            m.sender.address = sender  # The shared mailbox
            m.to.add(recepients)
            m.subject = subject

            # Check if attachments_paths is not None
            if attachments_paths is not None:
                # Loop over attachments paths
                for path in attachments_paths:
                    # Skip over None values
                    if path is not None:
                        # Add the attachment
                        m.attachments.add(path)

            m.body = email_body
            m.send()

            print(f"Email {code} from {sender} to {recepients} sent successfully!")
            return True
        else:
            print("Failed to send email. Authentication unsuccessful.")
            return False

        #TODO: Figure out when authentication expires, and how to make it last longer?

    def create_ics_attachment(self, subject, description, start_time, end_time, location):
        # Generate the ICS content as a string
        ics_content = textwrap.dedent(f"""\
    BEGIN:VCALENDAR
    VERSION:2.0
    PRODID:-//Your Organization//NONSGML v1.0//EN
    BEGIN:VEVENT
    UID:{datetime.now().strftime('%Y%m%dT%H%M%SZ')}
    DTSTAMP:{datetime.now().strftime('%Y%m%dT%H%M%SZ')}
    DTSTART:{start_time.strftime('%Y%m%dT%H%M%SZ')}
    DTEND:{end_time.strftime('%Y%m%dT%H%M%SZ')}
    SUMMARY:{subject}
    DESCRIPTION:{description}
    LOCATION:{location}
    END:VEVENT
    END:VCALENDAR
    """)

        # Ensure lines don't exceed 75 characters for ICS format
        ics_content = self._fold_lines(ics_content)

        # Write ICS content to a file
        ics_file_path = "calendarInvite.ics"
        with open(ics_file_path, 'w') as f:
            f.write(ics_content)

        return ics_file_path

    
    def is_valid_email(self, email):
        email = email.lower()  
        email_regex = r'^\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b$'
        return re.match(email_regex, email) is not None
    
    
    def get_email_template(self, email_code, templates_df):
        mask = templates_df["EmailCode"].astype(str) == email_code
        email_body = templates_df[mask]['EmailBody'].iloc[0]
        subject = templates_df[mask]['Subject'].iloc[0]
        escaped_email_body = re.sub(r"{(?!\w)", "{{", email_body)
        escaped_email_body = re.sub(r"(?<=\W)}", "}}", escaped_email_body)
        return subject, escaped_email_body

    def send_reminders(self, email_list, email_code, templates_df):
        if not email_list:
            return

        subject, email_body = self.get_email_template(email_code, templates_df)
        
        for email in email_list:
            self.send_email_from_outlook(self.creds_dict, SENDER_EMAIL, [email], subject, email_body, attachments_paths=None, code=email_code)
            self.google_sheet.attempt_request(self.google_sheet.update_column_value, 'Journalling Sign Ups', 5, "Email", email)
            self.google_sheet.attempt_request(self.google_sheet.update_column_value, 'Journalling Sign Ups', 5, "EmailCode", email_code)
            self.google_sheet.attempt_request(self.google_sheet.update_column_value, 'Journalling Sign Ups', 5, "SentAt", str(dt.datetime.now()))

    def generate_src_tag(self, file_paths):
        src_tags = {}
        
        for file_path in file_paths:
            # Encode the image in base64
            encoded_image = self.encode_image_base64(file_path)
            
            # Extract the file extension (without the dot)
            file_extension = os.path.splitext(file_path)[1][1:]
            
            # Generate the filename (without the extension)
            filename = os.path.splitext(os.path.basename(file_path))[0]
            
            # Generate the src tag
            src_tag = f'<img src="data:image/{file_extension};base64,{encoded_image}" alt="{filename} Image" width="200">'
            
            # Append the src tag to the dictionary
            src_tags[filename] = src_tag
        
        return src_tags

    def encode_image_base64(image_path):
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        return encoded_string
    

    def find_file_with_extension(self, directory, filename_prefix):
        # List all files in the given directory
        files = os.listdir(directory)
        
        # Search for a file that starts with the given filename_prefix
        for file in files:
            if file.startswith(filename_prefix):
                return file  # return the full filename including its extension
        return None  # return None if no matching file was found

    def read_emails_from_outlook(self, folder_name='Inbox', query=None, limit=10, mailbox='personal'):
    # Authenticate with the specified mailbox
        account = self.authenticate_outlook(mailbox=mailbox)
        if not account or not account.is_authenticated:
            print("! Failed to authenticate Outlook account for reading emails.")
            return None

        # Get the mailbox
        if mailbox == 'personal':
            mailbox = self.creds_dict["personal_mailbox"]
        elif mailbox == 'shared':
            mailbox = self.creds_dict["shared_mailbox"]

        mailbox = account.mailbox(mailbox)

        # Get the folder to read emails from (default is 'Inbox')
        folder = mailbox.get_folder(folder_name) if folder_name != 'Inbox' else mailbox.inbox_folder()

        # Query emails
        try:
            emails = folder.get_messages(limit=limit, query=query)
        except Exception as e:
            print(f"Error retrieving emails: {e}")
            return None

        email_data = []
        for message in emails:
            email_info = {
                'subject': message.subject,
                'from': message.sender.address,
                'to': [recipient.address for recipient in message.to],
                'received': message.received,
                'body': message.body,
                'attachments': [attachment.name for attachment in message.attachments]
            }
            email_data.append(email_info)

            # Attempt to mark emails as read
            # try:
            #     message.mark_as_read()
            # except Exception as e:
            #     print(f"Error marking message as read (message subject: {message.subject}): {e}")  # Print the specific error encountered
            #     continue

        return email_data