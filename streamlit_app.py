import streamlit as st
import json
import datetime
from dateutil.relativedelta import relativedelta
import pandas as pd
import os
import subprocess
from streamlit_calendar import calendar
import numpy as np


# Initialize session state
if 'form_stage' not in st.session_state:
    st.session_state['form_stage'] = 1

# Function to load configuration
def load_config(config):
    with open(config, 'r') as file:
        return json.load(file)

# Function to load passcodes
def load_passcodes(passcodes):
    with open(passcodes, 'r') as file:
        return json.load(file)

# Function to move to the next form
def next_form():
    st.session_state['form_stage'] += 1

# Display the homepage with passcode validation
def homepage(passcodes):
    st.image(
        "https://images.squarespace-cdn.com/content/v1/6192f109da8fd57373625bc7/d3657d1b-7b0f-4f67-80c1-dc0c81b1f4ab/LOGO111111.png?format=1500w", 
        width=300, output_format="PNG"
    )
    st.caption("VERSION 2.0 Released 11/10/2024")
    st.title("UNITy Experimenter Dashboard")
    valid_passcodes = list(passcodes.values())

    with st.form("Login"):
        st.session_state['Passcode'] = st.text_input("Please enter your Experimenter Passcode to proceed:", type='password')
        if st.form_submit_button("Submit"):
            if st.session_state['Passcode'] not in valid_passcodes:
                st.error("Wrong passcode.")
            else:
                st.session_state['LoginComplete'] = True
                next_form()

# Display the main menu to select tasks
def main_menu():
    choices = [
        "Register new participant",
        "Edit email templates",
        "Participant lookup",
        "View or edit CSVs",
        "View scheduled emails"
    ]
    with st.form("SelectTask"):
        st.session_state["Task"] = st.radio("What would you like to do today?", choices)
        if st.form_submit_button("Submit"):
            st.session_state['TaskComplete'] = True
            next_form()

# Register new participant form
def register_participant(config):

    with st.form("Register"):
        st.write("Please fill in the following information for the new participant:")
        
        # Initialize the participant dictionary
        participant_dict = {}

        # Participant Information
        participant_dict["ParticipantID"] = st.text_input("Participant ID")
        participant_dict["Active"] = st.selectbox("Active", ['True', 'False'])
        participant_dict["FirstName"] = st.text_input("First Name")
        participant_dict["LastName"] = st.text_input("Last Name")
        participant_dict["Email"] = st.text_input("Email")
        participant_dict["Number"] = st.text_input("Number")
        participant_dict["Gender"] = st.selectbox("Gender", config['gender'])
        participant_dict["Arm"] = st.selectbox("Arm", config['arm'])
        participant_dict["DrinkPreference"] = st.selectbox("Drink Preference", config['drink_preference'])
        participant_dict["MemoryReconsolidation"] = st.selectbox("Memory Reconsolidation Condition", config['memory_reconsolidation'])
        participant_dict["Researcher1"] = st.selectbox("Researcher 1", config['experimenters'])
        participant_dict["Researcher2"] = st.selectbox("Researcher 2", config['experimenters'])
        participant_dict["Glasses"] = st.text_input("If the participant wears glasses, please enter their prescription (optional)")
        participant_dict["Visit1_movie"] = st.selectbox("Visit 1 Movie", config['movies'])
        participant_dict["Visit3_movie"] = st.selectbox("Visit 3 Movie", config['movies'])
        participant_dict["Visit1_fmrioperator"] = st.selectbox("Visit 1 fMRI operator", config['fmri_operators'])
        participant_dict["Visit2_operator"] = st.selectbox("Visit 2 Operator (if applicable)", config['fmri_operators'])
        participant_dict["Visit3_fmrioperator"] = st.selectbox("Visit 3 fMRI operator", config['fmri_operators'])
        participant_dict["Medic"] = st.selectbox("Medic", config['medics'])

                
        # Core visit dates
        st.write("Core visit dates:")
        participant_dict["V1_Date"] = st.date_input("Visit 1 Date")
        participant_dict["V1_Time"] = st.time_input("Visit 1 Time", datetime.time(12,0)).strftime("%H:%M")
        participant_dict["V2_Date"] = st.date_input("Visit 2 Date")
        participant_dict["V2_Time"] = st.time_input("Visit 2 Time", datetime.time(12,0)).strftime("%H:%M")
        participant_dict["V3_Date"] = st.date_input("Visit 3 Date")
        participant_dict["V3_Time"] = st.time_input("Visit 3 Time", datetime.time(12,0)).strftime("%H:%M")
        
        # Follow-up visit dates
        st.write("Follow-up visit dates:")
        st.session_state['follow_up_selection'] = st.radio(
            "How would you like to schedule follow-up visits?",
            ["Use automatic scheduling based on V2 date", "Manually schedule follow-up visits"]
        )
        st.caption("You can manually edit the follow-up dates later, and the email schedule will be regenerated.")

        if st.form_submit_button("Submit"):
            result = check_for_errors(participant_dict, config)
            if result:
                st.session_state['participant_dict'] = participant_dict
                st.session_state['CoreVisitComplete'] = True
                next_form()

