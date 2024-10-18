import sys
import os

# Add the parent directory (or any specific directory) to PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.EmailScheduler import Scheduler
from datetime import datetime

if __name__ == "__main__":
    try:
        # Open the current log file (overwrite) and the cumulative log file (append)
        report_log = open("logs/report_log.txt", "wt")  # Overwrite mode for current log
        all_logs = open("logs/all_logs.txt", "a")  # Append mode for cumulative log

        # Redirect stdout to both log files
        class Tee:
            def __init__(self, *files):
                self.files = files

            def write(self, obj):
                for f in self.files:
                    f.write(obj)

            def flush(self):
                for f in self.files:
                    f.flush()

        sys.stdout = Tee(report_log, all_logs)

        print(f"REPORT begin at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        paths = 'admin/paths.json'
        scheduler = Scheduler(paths, backup_limit=60, overwrite_local=True)
        scheduler.main()

        print(f"REPORT end at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    except Exception as e:
        print(f"An error occurred: {e}, {e.with_traceback(None)}")

    # Stop redirecting stdout and close the log files
    sys.stdout = sys.__stdout__  # Restore stdout to console
    report_log.close()
    all_logs.close()

    # Read report log file and prepare email content
    with open("logs/report_log.txt", "r") as log_file:
        log_content = log_file.read()

    # Replace both \r\n and \n with <br> for HTML formatted emails
    html_log_content = log_content.replace("\r\n", "<br>").replace("\n", "<br>")

    scheduler.emailer.send_email_from_outlook(
        sender="unity-project@ucl.ac.uk",
        recepients=["unity-project@ucl.ac.uk"],
        subject=f"UNITY Scheduler Report Log: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        email_body=f"<html><body>{html_log_content}</body></html>",
        attachments_paths=[
            "logs/report_log.txt"
        ],  # No need for file attachment if content is in the body
        code="ReportLog",
    )
