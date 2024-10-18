import requests
import pandas as pd
import json
import os
from datetime import datetime

# TODO: ADD BOT DATA PULLING

class OneReachRequests:
    def __init__(self, creds_path, headers={}, pagesize=200):

        with open(creds_path) as file:
            creds = json.load(file)

        self.sql_url = creds["onereach_unity_sqlurl"]
        self.upload_url = creds["onereach_tableupload"]
        self.remove_url = creds["onereach_tableremove"]
        self.recalculate_url = creds["onereach_recalculate"]
        self.pagesize = pagesize
        self.headers = {"auth": creds["authSQL"]}
        self.output_csv = "data/local/7_botstatus.csv"

        self.table_list = [
            'unity_alcohol',
            'unity_analysis',
            'unity_botmessage',
            'unity_entries_for_summaries',
            'unity_gptprompt',
            'unity_gptsummaries',
            'unity_iss_answers',
            'unity_iss_entries',
            'unity_iss_messages',
            'unity_journals_saved',
            'unity_moodanswers',
            'unity_moodquestions',
            'unity_mooduseranswers',
            'unity_notifications',
            'unity_timezonecheck',
            'unity_usernames',
            'unity_usertable',
            'unity_visitschedule',
            'unity_voice_analytics',
            'unitybot_usernames'
            ]

    def sql_query(self, tablename):
        data = {"query": f"SELECT COUNT(*) FROM {tablename}"}
        print(data)
        response = requests.post(self.sql_url, json=data, headers=self.headers)

        if response.status_code != 200:
            print(f"Error when counting rows. Status code: {response.status_code}. Message: {response.text}")

        total_rows = response.json()[0]['COUNT(*)']
        print(f"Total rows: {total_rows}")
        total_pages = (total_rows + self.pagesize - 1) // self.pagesize
        print(f"Total pages: {total_pages}")

        if total_rows == 0:
            print(f"No data in table {tablename}, skipping...")
            return pd.DataFrame()
        
        if total_rows < 200: 
            data = {
                    "query": f"SELECT * FROM {tablename}"
                }
            response = requests.post(self.sql_url, json=data, headers=self.headers)
            response_data = response.json()
            df = pd.DataFrame(response_data)
            return df

        else:

            # Create an empty list to store all the dataframes
            dfs = []

            # Fetch journal data page by page
            for page_number in range(total_pages):
                data = {
                    "query": f"SELECT * FROM {tablename} LIMIT {self.pagesize} OFFSET {page_number * self.pagesize}"
                }
                response = requests.post(self.sql_url, json=data, headers=self.headers)

                if response.status_code != 200:
                    print(f"Error on page {page_number}. Status code: {response.status_code}. Message: {response.text}")
                    continue

                response_data = response.json()
                dfx = pd.DataFrame(response_data)
                dfs.append(dfx)

                # Verify counts after each page
                print(f"After processing page {page_number+1}, total rows retrieved: {sum(len(df) for df in dfs)}")

            # Concatenate all dataframes
            complete_df = pd.concat(dfs, ignore_index=True)

            # Verify total rows
            print(f"Expected rows based on COUNT: {total_rows}")
            print(f"Actual rows retrieved: {len(complete_df)}")

            return complete_df
    
    def find_new_rows(self, df, tablename='unity_visitschedule'):
        """ 
        Determine which rows in df are not present in the onereach table specified by tablename.
        Default table is unity_visitschedule but can be changed to any other table. 
        Converts the identified rows to a list of dictionaries, each representing a record. 
        """

        df.reset_index(inplace=True, drop=True)
        df_onereach = self.sql_query("unity_visitschedule")
        df_onereach.reset_index(inplace=True, drop=True)

        # Check if 'UserID' column exists in both dataframes
        if 'UserID' not in df.columns:
            # print path of the dataframe 
            raise ValueError("The DataFrame does not have a 'UserID' column.")
        if 'UserID' not in df_onereach.columns:
            raise ValueError(f"The DataFrame for table '{tablename}' does not have a 'UserID' column.")


        # Check if there are any UserIDs present in df_bot_users that are not present in df_onereach
        dfx = df[~df['UserID'].isin(df_onereach['UserID'])]
        # print values of UserID selected from df_bot_users that are not present in df_onereach
        if dfx.empty:
            return False

        else:
            print(dfx['UserID'].values)

            # create a dictionary of new users where UserID is key and the rest of the row is the value
            new_users = {}
            for index, row in dfx.iterrows():
                if row['UserID'] not in df_onereach['UserID']:
                    new_users[row['UserID']] = row

            # Assuming new_users is a dictionary where the key is UserID and the value is the rest of the row
            # Convert new_users to a list of dictionaries, each representing a record

            records_to_add = []
            for user_id, user_data in new_users.items():
                record = {'UserID': user_id}
                for field, value in user_data.items():
                    # Assuming user_data is a Series or a dictionary-like object
                    record[field] = value
                records_to_add.append(record)

            # print each record to be added in a new line
            if records_to_add:
                print("Records to add:")
                for record in records_to_add:
                    print(record)

        return records_to_add

    def upload_new_rows(self, df, tablename='unity_visitschedule'):

        """
        First calls the find_new_rows function to determine which rows in df are not present in the onereach table specified by tablename.
        Takes the list of records and makes a HTTP POST request to upload them to OneReach server.
        """

        # print path
        path = os.path.join(os.getcwd(), 'data', 'unity_visitschedule.csv')
        records_to_add = self.find_new_rows(df,tablename)
        if records_to_add:
            response = requests.post(self.upload_url, json={'tablename': 'unity_visitschedule', 'content': records_to_add}, headers=self.headers)
            response_data = response.json()
            print(response_data)

            return records_to_add

        else: 
            print("No new records to add.")


    def delete_changed_rows(self, df_local, remote_tablename='unity_visitschedule'):
        
        
        df_remote = self.sql_query(remote_tablename).reindex(columns=df_local.columns)
        df_local.set_index("UserID", inplace=True)
        df_remote.set_index("UserID", inplace=True)
        df_local.sort_index(inplace=True)
        df_remote.sort_index(inplace=True)

        visit_list = ['V1','V2', 'V3']
        # Filter both DataFrames to include only the specified columns
        dfbf = df_local[visit_list]
        dfrf = df_remote[visit_list]

        # Compare the filtered DataFrames
        differences = dfbf.compare(dfrf)
        # Save UserID values to a list
        user_ids = differences.index.tolist()

        print(f"User IDs with differences: {user_ids}")

        headers = {}

        for user_id in user_ids:
            print(f"Processing for: {user_id}")
            response = requests.post(self.remove_url, json={'tablename': 'unity_visitschedule', 'content': user_id}, headers=headers)
            response_data = response.json()
            print(response_data)
        
        return user_ids
    
    def trigger_recalculation(self, user_ids):
        """ 
        Triggers a remote flow to recalculate the the DayCounter after changes to visit dates,
        and uploads new value to onereach server table.
        """
        if user_ids:
            for user in user_ids: 
                print(f"Processing for: {user}")
                response = requests.post(self.recalculate_url , json={'tablename': 'unity_visitschedule', 'content': user}, headers={})
                response_data = response.json()
                print(response_data)
        else:
            print("No users to recalculate days for.")


    def update_telegram_ids(self, df_local, tablename='unity_usertable'):
        df = self.sql_query(tablename)
        # Convert to dict with value of ParticipantID as key and column names as subkeys
        df_dict = df.set_index('ParticipantID').T.to_dict('dict')
        # Iterate over every row of dfx
        dfx = pd.read_csv('data/local/5_bot_users.csv')
        for index, row in df_local.iterrows():
            userid = row['UserID']
            if userid in df_dict:
                if str(row['TelegramID']) != str(df_dict[userid]['TelegramID']):
                    print(f"TelegramID for {row['UserID']} has changed from {row['TelegramID']} to {df_dict[row['UserID']]['TelegramID']}")
                    # Update the TelegramID in dfx
                    df_local.at[index, 'TelegramID'] = df_dict[userid]['TelegramID']

        # Write the updated dfx to a csv
        df_local.to_csv('data/local/5_bot_users.csv', index=False)

    
    def pull_all_data(self, path='/data/jkuc/unity_scheduler/data/bot'):


        for table_name in self.table_list:
            
            dfs = {}
            
            dfs[table_name] = self.sql_query(table_name)
            # if df has more than 0 rows
            if len(dfs[table_name]) > 0:
                dfs[table_name].to_csv(f"{path}/{table_name}.csv", index=False)

        # Write date to txt file
        with open(f"{path}/info.txt", "w") as file:
            file.write(f"Data pulled from OneReach on {datetime.now()}.")

        print("All tables saved to CSV files.")


if __name__ == "__main__":
    
    creds_path = '/data/jkuc/unity/creds.json'
    onereach = OneReachRequests(creds_path=creds_path)
    onereach.pull_all_data(path='/data/jkuc/unity_scheduler/data/bot')