def check_for_errors(participant_dict, config):

    df = pd.read_csv("data/local/1_visit_schedule.csv")

    input_fields = {
        "ParticipantID": "Participant ID",
        "FirstName": "First Name",
        "LastName": "Last Name",
        "Email": "Email",
        "Number": "Number"
    }

    select_fields = {
        "Gender": config['gender'],
        "Arm": config['arm'],
        "DrinkPreference": config['drink_preference'],
        "MemoryReconsolidation": config['memory_reconsolidation'],
        "Researcher1": config['experimenters'],
        "Researcher2": config['experimenters'],
        "Visit1_movie": config['movies'],
        "Visit1_fmrioperator": config['fmri_operators'],
        "Medic": config['medics'],
        "Visit3_movie": config['movies'],
        "Visit3_fmrioperator": config['fmri_operators']
    }

    # Check for errors in the participant dictionary
    errors_found = False

    # check if the participant ID already exists
    if participant_dict["ParticipantID"] in df["ParticipantID"].values:
        st.error("!! Participant ID already exists.")
        errors_found = True
    
    # Check text inputs
    for var, name in input_fields.items():
        if var not in participant_dict or participant_dict[var].strip() == "":
            st.error(f"Please enter {name}.")
            errors_found = True

    # Check select box inputs
    for var, options in select_fields.items():
        if var not in participant_dict or participant_dict[var] == options[0]:  # Assuming the first option is a default/empty choice
            st.error(f"Please select a value for {var.replace('_', ' ')}.")
            errors_found = True

    # Check that Researcher1 and Researcher2 are not the same
    if participant_dict["Researcher1"] == participant_dict["Researcher2"]:
        st.error("Researcher 1 must be different from Researcher 2.")
        errors_found = True

    # Check the order of visit dates
    visit1_date = participant_dict["V1_Date"]
    visit2_date = participant_dict["V2_Date"]
    visit3_date = participant_dict["V3_Date"]

    if not (visit1_date < visit2_date < visit3_date):
        st.error("Visits must be scheduled in the correct order (Visit 1 < Visit 2 < Visit 3).")
        errors_found = True

    # Warn if any visit is scheduled in the past
    today = datetime.date.today()
    visits = [visit1_date, visit2_date, visit3_date]
    for i, visit in enumerate(visits):
        if visit < today:
            st.warning(f"Visit {i + 1} is scheduled for {visit}, which is in the past.")
    
    return not errors_found

   

# Generate sample follow-up visits
def generate_sample_follow_ups(V2_Date, V2_Time):
    V4_Date = V2_Date + relativedelta(months=+1)
    V4_Time = V2_Time
    V5_Date = V2_Date + relativedelta(months=+3)
    V5_Time = V2_Time
    V6_Date = V2_Date + relativedelta(months=+6)
    V6_Time = V2_Time
    V7_Date = V2_Date + relativedelta(months=+9)
    V7_Time = V2_Time
    return {
        "V4_Date": V4_Date, "V4_Time": V4_Time,
        "V5_Date": V5_Date, "V5_Time": V5_Time,
        "V6_Date": V6_Date, "V6_Time": V6_Time,
        "V7_Date": V7_Date, "V7_Time": V7_Time
    }

