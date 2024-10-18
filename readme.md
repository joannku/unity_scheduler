# Scheduler and Email Automation System

## Overview
This system is designed to automate the scheduling and sending of emails to participants based on a predefined visit schedule. It integrates with a local file system to maintain backups, and a Streamlit interface allows users to manually manage visit schedules. The system ensures that participants receive timely and accurate reminders, and can handle updates to the schedule dynamically. Below is a detailed description of the core functionality and workflow of the system.

## Features

### 1. Adding a New Participant
- **Manual Addition via Streamlit app**: Users can manually add new participants to the visit schedule through the Streamlit interface. This action allows new participants to be registered with a specific `ParticipantID` and associated visit dates.
- **Automated Sync**: Once a new participant is added to the Streamlit visit schedule, the system automatically detects this change and updates the local visit schedule file accordingly. This ensures data consistency across the system.

### 2. Generating Email Schedules
- **Automatic Email Schedule Generation**: After detecting a new participant in the local visit schedule, the system generates an email schedule for this participant. This schedule is based on predefined templates and offsets that determine when specific emails (e.g., reminders, follow-ups) should be sent.
- **Customizable Email Templates**: Email templates are stored in a separate configuration file, where users can define the subject, body, and offsets for each type of email. The system uses this information to populate and schedule emails for new participants.

### 3. Sending Emails to Participants
- **Daily Email Checks**: The system automatically checks the local email schedule daily to determine if any emails are scheduled to be sent on the current date. If there are, it prepares the necessary details and sends them out.
- **New Participant Emails**: If a new participant has been registered, and they are due to receive an email on the same day, the system ensures that these emails are sent promptly.
- **Bulk Email Capability**: The system can handle sending multiple emails in one run, whether it's multiple emails to the same participant (e.g., different reminders) or emails to different participants. This enables efficient communication without the need for manual intervention.

### 4. Dynamic Update Handling
- **Date Changes in Visit Schedule**: If users manually update the visit schedule for a participant via the Streamlit interface (e.g., changing the date of a visit), the system will detect these changes and respond accordingly.
  - **New Schedule Generation**: A new email schedule is generated for the updated participant, replacing the previous one.
  - **Clearing Future Emails**: Any previously scheduled emails for dates in the future will be cleared from the email schedule. This ensures that outdated or incorrect emails are not sent. 
  - **Past Emails Remain Unchanged**: Emails that were scheduled for dates in the past remain unaffected. This ensures that the system does not interfere with reminders that have already been sent, preserving historical accuracy.

### 5. Robust Backup System
- **Scheduled Backups**: The system regularly backs up the local CSV files (visit schedules, email schedules, and logs) to a designated backup directory. 
- **Change Detection**: Before creating a backup, the system compares current files to the most recent backups. If there are no changes, the backup is skipped to save storage space.
- **Automatic Cleanup**: Older backups are automatically deleted based on a defined retention period, ensuring that only recent, relevant data is kept on the system.

## Workflow Summary
1. **Manual Registration**: A new participant is added to the Streamlit visit schedule.
2. **Sync to Local**: The system automatically copies the new participant's data to the local visit schedule file.
3. **Email Schedule Generation**: An email schedule is generated for the new participant based on predefined templates and visit dates.
4. **Daily Email Dispatch**: The system checks if any emails are scheduled to be sent today and sends them.
5. **Dynamic Schedule Updates**: If visit dates are manually changed in the Streamlit file, the system clears future emails and regenerates the schedule based on the new dates.
6. **Backup & Maintenance**: Regular backups are performed, ensuring data safety and reliability.

## Key Advantages
- **Automation**: Reduces the need for manual intervention, ensuring that emails are sent accurately and on time.
- **Adaptability**: Handles updates to schedules dynamically, ensuring that changes are reflected without causing disruption.
- **Scalability**: Can handle multiple participants and send bulk emails in a single run, making it suitable for large-scale operations.
- **Data Integrity**: Ensures data consistency between the Streamlit and local files, with robust backup mechanisms for safety.

## Conclusion
This system is a comprehensive solution for managing participant communication based on a scheduled set of visits. By automating routine tasks such as email scheduling, sending, and backup, it helps streamline operations, reduces errors, and improves efficiency. Its ability to dynamically adapt to schedule changes ensures that participants receive accurate and timely information without the need for manual oversight.
