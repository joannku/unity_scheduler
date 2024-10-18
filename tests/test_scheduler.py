import pytest
from unittest import mock
from src.EmailScheduler import Scheduler
import os
import pandas as pd

@pytest.fixture
def mock_paths():
    return {
        'visit_schedule_local': 'test_data/visit_schedule.csv',
        'email_schedule_local': 'test_data/email_schedule.csv',
        'email_templates_local': 'test_data/email_templates.csv',
        'email_log_local': 'test_data/email_log.csv',
        'visit_schedule_streamlit': 'test_data/visit_schedule_streamlit.csv',
        'email_templates_streamlit': 'test_data/email_templates_streamlit.csv',
        'creds': 'test_data/creds.json',
        'log_file': 'test_data/test_log.log',
        'local_dir': 'test_data/',
        'backup_dir': 'test_data/backups/',
        'email_sender': 'test_sender@example.com'
    }

@pytest.fixture
def scheduler(mock_paths):
    return Scheduler(mock_paths, backup_limit=60, overwrite_local=True)

@mock.patch('src.scheduler.OutlookEmailer.authenticate_outlook')
def test_authenticate_outlook(mock_authenticate, scheduler):
    mock_authenticate.return_value.is_authenticated = True
    account = scheduler.emailer.authenticate_outlook()
    assert account.is_authenticated

@mock.patch('src.scheduler.OutlookEmailer.send_email_from_outlook')
def test_send_email(mock_send_email, scheduler):
    mock_send_email.return_value = True
    status = scheduler.send_email(
        pid='1234',
        email_data={
            'EmailCode': 'reminder',
            'Subject': 'Test Subject',
            'EmailBody': 'Test Body',
            'Email': 'test@example.com'
        }
    )
    assert status

def test_backup_local_csvs(scheduler):
    with mock.patch('os.listdir', return_value=['visit_schedule.csv']), \
         mock.patch('shutil.copy2') as mock_copy2, \
         mock.patch('filecmp.cmp', return_value=False):
        scheduler.backup_local_csvs()
        mock_copy2.assert_called_once()

def test_check_missing_schedule(scheduler):
    scheduler.df_vs_l = pd.DataFrame({
        'ParticipantID': ['1234', '5678'],
        'Email': ['test1@example.com', 'test2@example.com'],
        'Active': [True, True]
    })
    scheduler.df_es_l = pd.DataFrame({
        'ParticipantID': ['5678']
    })
    missing_schedule = scheduler.check_missing_schedule()
    assert '1234' in missing_schedule