# Follow-up visit scheduling
def follow_up_visits():
    st.write("YEAH! Core visit dates have been successfully set. Now let's schedule the follow-up visits.")
    
    with st.form("Select follow-up visit dates"):
        st.subheader("Follow-up visit dates")
        
        # Check that 'follow_up_selection' is properly set
        if 'follow_up_selection' not in st.session_state:
            st.error("Follow-up selection is not set.")
            return

        if st.session_state['follow_up_selection'] == "Use automatic scheduling based on V2 date":
            follow_up_dates = generate_sample_follow_ups(
                st.session_state['participant_dict']["V2_Date"],
                st.session_state['participant_dict']["V2_Time"]
            )

            

            st.write(f"Automatically generated follow-up visit dates for participant {st.session_state['participant_dict']['ParticipantID']}:")
            st.caption("Remember: You can edit the follow-up dates later, and the email schedule will be regenerated.")
            st.write(f"* V4 Date: {follow_up_dates['V4_Date']}, V4 Time: {follow_up_dates['V4_Time']}")
            st.write(f"* V5 Date: {follow_up_dates['V5_Date']}, V5 Time: {follow_up_dates['V5_Time']}")
            st.write(f"* V6 Date: {follow_up_dates['V6_Date']}, V6 Time: {follow_up_dates['V6_Time']}")
            st.write(f"* V7 Date: {follow_up_dates['V7_Date']}, V7 Time: {follow_up_dates['V7_Time']}")

    

        else:

            V4_Date = st.date_input("Visit 4 Date")
            V4_Time = st.time_input("Visit 4 Time", datetime.time(12,0)).strftime("%H:%M")
            V5_Date = st.date_input("Visit 5 Date")
            V5_Time = st.time_input("Visit 5 Time", datetime.time(12,0)).strftime("%H:%M")
            V6_Date = st.date_input("Visit 6 Date")
            V6_Time = st.time_input("Visit 6 Time", datetime.time(12,0)).strftime("%H:%M")
            V7_Date = st.date_input("Visit 7 Date")
            V7_Time = st.time_input("Visit 7 Time", datetime.time(12,0)).strftime("%H:%M")

            follow_up_dates = {
                "V4_Date": V4_Date, "V4_Time": V4_Time,
                "V5_Date": V5_Date, "V5_Time": V5_Time,
                "V6_Date": V6_Date, "V6_Time": V6_Time,
                "V7_Date": V7_Date, "V7_Time": V7_Time
            }

        if st.form_submit_button("Submit"):
            st.session_state['participant_dict'].update(follow_up_dates)
            check_follow_up_dates(st.session_state['participant_dict'])
            st.session_state['FollowUpVisits'] = True
            st.write("Follow-up visit dates have been successfully set.")
            next_form()

def check_follow_up_dates(participant_dict):
    errors_found = False

    # Check that follow-up visits are scheduled in the correct order
    visit4_date = participant_dict["V4_Date"]
    visit5_date = participant_dict["V5_Date"]
    visit6_date = participant_dict["V6_Date"]
    visit7_date = participant_dict["V7_Date"]

    if not (visit4_date < visit5_date < visit6_date < visit7_date):
        st.error("Follow-up visits must be scheduled in the correct order (V4 < V5 < V6 < V7).")
        errors_found = True

    # Warn if any follow-up visit is scheduled in the past
    today = datetime.date.today()
    visits = [visit4_date, visit5_date, visit6_date, visit7_date]
    for i, visit in enumerate(visits):
        if visit < today:
            st.warning(f"Follow-up visit {i + 4} is scheduled for {visit}, which is in the past.")
            errors_found = True

    return not errors_found

def add_participant_to_csv(participant_dict):

    try:
        dfx = pd.DataFrame(participant_dict, index=[0])
        dfx.to_csv('data/streamlit/1_visit_schedule.csv', mode='a', header=False, index=False)
        st.success("Participant information has been successfully added to the CSV file.")
    except Exception as e:
        st.error("An error occurred while writing to the CSV file.")
        st.error(e)


def run_daily_email_scheduler():
    st.write("Running the email scheduler script. Please give it a moment...")
    try:
        # Run the Python script using the specified command
        command = "PYTHONPATH=/data/jkuc/unity_scheduler /data/jkuc/unity_scheduler/.venv/bin/python /data/jkuc/unity_scheduler/cronjobs/dailyEmailScheduler.py"
        result = subprocess.run(
            command,
            shell=True,  # Use shell=True to allow the full command with environment variables
            capture_output=True,
            text=True,
            check=True
        )

        # Display the standard output (stdout) from the script
        st.write("Script Output:")
        st.write(result.stdout)

        st.write("Syncing bot... Please give it a few minutes and don't close the browser until you see the success message.")
        command = "PYTHONPATH=/data/jkuc/unity_scheduler /data/jkuc/unity_scheduler/.venv/bin/python /data/jkuc/unity_scheduler/cronjobs/updateBotData.py"

        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            check=True
        )

        st.write("Bot Sync Output:")
        st.write(result.stdout)

        st.success("ALL DONE! The email scheduler has been successfully run and the bot has been synced.")

    except subprocess.CalledProcessError as e:
        # If the script returns an error, display it to the user
        st.error("An error occurred while running the script.")
        st.error(e.stderr)



