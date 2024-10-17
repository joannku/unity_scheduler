import re
import pandas as pd
import json
import os
import csv
import logging
import streamlit as st
import datetime
import lxml
import datetime as DateTime
import numpy as np
import subprocess
from dateutil.relativedelta import relativedelta
from datetime import time, date
from io import StringIO

class StreamlitScheduler:

    def __init__(self, config, passcodes):
        
        self.config = self.__load_config(config)
        self.passcodes = self.__load_passcodes(passcodes)
        self.homepage()
        if 'LoginComplete' in st.session_state and st.session_state['LoginComplete']:
            self.main_menu()
        if 'TaskComplete' in st.session_state and st.session_state['TaskComplete']:
            if st.session_state["Task"] == "Register new participant":
                st.session_state['participant_dict'] = self.register_participant()
            if 'CoreVisitComplete' in st.session_state and st.session_state['CoreVisitComplete']:
                self.follow_up_visits()

    def __load_config(self, config):
        with open(config, 'r') as file:
            config = json.load(file)
        return config
    
    def __load_passcodes(self, passcodes):
        with open('admin/.passcodes.json', 'r') as file:
            passcodes_data = json.load(file)
        return passcodes_data
    
    def homepage(self):
        logo_unity = st.image(
        "https://images.squarespace-cdn.com/content/v1/6192f109da8fd57373625bc7/d3657d1b-7b0f-4f67-80c1-dc0c81b1f4ab/LOGO111111.png?format=1500w", 
        width=300, output_format="PNG")
        st.caption("VERSION 2.0 Released 11/10/2024")
        title = st.title("UNITy Experimenter Dashboard")
        valid_passcodes = list(self.passcodes.values())

        with st.form("Login"): 
            st.session_state['Passcode'] = st.text_input("Please enter your Experimenter Passcode to proceed:", type='password')
            button_login = st.form_submit_button(label="Submit")
            if button_login: 
                if st.session_state['Passcode'] not in valid_passcodes:
                    st.error("Wrong passcode.")
                else: 
                    st.session_state['LoginComplete'] = True

            if 'LoginComplete' in st.session_state and st.session_state['LoginComplete']:
                st.success("Correct passcode. Welcome to the UNITy Experimenter Dashboard!")
                return st.session_state['LoginComplete']
    
    def main_menu(self):
        choices = [
            "Register new participant",
            "Update participant information or visit schedule",
        ]

        with st.form("SelectTask"): 
            st.session_state["Task"] = st.radio("What would you like to do today?", choices)
            button_task = st.form_submit_button("Submit")
            if button_task: 
                st.session_state['TaskComplete'] = True
                return st.session_state['TaskComplete']

    def register_participant(self):

        st.divider()
        st.subheader(st.session_state["Task"])

        if st.session_state["Task"] == "Register new participant":

            with st.form("Register"): 

                st.write(f"Please fill in the following information for the new participant:")

                st.session_state['participant_dict'] = {}

                # Participant ID
                st.session_state['participant_dict']["ParticipantID"] = st.text_input("Participant ID") #TODO: This can be linked with a list of existing participant IDs from another google sheet

                # Core visit dates
                st.write("Core visit dates:")
                st.session_state['participant_dict']["V1_Date"] = st.date_input("Visit 1 Date")
                st.session_state['participant_dict']["V1_Time"] = st.time_input("Visit 1 Time", datetime.time(12,0))
                st.session_state['participant_dict']["V2_Date"] = st.date_input("Visit 2 Date")
                st.session_state['participant_dict']["V2_Time"] = st.time_input("Visit 2 Time", datetime.time(12,0))
                st.session_state['participant_dict']["V3_Date"] = st.date_input("Visit 3 Date")
                st.session_state['participant_dict']["V3_Time"] = st.time_input("Visit 3 Time", datetime.time(12,0))
                
                # Follow-up visit dates
                st.write("Follow-up visit dates:")
                st.session_state['follow_up_selection'] = st.radio("How would you like to schedule follow-up visits?", ["Use automatic scheduling based on V2 date", "Manually schedule follow-up visits"])
                st.caption("You can always manually edit the follow-up dates later.")


                if st.form_submit_button("Submit"):
                    # check if participant ID is not none 
                    if st.session_state['participant_dict']["ParticipantID"] is "":
                        st.error("Please enter a valid participant ID.")
                    else:
                        st.session_state['CoreVisitComplete'] = True
                        return st.session_state['participant_dict']
                
    def follow_up_visits(self):
        
        with st.form("FollowUps"): 
            st.write(f"Follow-up visit dates for participant {st.session_state['participant_dict']['ParticipantID']}:")

            if st.form_submit_button("Submit"):
                st.session_state['FollowUpVisits'] = True
      


                # if 'follow_up_selection' in st.session_state: 
                #     if st.session_state['follow_up_selection'] == "Use automatic scheduling based on V2 date":
                #         V4_Date = V2_Date + relativedelta(months=+1)
                #         V4_Time = V2_Time
                #         V5_Date = V2_Date + relativedelta(months=+2)
                #         V5_Time = V2_Time
                #         V6_Date = V2_Date + relativedelta(months=+3)
                #         V6_Time = V2_Time
                #         V7_Date = V2_Date + relativedelta(months=+4)
                #         V7_Time = V2_Time
                #     else:
                #         V4_Date = st.date_input("Visit 4 Date")
                #         V4_Time = st.time_input("Visit 4 Time", datetime.time(12,0))
                #         V5_Date = st.date_input("Visit 5 Date")
                #         V5_Time = st.time_input("Visit 5 Time", datetime.time(12,0))
                #         V6_Date = st.date_input("Visit 6 Date")
                #         V6_Time = st.time_input("Visit 6 Time", datetime.time(12,0))
                #         V7_Date = st.date_input("Visit 7 Date")
                #         V7_Time = st.time_input("Visit 7 Time", datetime.time(12,0))





                # FirstName = st.text_input("First Name")
                # LastName = st.text_input("Last Name")
                # Gender = st.selectbox("Gender", self.config['gender'])
                # Email = st.text_input("Email")
                # Number = st.text_input("Number")
                # Arm	= st.selectbox("Arm", self.config['arm'])
                # DrinkPreference = st.selectbox("Drink Preference", self.config['drink_preference'])
                # MemoryReconsolidation = st.selectbox("Memory Reconsolidation Condition", self.config['memory_reconsolidation'])

                # Researcher1 = st.selectbox("Researcher 1", self.config['experimenters'])
                # Researcher2 = st.selectbox("Researcher 2", self.config['experimenters'])
                
                # Glasses = st.text_input("If the participant wears glasses, please enter their prescription (optional)")
                
                # Visit1_date	= st.date_input("Visit 1 Date")
                # Visit1_time	= st.time_input("Visit 1 Time", datetime.time(12,0))
                # Visit1_movie = st.selectbox("Visit 1 Movie", self.config['movies'])

                # Visit1_fmrioperator	= st.selectbox("Visit 1 fMRI operator", self.config['fmri_operators'])
                # Visit2_date	= st.date_input("Visit 2 Date")
                # Visit2_time	= st.time_input("Visit 2 Time", datetime.time(12,0))
                # Visit2_operator= st.selectbox("Visit2 Operator (if applicable)", self.config['fmri_operators'])

                # Medic = st.selectbox("Medic", self.config['medics'])

                # Visit3_date	= st.date_input("Visit3 Date")
                # Visit3_time	= st.time_input("Visit3 Time", datetime.time(12,0))
                # Visit3_movie = st.selectbox("Visit3 Movie", self.config['movies'])
                # Visit3_fmrioperator	= st.selectbox("Visit3 fMRI operator", self.config['fmri_operators'])
                
                

                
       

if __name__ == '__main__':
    config = 'admin/config.json'
    passcodes = 'admin/.passcodes.json'
    streamlit = StreamlitScheduler(config, passcodes)