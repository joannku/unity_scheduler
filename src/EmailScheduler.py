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
from OutlookEmailer import OutlookEmailer


class Scheduler:

    def __init__(self, paths, backup_limit=60, overwrite_local=True):

        self.paths = self.__load_paths(paths)
        self.__reload_dfs()
        
        self.local_dir = self.paths['local_dir']
        self.backup_dir = self.paths['backup_dir']
        self.log_file = self.paths['log_file']

        self.missing_schedule_checked = False
        
        self.emailer = OutlookEmailer(self.paths['creds'])

        self.date_time_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.date_time_now_fileformat = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.backup_limit = backup_limit
        self.overwrite_local = overwrite_local
        
        self.dates = ['V1_Date', 'V2_Date', 'V3_Date', 'V4_Date', 'V5_Date', 'V6_Date', 'V7_Date']
        self.times = ['V1_Time', 'V2_Time', 'V3_Time', 'V4_Time', 'V5_Time', 'V6_Time', 'V7_Time']

        logging.basicConfig(
            filename=self.log_file, 
            level=logging.INFO, 
            format='%(asctime)s - %(levelname)s - %(message)s', 
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # load dataframes
    
    def __reload_dfs(self):
        # local
        self.df_vs_l = pd.read_csv(self.paths['visit_schedule_local'])
        self.df_es_l = pd.read_csv(self.paths['email_schedule_local'])
        self.df_et_l = pd.read_csv(self.paths['email_templates_local'])
        self.df_el_l = pd.read_csv(self.paths['email_log_local'])
        # streamlit
        self.df_vs_s = pd.read_csv(self.paths['visit_schedule_streamlit'])
        self.df_et_s = pd.read_csv(self.paths['email_templates_streamlit'])
    
    def __load_paths(self, paths):
        with open(paths, 'r') as f:
            paths = json.load(f)
        return paths

    def backup_local_csvs(self):
        print("# Backing up local CSVs.")
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
            
        log_details = []
        
        for filename in os.listdir(self.local_dir):
            if filename.endswith('.csv'):
                subfolder_name = filename.rsplit('.', 1)[0]
                subfolder_path = os.path.join(self.backup_dir, subfolder_name)
                
                if not os.path.exists(subfolder_path):
                    os.makedirs(subfolder_path)

                source_file_path = os.path.join(self.local_dir, filename)

                # Get the most recent backup file in the subfolder (if any)
                existing_backups = [f for f in os.listdir(subfolder_path) if f.endswith('.csv')]
                existing_backups.sort(reverse=True)  # Sort backups by date

                most_recent_backup = existing_backups[0] if existing_backups else None
                most_recent_backup_path = os.path.join(subfolder_path, most_recent_backup) if most_recent_backup else None

                # Compare the current file with the most recent backup (if any)
                if most_recent_backup_path and filecmp.cmp(source_file_path, most_recent_backup_path, shallow=False):
                    log_details.append(f"    No changes detected in {filename}, skipping backup.")
                else:
                    backup_filename = f"{subfolder_name}_{self.date_time_now_fileformat}.csv"
                    backup_file_path = os.path.join(subfolder_path, backup_filename)
                    if self.overwrite_local:
                        shutil.copy2(source_file_path, backup_file_path)
                    log_details.append(f"    * Backed up {filename}.")

        # Write log details to the log file
        with open(self.log_file, 'a') as log:
            for detail in log_details:
                log.write(detail + '\n')
                print(detail)
        
        print('    > Backup complete.')

    def clear_old_backups(self):
        print("# Clearing old backups.")
        print(f"    Starting to scan {self.backup_dir}...")  # Debugging print
        pattern = re.compile(r"(\d{8})_(\d{6})\.csv$")
        for foldername, _, filenames in os.walk(self.backup_dir):
            print(f"    Scanning folder: {foldername}")  # Debugging print
            for filename in filenames:
                match = pattern.search(filename)
                if not match:
                    print(f"    Skipping: {filename}")  # Debugging print for filenames that don't match the pattern
                    continue
                
                date_str, time_str = match.groups()
                
                # Convert date and time strings to a datetime object
                file_date = datetime.strptime(date_str + time_str, "%Y%m%d%H%M%S")
                self.dtm = datetime.strptime(self.date_time_now_fileformat, "%Y%m%d_%H%M%S")
                
                # Check file age
                if self.backup_limit == 0:
                    # remove all files
                    file_path = os.path.join(foldername, filename)
                    try:
                        os.remove(file_path)
                        print(f"    Removed {file_path}")
                    except Exception as e:
                        print(f"    Unable to remove {file_path}. Reason: {e}")
                elif (self.dtm - file_date).days > self.backup_limit:
                    file_path = os.path.join(foldername, filename)
                    try:
                        os.remove(file_path)
                        print(f"    Removed {file_path}")
                    except Exception as e:
                        print(f"    Unable to remove {file_path}. Reason: {e}")


        print(f"    > Finished scanning {self.backup_dir}.")  # Debugging print

    def check_for_changes(self):
        print("# Checking for changes between local and streamlit files.")
        pairs = []
        grouped_paths = {}
        changes_dict = {}

        # Step 1: Group paths by their common prefix
        for key, path in self.paths.items():
            # if key does not contain an underscore, skip
            if '_' not in key:
                continue
            prefix, suffix = key.rsplit('_', 1)
            if prefix not in grouped_paths:
                grouped_paths[prefix] = []
            grouped_paths[prefix].append((suffix, path))

        # Step 2: Create pairs from the grouped paths
        for prefix, path_list in grouped_paths.items():
            if len(path_list) > 1:
                for i in range(len(path_list)):
                    for j in range(i + 1, len(path_list)):
                        suffix1, path1 = path_list[i]
                        suffix2, path2 = path_list[j]
                        pairs.append(((suffix1, path1), (suffix2, path2)))

        # Step 3: Compare files in each pair and check for changes
        for pair in pairs:
            (suffix1, path1), (suffix2, path2) = pair
            filename = path1.split('/')[-1]

            # Compare the files and capture changes
            if filecmp.cmp(path1, path2, shallow=False):
                print(f"    No updates in {filename}.")
            else:
                print(f"    ! Changes detected in {filename}.")
                self.process_changes(filename, path1, path2)
                if self.overwrite_local:
                    shutil.copy2(path2, path1)
                    print(f"    * Updated {filename}.")
                
                # If email templates have changed, update existing schedules
                if filename == '3_email_templates.csv':
                    self.update_existing_participants_schedule(self.get_email_templates())

        print('    > Check for changes completed.')
        return changes_dict


    def get_email_templates(self):
        """
        Load the email templates from the local file.
        """
        email_templates = {}
        # reload dfs
        self.__reload_dfs()
        for index, row in self.df_et_l.iterrows():
            email_templates[row['EmailCode']] = {
                'Subject': row['Subject'],
                'EmailBody': row['EmailBody'],
                'Offset': row['Offset'],
                'VisitNumber': row['VisitNumber'],
            }
        return email_templates


    def process_changes(self, filename, path1, path2):
        if filename == '1_visit_schedule.csv':
            self.process_visit_schedule_changes(filename, path1, path2)
                
    
    def process_visit_schedule_changes(self, filename, path1, path2):
        pids_needing_new_schedule = []
        
        for index, row in self.df_vs_s.iterrows():
            pid = row['ParticipantID']

            # NEW PARTICIPANT
            if not pid in self.df_vs_l['ParticipantID'].values:
                print("        New participant registered:", pid)
                pids_needing_new_schedule.append(pid)

            # CHANGES TO EXISTING PARTICIPANT
            else:
                row_l = self.df_vs_l[self.df_vs_l['ParticipantID'] == pid]
                row_s = self.df_vs_s[self.df_vs_s['ParticipantID'] == pid]
                if not row_l.equals(row_s):
                    print("        Visit information updated for participant:", pid)
                    pids_needing_new_schedule.append(pid)

        if pids_needing_new_schedule:
            print("    > Generating new email schedule for updated participants:", pids_needing_new_schedule)
            self.generate_email_schedule(pids_needing_new_schedule)


    def check_missing_schedule(self): 
        
        print("# Checking for missing schedules.")
        pids_needing_new_schedule = []               
        # PARTICIPANT WITH MISSING EMAIL SCHEDULE
        for pid in self.df_vs_l['ParticipantID'].values:
            if pid not in pids_needing_new_schedule:
                if not pid in self.df_es_l['ParticipantID'].values:
                    print("    Participant missing email schedule:", pid)
                    pids_needing_new_schedule.append(pid)
            
        if len(pids_needing_new_schedule) > 0:
            print("    > Generating new email schedule for participants:", pids_needing_new_schedule)
            self.generate_email_schedule(pids_needing_new_schedule)

        self.missing_schedule_checked = True

        if not len(pids_needing_new_schedule) > 0:
            print("    > No missing schedules found.")

        return pids_needing_new_schedule

    def generate_email_schedule(self, pids):
        email_templates = {}
        for index, row in self.df_et_l.iterrows():
            email_templates[row['EmailCode']] = {
                'Subject': row['Subject'],
                'EmailBody': row['EmailBody'],
                'Offset': row['Offset'],
                'VisitNumber': row['VisitNumber'],
            }
        
        print("    Loaded email codes:", email_templates.keys())

        rows_to_add = []
        for pid in pids:
            # Remove future scheduled emails for the participant before creating a new schedule
            self.remove_future_scheduled_emails(pid)

            # Generate new email schedule only if the EmailCode is not already present for this participant
            participant_row = self.df_vs_l.loc[self.df_vs_l['ParticipantID'] == pid]
            existing_email_codes = self.df_es_l[self.df_es_l['ParticipantID'] == pid]['EmailCode'].tolist()

            participant_arm = participant_row['Arm'].values[0]

            for email_code, info in email_templates.items():
                if '-' in email_code:
                    suffix = email_code.split('-')[-1]
                    if (suffix == 'HA' and participant_arm != 'Healthy Arm') or \
                        (suffix == 'AA' and participant_arm != 'Alcohol Arm'):
                        continue
                if email_code not in existing_email_codes:
                    rows_to_add.append({
                        'ParticipantID': pid,
                        'EmailCode': email_code,
                        'ScheduledDate': self.calculate_scheduled_date(pid, info['VisitNumber'], info['Offset']),
                        'UpdatedAt': self.date_time_now,
                    })

        new_rows = pd.DataFrame(rows_to_add)
        self.df_es_l = pd.concat([self.df_es_l, new_rows], axis=0).reset_index(drop=True)
        if self.overwrite_local:
            self.df_es_l.to_csv(self.paths['email_schedule_local'], index=False)
            self.__reload_dfs()
            print("      * Added new email schedule for participants: ", pids)

        # Check for existing participants to update their schedule with new templates
        self.update_existing_participants_schedule(email_templates)

    def update_existing_participants_schedule(self, email_templates):
        """
        Update the email schedule for existing participants if there are new email templates added.
        """
        print("    Checking for new email templates to update existing schedules...")
        
        # Get all participants who already have a schedule
        participants = self.df_es_l['ParticipantID'].unique()
        
        rows_to_add = []
        for pid in participants:
            participant_arm = self.df_vs_l.loc[self.df_vs_l['ParticipantID'] == pid]['Arm'].values[0]
            # Retrieve the list of existing email codes scheduled for this participant
            existing_email_codes = self.df_es_l[self.df_es_l['ParticipantID'] == pid]['EmailCode'].tolist()
            print(f"    Participant {pid} has the following existing EmailCodes: {existing_email_codes}")
            # Check if any email templates are missing in the existing schedule
            for email_code, info in email_templates.items():                
                if email_code not in existing_email_codes:
                    if '-' in email_code:
                        suffix = email_code.split('-')[-1]
                        if (suffix == 'HA' and participant_arm != 'Healthy Arm') or \
                            (suffix == 'AA' and participant_arm != 'Alcohol Arm'):
                            print(f"      * Skipping email code {email_code} for participant {pid} in arm {participant_arm}.")
                            continue
                    # Add only if the email is not already scheduled
                    print(f"    EmailCode {email_code} is missing for Participant {pid}. Adding to schedule.")
                    scheduled_date = self.calculate_scheduled_date(pid, info['VisitNumber'], info['Offset'])
                    
                    # Check that scheduled_date is not None or invalid
                    if scheduled_date:
                        rows_to_add.append({
                            'ParticipantID': pid,
                            'EmailCode': email_code,
                            'ScheduledDate': scheduled_date,
                            'UpdatedAt': self.date_time_now,
                        })

        # If new rows are added, update the email schedule
        if rows_to_add:
            new_rows = pd.DataFrame(rows_to_add)
            self.df_es_l = pd.concat([self.df_es_l, new_rows], axis=0).reset_index(drop=True)
            if self.overwrite_local:
                self.df_es_l.to_csv(self.paths['email_schedule_local'], index=False)
                self.__reload_dfs()
            print("    * Updated existing participants' email schedules with new templates.")
        else:
            print("    * No new templates needed to be added to existing participants.")




    def calculate_scheduled_date(self, pid, visit_code, offset):
        if not visit_code == 'Signup':
            visit_date = self.df_vs_s.loc[self.df_vs_s['ParticipantID'] == pid, f"{visit_code}_Date"].values[0]
        else:
            # today
            visit_date = datetime.now().strftime('%Y-%m-%d')
        visit_date = datetime.strptime(visit_date, "%Y-%m-%d")       
        scheduled_date = visit_date + timedelta(days=offset)
        scheduled_date = scheduled_date.strftime("%Y-%m-%d")
        return scheduled_date
    
    # THESE ARE NEW AND NEED TO BE CHECKED

    def check_emails_to_send_today(self):
        print("# Checking for emails to be sent today.")
        today = datetime.now().strftime('%Y-%m-%d')
        emails_to_send = self.df_es_l[self.df_es_l['ScheduledDate'] == today]
        
        if emails_to_send.empty:
            print("    > No emails to be sent today.")
            return pd.DataFrame()
        
        print(f"    > Found {len(emails_to_send)} emails to send today.")
        # print the emails 
        for _, row in emails_to_send.iterrows():
            print(f"        Participant {row['ParticipantID']} scheduled to receive email {row['EmailCode']} today.")
        return emails_to_send

    
    def create_email_dict(self, emails_to_send_today):
        email_dict = {}
        for _, row in emails_to_send_today.iterrows():
            # check if participant is active
            self.__reload_dfs()
            if self.df_vs_l.loc[
                self.df_vs_l['ParticipantID'] == row['ParticipantID'], 'Active'].empty or \
                self.df_vs_l.loc[self.df_vs_l['ParticipantID'] == row['ParticipantID'], 'Active'].values[0] not in ['True', True]:
                print(f"        Participant {row['ParticipantID']} is not active. Skipping email.")
            # check if email was already sent
            elif not self.df_el_l.loc[(self.df_el_l['ParticipantID'] == row['ParticipantID']) & (self.df_el_l['EmailCode'] == row['EmailCode'])].empty:
                print(f"        Email {row['EmailCode']} for participant {row['ParticipantID']} was already sent. Skipping.")
            else:
                # Verify arm-specific emails
                participant_arm = self.df_vs_l.loc[self.df_vs_l['ParticipantID'] == row['ParticipantID'], 'Arm'].values[0]
                print(f"Participant {row['ParticipantID']} arm: {participant_arm}")
                if '-' in row['EmailCode']:
                    print(f"    Email {row['EmailCode']} is arm-specific.")
                    suffix = row['EmailCode'].split('-')[-1]
                    if (suffix == 'HA' and participant_arm != 'Healthy Arm') or \
                    (suffix == 'AA' and participant_arm != 'Alcohol Arm'):
                        print(f"        Email {row['EmailCode']} does not match participant {row['ParticipantID']}'s arm. Skipping.")
                        continue
                
                # Check if the participant already exists in the dictionary
                if row['ParticipantID'] not in email_dict:
                    email_dict[row['ParticipantID']] = {}
                
                # Add the email details to the participant's dictionary
                email_dict[row['ParticipantID']][row['EmailCode']] = { 
                    'ParticipantID': row['ParticipantID'],
                    'EmailCode': row['EmailCode'],
                    'ScheduledDate': row['ScheduledDate'],
                    'UpdatedAt': row['UpdatedAt'],
                    'Email': self.df_vs_l.loc[self.df_vs_l['ParticipantID'] == row['ParticipantID'], 'Email'].values[0],
                    'FirstName': self.df_vs_l.loc[self.df_vs_l['ParticipantID'] == row['ParticipantID'], 'FirstName'].values[0],
                    'LastName': self.df_vs_l.loc[self.df_vs_l['ParticipantID'] == row['ParticipantID'], 'LastName'].values[0],
                    'Subject': self.df_et_l.loc[self.df_et_l['EmailCode'] == row['EmailCode'], 'Subject'].values[0],
                    'EmailBody': self.df_et_l.loc[self.df_et_l['EmailCode'] == row['EmailCode'], 'EmailBody'].values[0],
                    'V1_Date': self.df_vs_l.loc[self.df_vs_l['ParticipantID'] == row['ParticipantID'], 'V1_Date'].values[0],
                    'V2_Date': self.df_vs_l.loc[self.df_vs_l['ParticipantID'] == row['ParticipantID'], 'V2_Date'].values[0],
                    'V3_Date': self.df_vs_l.loc[self.df_vs_l['ParticipantID'] == row['ParticipantID'], 'V3_Date'].values[0],
                    'V4_Date': self.df_vs_l.loc[self.df_vs_l['ParticipantID'] == row['ParticipantID'], 'V4_Date'].values[0],
                    'V5_Date': self.df_vs_l.loc[self.df_vs_l['ParticipantID'] == row['ParticipantID'], 'V5_Date'].values[0],
                    'V6_Date': self.df_vs_l.loc[self.df_vs_l['ParticipantID'] == row['ParticipantID'], 'V6_Date'].values[0],
                    'V7_Date': self.df_vs_l.loc[self.df_vs_l['ParticipantID'] == row['ParticipantID'], 'V7_Date'].values[0],
                    'V1_Time': self.df_vs_l.loc[self.df_vs_l['ParticipantID'] == row['ParticipantID'], 'V1_Time'].values[0],
                    'V2_Time': self.df_vs_l.loc[self.df_vs_l['ParticipantID'] == row['ParticipantID'], 'V2_Time'].values[0],
                    'V3_Time': self.df_vs_l.loc[self.df_vs_l['ParticipantID'] == row['ParticipantID'], 'V3_Time'].values[0],
                    'V4_Time': self.df_vs_l.loc[self.df_vs_l['ParticipantID'] == row['ParticipantID'], 'V4_Time'].values[0],
                    'V5_Time': self.df_vs_l.loc[self.df_vs_l['ParticipantID'] == row['ParticipantID'], 'V5_Time'].values[0],
                    'V6_Time': self.df_vs_l.loc[self.df_vs_l['ParticipantID'] == row['ParticipantID'], 'V6_Time'].values[0],
                    'V7_Time': self.df_vs_l.loc[self.df_vs_l['ParticipantID'] == row['ParticipantID'], 'V7_Time'].values[0],
                }

        return email_dict

    
    def check_attachments(self, email_code):

        # Find value of column Attachments in df_et_l
        attachment = self.df_et_l.loc[self.df_et_l['EmailCode'] == email_code, 'Attachments'].values[0]

        # Check if the attachment is not None, 'None', or an empty string
        if not pd.isna(attachment) and attachment not in ['False', False, 'None', 'none', 'NONE', '']:
            # Check if it's a list of attachments (comma-separated)
            if ',' in attachment:
                attachment = [a.strip() for a in attachment.split(',')]  # Split and strip whitespace
            else:
                attachment = [attachment.strip()]  # Convert single attachment to list
            # Prepend the path to each attachment
            attachment = [os.path.join(self.paths['attachments'], a) for a in attachment]
        else:
            attachment = None

        return attachment
    
    def check_calendar_event(self, email_code):
        cal_event = self.df_et_l.loc[self.df_et_l['EmailCode'] == email_code, 'CalendarEvent'].values[0]
        if cal_event in [0, '0']:
            cal_event = False
        else:
            cal_event = True
        
        return cal_event
    

    def format_calendar_event(self, email_data):
        # Find the corresponding visit number for the emal code
        visit_number = self.df_et_l.loc[self.df_et_l['EmailCode'] == email_data['EmailCode'], 'VisitNumber'].values[0]
        if visit_number != 'Signup':
            visit_number = visit_number[-1]  # Only keep the last character
        else: # If the email is a signup email, use the first visit
            visit_number = 0

        subject = f"UNITY Visit {visit_number} for {email_data['ParticipantID']}"
        description = f"UNITY Visit {visit_number} for {email_data['ParticipantID']}"
        
        # Combine date and time fields from email_data
        start_date_str = email_data[f'V{visit_number}_Date']
        start_time_str = email_data[f'V{visit_number}_Time']
        
        # Split the date and time strings into components
        year, month, day = map(int, start_date_str.split('-'))  # Split and convert to integers
        hour, minute = map(int, start_time_str.split(':'))  # Split and convert to integers

        # Create a datetime object using the parsed components
        start_time = datetime(year, month, day, hour, minute)
        # Add 3 hours for the end time
        end_time = start_time + timedelta(hours=3)

        location = 'UCL'

        # Generate the ICS attachment with formatted times
        cal_attachment = self.emailer.create_ics_attachment(subject, description, start_time, end_time, location)

        return cal_attachment



    def send_email(self, pid, email_data):

        email_code = email_data['EmailCode']
        subject = email_data['Subject'].format(**email_data)
        body = email_data['EmailBody']
        escaped_email_body = re.sub(r"{(?!\w)", "{{", body)
        escaped_email_body = re.sub(r"(?<=\W)}", "}}", escaped_email_body)
        formatted_email_body = escaped_email_body.format(**email_data)
        recipient = email_data['Email']
        attachment = self.check_attachments(email_code)
        calendar_event = self.check_calendar_event(email_code)
        if calendar_event:
            # add to attachment
            cal_attachment = self.format_calendar_event(email_data)
            if attachment:
                attachment.append(cal_attachment)
            else:
                attachment = [cal_attachment]
                              

        status = self.emailer.send_email_from_outlook(sender=self.paths['email_sender'],
                                            recepients=[recipient],
                                            subject=subject,
                                            email_body=formatted_email_body,
                                            attachments_paths=attachment,  # Add if necessary
                                            code=email_code)
        
        filtered_df = self.df_es_l.loc[
                        (self.df_es_l["ParticipantID"] == pid)
                        & (self.df_es_l["EmailCode"] == email_code),
                        "ScheduledDate",
                    ]

        scheduled_for = None
        if filtered_df.empty:
            raise ValueError(
                f"No matching records found for ParticipantID: {pid} and EmailCode: {email_code}"
            )
        else:
            scheduled_for = filtered_df.values[0]
        
        email_receipt = {
            'ParticipantID': pid,
            'EmailCode': email_code,
            'ScheduledFor': scheduled_for,
            'SentAt': self.date_time_now,
            'Status': status
        }
        time.sleep(2)
        return email_receipt
        
    
    def update_local_email_log(self, email_receipts):

        dfx = pd.DataFrame(email_receipts)
            
        # concat to df_local_el
        self.df_el_l = pd.concat([self.df_el_l, dfx], axis=0).reset_index(
            drop=True
        )
        # save to csv
        if self.overwrite_local:
            self.df_el_l.to_csv(self.paths['email_log_local'], index=False)
            for email_receipt in email_receipts:
                print(f"     * Updated local email log for participant: {email_receipt['ParticipantID']}: {email_receipt['EmailCode']}.")

    def remove_future_scheduled_emails(self, participant_id):
        """
        Remove future scheduled emails for the given participant ID.
        
        :param participant_id: The ID of the participant whose future emails should be removed.
        """
        # Get today's date
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Filter out rows where the participant ID matches and the scheduled date is in the future
        self.df_es_l = self.df_es_l[~((self.df_es_l['ParticipantID'] == participant_id) & (self.df_es_l['ScheduledDate'] > today))]
        
        # Optionally save changes back to the local file
        if self.overwrite_local:
            self.df_es_l.to_csv(self.paths['email_schedule_local'], index=False)
            print(f"     * Removed future scheduled emails for participant: {participant_id}")

    
    def main(self):
        print("REPORT TIME:", self.date_time_now)
        self.clear_old_backups()
        self.backup_local_csvs()
        changes = self.check_for_changes()
        if not self.missing_schedule_checked:
            self.check_missing_schedule()
        emails_to_send_today = self.check_emails_to_send_today()

        # # NEEDS TO BE CHECKED
        email_receipts = []
        if not emails_to_send_today.empty:
            email_dict = self.create_email_dict(emails_to_send_today)
            for pid, values in email_dict.items():
                for email_code, email_data in values.items():
                    email_receipt = self.send_email(pid, email_data)
                    email_receipts.append(email_receipt)
            if email_receipts:
                self.update_local_email_log(email_receipts)