def preview_participant_information():
    with st.form("RegisterToCSV"):
        st.write("Now let's have a look at the participant information you've entered.")
        st.write("Please review the information below and click 'Submit' to save the participant information to a CSV file.")

        st.write("Participant information:")
        st.table(st.session_state['participant_dict'])
        check = st.checkbox("Please select this box to automatically generate new email schedule.")
        st.caption("Note: If you don't do it, it will happen at the next scheduled hour (10/15/21 daily).")
        if st.form_submit_button("Submit"):
            participant_dict = st.session_state['participant_dict']
            add_participant_to_csv(participant_dict)
            if check:
                run_daily_email_scheduler()

            st.session_state['form_stage'] += 1

def check_function():
    check = st.checkbox("Please select this box to automatically generate new email schedule.")
    st.caption("Note: If you don't do it, it will happen at the next scheduled hour (10/15/21 daily).")

def edit_email_templates():
    st.write("This is the email template editor.")

    # Load the CSV into session state if it's not already there
    if 'templates' not in st.session_state:
        st.session_state['templates'] = pd.read_csv('data/streamlit/3_email_templates.csv')

    # Display the data editor
    dfx = st.data_editor(st.session_state['templates'], width=1000, hide_index=True)

    # Add a new row when the button is clicked
    add_row = st.button("Add new row")
    st.write("Note: Empty rows will not be added to the CSV file.")
    if add_row:
        # Add an empty row to the dataframe and update the session state
        empty_row = pd.DataFrame(columns=st.session_state['templates'].columns, index=[len(st.session_state['templates'])])
        st.session_state['templates'] = pd.concat([dfx, empty_row], ignore_index=True)
        
        # Refresh the editor display by re-rendering it
        st.rerun()

    # Show a button to view the edited version
    view_button = st.button("View edited version")
    if view_button:
        # Set a session state variable to indicate the edited version should be displayed
        st.session_state['view_mode'] = True

    # If the view mode is enabled, show the edited version and save button
    if st.session_state.get('view_mode', False):
        # remove all empty rows
        st.session_state['templates'] = dfx.dropna(how='all')
        st.dataframe(st.session_state['templates'])
        st.write("Looking good? Click 'Save changes' to save the edited version.")
        check = st.checkbox("Please select this box to automatically generate new email schedule.")
        st.caption("Note: If you don't do it, it will happen at the next scheduled hour (10/15/21 daily).")
        st.session_state['view_mode'] = True
        if st.session_state['view_mode']:
            save_changes = st.button("Save changes")
        try:
            if save_changes:
                if st.session_state['view_mode'] == False:
                    st.error("The changes have already been saved. Please refresh the page to make new changes.")
                else: 
                    # hide the button
                    st.session_state['view_mode'] = False
                    st.session_state['templates'].to_csv('data/streamlit/3_email_templates.csv', index=False)
                    st.success("Changes have been saved successfully.")
                    # Reset the view mode after saving
                    st.session_state['view_mode'] = False
                if check:
                    run_daily_email_scheduler()
        except Exception as e:
            st.error("An error occurred while saving changes.")
            st.error(e)

def participant_lookup():

    df = pd.read_csv('data/streamlit/1_visit_schedule.csv')

    participants = df['ParticipantID'].tolist()
    phone_numbers = df['Number'].tolist()
    emails = df['Email'].tolist()

    lookup = st.selectbox("Select how you want to look up participant", ['',
                                                                        'ParticipantID',
                                                                        'Phone number',
                                                                        'Email'])
    if lookup == 'ParticipantID':
        criteria = st.selectbox('Participant ID',participants)
    
    elif lookup == 'Phone number':
        lookup = "Number"
        criteria = st.selectbox('Phone number',phone_numbers)

    elif lookup == 'Email':
        criteria = st.selectbox('Email',emails)

    if st.button("Search"):
        st.session_state['LookUp'] = True
        participant_id = df[df[lookup] == criteria]['ParticipantID'].iloc[0]
        st.subheader(f"Participant information for {participant_id}")    
        st.dataframe((df[df[lookup] == criteria].T.rename(columns={0: 'Data'})), 
                    width=1000, height=910)


