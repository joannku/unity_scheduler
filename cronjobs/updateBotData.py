import sys
import os

# Add the parent directory (or any specific directory) to PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import requests
import json
from src.OneReach import OneReachRequests

class csvUtils:

    def __init__(self, creds):
        self.creds = creds

    def load_dfs(self, file_dict):
        dataframes = {}
        for key, filepath in file_dict.items():
            if filepath.endswith('.csv'):
                if key == 'emoodie_usernames':
                    dataframes[key] = pd.read_csv(filepath, dtype={'ParticipantID': str})
                else:
                    dataframes[key] = pd.read_csv(filepath)
        return dataframes

    def load_attachments(self, folder_path='attachments'):
        files = os.listdir(folder_path)
        return {os.path.splitext(file)[0]: os.path.join(folder_path, file) for file in files}
    
    def enumerate_dict_keys(self, some_dictionary):
        for i, key in enumerate(some_dictionary.keys(), start=1):
            print(f"{i}. {key}")

class UnityCSVHandler(csvUtils):

    def __init__(self, creds, *args, **kwargs):
        super().__init__(creds, *args, **kwargs)
    
    def update_bot_table(self,df1,df5):

        new_bot_signups = df1[~df1['ParticipantID'].isin(df5['UserID'])].set_index('ParticipantID').to_dict(orient='index')
        new_bot_signups = {k: {k1: v1 for k1, v1 in v.items() if k1 in ['V1_Date', 'V2_Date', 'V3_Date']} for k, v in new_bot_signups.items()}
        new_bot_signups = {k: {k1[:2]: v1 for k1, v1 in v.items()} for k, v in new_bot_signups.items()}
        for user, data in new_bot_signups.items():
            data['TelegramID'] = 0

        
        if not new_bot_signups:
            print("No new signups to update in bot table.")
        else: 
            print("New users to update:")
            print(new_bot_signups)
            new_bot_signups_df = pd.DataFrame.from_dict(new_bot_signups, orient='index')
            new_bot_signups_df.index.name = 'UserID'
            new_bot_signups_df.reset_index(inplace=True)
            df5 = pd.concat([df5, new_bot_signups_df], ignore_index=True)
            df5.to_csv('data/local/5_bot_users.csv', index=False)
            print("Completed updating local csv file.")

        return df5

    def correct_changed_dates(self, df1, df5):
        # Convert df to dict with Participant ID as key
        df1_dict = df1.set_index('ParticipantID').T.to_dict('dict')

        # Define the columns to check
        columns_to_check = ['V1', 'V2', 'V3']

        for user, data in df1_dict.items():
            # Check if the user exists in df5
            if user not in df5['UserID'].values:
                print(f"User {user} not found in df5")
            else:
                for col in columns_to_check:
                    # Find the corresponding date column in df1_dict (e.g., 'V1_Date' for 'V1')
                    data_key = f"{col}_Date"

                    # Retrieve the value from df5 for comparison
                    df5_value = df5.loc[df5['UserID'] == user, col].values[0]

                    # Compare and update if necessary
                    if df5_value != data[data_key]:
                        print(f"{col} dates don't match for {user}")
                        df5.loc[df5['UserID'] == user, col] = data[data_key]
                        print(f"Updated {col} for {user}.")

        df5.to_csv('data/local/5_bot_users.csv', index=False)
        return df5


if __name__ == "__main__":

    creds = 'admin/creds.json'
    ucsv = UnityCSVHandler(creds)
    onereach = OneReachRequests(creds_path=creds)\
    
    # Pull all data
    onereach.pull_all_data(path='/data/jkuc/unity_scheduler/data/bot')

    # # Update the local table
    df5path = 'data/local/5_bot_users.csv'

    df1 = pd.read_csv('/data/jkuc/unity_scheduler/data/local/1_visit_schedule.csv')
    df5 = pd.read_csv(df5path)
    df5 = ucsv.update_bot_table(df1, df5)
    df5 = ucsv.correct_changed_dates(df1, df5)

    # # Pull latest Telegram IDs
    onereach.update_telegram_ids(df5)

    # # Reload dfs, and upload to OneReach
    df5 = pd.read_csv(df5path)
    user_ids_new = onereach.upload_new_rows(df5)
    user_ids_changed = onereach.delete_changed_rows(df5)

    df5 = pd.read_csv(df5path)
    records_updated = onereach.upload_new_rows(df5)
    onereach.trigger_recalculation(user_ids_changed)