def view_or_edit_csvs():
    st.write("<i>This is the CSV viewer and editor.</i>", unsafe_allow_html=True)
    st.write("Please select a folder /and subfolder to view or edit the CSV files within it.")
    st.write("NOTE: If you want to edit participant data or visit schedules: \n\n<b>please edit the file in data/streamlit/1_visit_schedule.csv</b>", unsafe_allow_html=True)

    # List all top-level folders
    folders = sorted([d for d in os.listdir() if os.path.isdir(d) and not d.startswith('.') and not d.startswith('__')])
    subdirectory = st.radio("Folders", folders)

    # List subfolders within the selected top-level folder
    subfolders = sorted([d for d in os.listdir(subdirectory) if os.path.isdir(os.path.join(subdirectory, d))])
    
    selected_subfolder = None
    selected_sub_subfolder = None

    # If there are subfolders, allow the user to select one
    if subfolders:
        selected_subfolder = st.radio("Subfolders", subfolders)

    # If a subfolder is selected, check for sub-subfolders within it
    if selected_subfolder:
        sub_subfolders = sorted([d for d in os.listdir(os.path.join(subdirectory, selected_subfolder)) 
                                 if os.path.isdir(os.path.join(subdirectory, selected_subfolder, d))])
        
        if sub_subfolders:
            selected_sub_subfolder = st.radio("Sub-Subfolders", sub_subfolders)

    # Update file_list based on the selected folder level
    if selected_sub_subfolder:
        # If a sub-subfolder is selected, list files from that path
        file_list = os.listdir(os.path.join(subdirectory, selected_subfolder, selected_sub_subfolder))
    elif selected_subfolder:
        # If only a subfolder is selected, list files from that path
        file_list = os.listdir(os.path.join(subdirectory, selected_subfolder))
    else:
        # If no subfolder is selected, list files from the top-level directory
        file_list = os.listdir(subdirectory)

    # Filter and display only CSV files
    csv_files = sorted([f for f in file_list if f.endswith('.csv')])
    if csv_files:
        df_path = st.selectbox("Select file:", csv_files)
        st.write(f"Selected file path: {os.path.join(subdirectory, selected_subfolder or '', selected_sub_subfolder or '', df_path)}")
    else:
        st.write("No CSV files found.")

    # Maintain the state of the "View CSV" button using session state
    if "view_csv" not in st.session_state:
        st.session_state["view_csv"] = False

    button = st.button("View CSV")
    if button:
        st.session_state["view_csv"] = True  # Set to True when the button is clicked
        st.write("Note: Empty rows will not be added to the CSV file.")
    # Only show this section if the "View CSV" button was clicked
    if st.session_state["view_csv"]:
        if csv_files:
            df = pd.read_csv(os.path.join(subdirectory, selected_subfolder or '', selected_sub_subfolder or '', df_path))
            st.data_editor(df)

            # Prompt to enter password to save changes
            passcode = st.text_input("Please enter your Experimenter Passcode to continue:", type='password')
            # Run additional function if needed
            check = check_function()
            save_changes = st.button("Save changes")
            if save_changes:
                if passcode == st.session_state.get('Passcode'):
                    # Save changes
                    df.to_csv(os.path.join(subdirectory, selected_subfolder or '', selected_sub_subfolder or '', df_path), index=False)
                    st.success("Changes saved successfully.")
                    if check:
                        run_daily_email_scheduler()
                else: 
                    st.error("Incorrect passcode. Please try again.")

def view_scheduled_emails():
    df = pd.read_csv('/data/jkuc/unity_scheduler/data/local/2_email_schedule.csv')
    dfx = pd.read_csv('/data/jkuc/unity_scheduler/data/local/3_email_templates.csv')
    dfv = pd.read_csv('/data/jkuc/unity_scheduler/data/local/1_visit_schedule.csv')
    
    participants = np.append(["Select all"], df['ParticipantID'].unique())
    participant_id = st.selectbox('Participant ID', participants)
    codes = np.append(['Select all'], df['EmailCode'].unique())
    email_code = st.selectbox('Email Code', codes)

    # Use session state to retain calendar events
    if 'calendar_events' not in st.session_state:
        st.session_state['calendar_events'] = []
    if 'calendar_generated' not in st.session_state:
        st.session_state['calendar_generated'] = False

    search_button = st.button("Search")
    if search_button:
        st.write(f"Showing scheduled emails for Participant ID: {participant_id} and Email Code: {email_code}")
        if participant_id == "Select all" and email_code == "Select all":
            df_filtered = df
            dfv_f = dfv
        elif participant_id == "Select all" and email_code != "Select all":
            df_filtered = (df[df['EmailCode'] == email_code])
            dfv_f = dfv
        elif participant_id != "Select all" and email_code == "Select all":
            df_filtered = (df[df['ParticipantID'] == participant_id])
            dfv_f = dfv[dfv['ParticipantID'] == participant_id]
        else:
            df_filtered = (df[(df['ParticipantID'] == participant_id) & (df['EmailCode'] == email_code)])
            dfv_f = dfv[dfv['ParticipantID'] == participant_id]

        st.dataframe(df_filtered, width=2000)

        # Generate calendar events
        calendar_options = {}    
        calendar_events = []

        # ParticipantID, EmailCode, ScheduledDate, UpdatedAt
        for index, row in df_filtered.iterrows():
            email_description = dfx[dfx['EmailCode'] == row['EmailCode']]['Description'].iloc[0]
            calendar_event = {
                "title": f"{row['EmailCode']}: {row['ParticipantID']}",
                "start": row['ScheduledDate'],
                "resourceId": {"id": row['ParticipantID'], "email_code": row['EmailCode'], "description": email_description},
                "backgroundColor": "blue",
            }
            calendar_events.append(calendar_event)
        
        # Add visit schedule events
        visit_dict = {}
        for index, row in dfv_f.iterrows():
            visit_dict[row['ParticipantID']] = {
                "V1": {"date": row['V1_Date'], "time": row['V1_Time']},
                "V2": {"date": row['V2_Date'], "time": row['V2_Time']},
                "V3": {"date": row['V3_Date'], "time": row['V3_Time']},
                "V4": {"date": row['V4_Date'], "time": row['V4_Time']},
                "V5": {"date": row['V5_Date'], "time": row['V5_Time']},
                "V6": {"date": row['V6_Date'], "time": row['V6_Time']},
                "V7": {"date": row['V7_Date'], "time": row['V7_Time']},
            }
        
        for pid, visit_data in visit_dict.items():
            for visit, date_time in visit_data.items():
                calendar_event = {
                    "title": f"{visit}: {pid}",
                    "start": f"{date_time['date']}T{date_time['time']}",
                    "backgroundColor": "red",
                }
                calendar_events.append(calendar_event)

        # Store events in session state
        st.session_state['calendar_events'] = calendar_events
        st.session_state['calendar_options'] = calendar_options
        st.session_state['custom_css'] = """
            .fc-event-past {
                opacity: 0.5;
            }
            .fc-event-time {
                font-style: italic;
            }
            .fc-event-title {
                font-weight: 200; font-size: 0.7rem;
            }
            .fc-toolbar-title {
                font-size: 1rem;
            }
        """
        st.session_state['calendar_generated'] = True

    # Render calendar if events are stored
    if st.session_state.get('calendar_generated', False):
        calendar_1 = calendar(
            events=st.session_state['calendar_events'],
            options=st.session_state['calendar_options'],
            custom_css=st.session_state['custom_css']
        )
        st.write(calendar_1)

# Main application
def main():
    passcodes = 'admin/.passcodes.json'
    config_path = 'admin/config.json'
    with open(config_path, 'r') as file:
        config = json.load(file)
    passcodes_data = load_passcodes(passcodes)
    
    # Sequential forms logic
    if st.session_state['form_stage'] >= 1:
        homepage(passcodes_data)
    if st.session_state['form_stage'] >= 2:
        main_menu()
    if st.session_state['form_stage'] >= 3 and st.session_state["Task"] == "Register new participant":
        register_participant(config)
        if st.session_state['form_stage'] >= 4 and ('CoreVisitComplete' in st.session_state and st.session_state['CoreVisitComplete']):
            follow_up_visits()
        if st.session_state['form_stage'] >= 5 and ('FollowUpVisits' in st.session_state and st.session_state['FollowUpVisits']):
            preview_participant_information()
    if st.session_state['form_stage'] >= 3 and st.session_state["Task"] == "Edit email templates":
        edit_email_templates()
    if st.session_state['form_stage'] >= 3 and st.session_state["Task"] == "Participant lookup":
        participant_lookup()
    if st.session_state['form_stage'] >= 3 and st.session_state["Task"] == "View or edit CSVs":
        view_or_edit_csvs()
    if st.session_state['form_stage'] >= 3 and st.session_state["Task"] == "View scheduled emails":
        view_scheduled_emails()
        

if __name__ == '__main__':
    main()
