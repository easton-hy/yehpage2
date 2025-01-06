import os
import time
from datetime import datetime, timedelta
import ctypes
import re
import subprocess


'''
1. python to exe application: pyinstaller --noconsole --onefile recorder.py
2. Start the application once start the computer or log on:
    - Task Scheduler
    - Create a task to run the application at startup & log on
    - Set the task to run with the highest privileges
    - Change 'User or Group Name' to 'Administrators'
'''

# Path to save log file
log_file_path = "G:/yehpage2/plugin-page/heatmap_record/usage_time_log.txt"
html_file_path="G:/yehpage2/plugin-page/heatmap.html"
local_repo_path = r'G:\yehpage2'
commit_message = f'Automated heatmap update on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'

up_load_hour=3
up_load_min=0

# Initialize variables
start_time = None
minute_usage_time = timedelta()
current_minute_start = None
previous_locked_state = False  # Track if the system was locked previously
idle_threshold = 300  # Time in seconds to consider as "inactive"

# Load the User32 DLL
user32 = ctypes.windll.User32

def upload_web(repo_path, commit_message):
    try:
        os.chdir(repo_path)
        subprocess.run(['git', 'pull'], check=True)
        subprocess.run(['git', 'add', '.'], check=True)
        subprocess.run(['git', 'commit', '-m', commit_message], check=True)
        subprocess.run(['git', 'push'], check=True)

        print("Update and push completed successfully.")
    
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}")

def add_data_to_html(html_file_path, txt_file_path, repo_path, commit_message):
    duration_hours_list=[]
    try:
        with open(txt_file_path, 'r') as file:
            for line in file:
                # 假设每行的格式是 "timestamp, duration_hours hours"
                parts = line.strip().split(', ')
                if len(parts) == 2:
                    # 提取 duration_hours
                    duration_str = parts[1].split(' ')[0]
                    try:
                        duration_hours = float(duration_str)
                        duration_hours_list.append(duration_hours)
                    except ValueError:
                        print(f"无法解析时间：{duration_str}")
            total_duration_hours = sum(duration_hours_list)

            previous_date = datetime.now() - timedelta(days=1)
            current_date=previous_date.strftime('%Y-%m-%d')

            with open(html_file_path, 'r', encoding='utf-8') as html_file:
                html_content = html_file.read()

            pattern = r"(var\s+datas2025\s*=\s*\[)([\s\S]*?)(\]\s*;)"
            match = re.search(pattern, html_content, re.DOTALL)
            
            if match:
                original_data_start = match.group(1)  # 'var datas2025 = ['
                existing_data = match.group(2)        # 数组中的已有数据
                original_data_end = match.group(3)    # '];'

                new_data_entry = f"{{date: '{current_date}', value: {total_duration_hours}}}"

                if existing_data.strip():
                    updated_data = f"{original_data_start}{existing_data},\n{new_data_entry}{original_data_end}"
                else:
                    updated_data = f"{original_data_start}{new_data_entry}{original_data_end}"
                
                updated_content = html_content.replace(match.group(0), updated_data)
                
                with open(html_file_path, 'w', encoding='utf-8') as html_file:
                    html_file.write(updated_content)
                
                print("HTML file has been updated with the new data.")
            else:
                print("Could not find the 'datas2025' section in the HTML file.")

        file.close()
        try:
            upload_web(repo_path, commit_message)
        except:
            print("Cannot upload the web folder.")
        #os.remove(txt_file_path)
    except FileNotFoundError:
        print(f"{txt_file_path} file doesn't exist")

# Utility function to log minute usage duration to file
def log_minute_usage(minute_start, duration):
    """Log the accumulated time for each minute to file."""
    timestamp = minute_start.strftime('%Y-%m-%d %H:%M')
    duration_hours = round(duration.total_seconds() / 3600, 4)

    # Append a new line with the usage time for this minute
    if not os.path.exists(log_file_path):
        with open(log_file_path, 'w') as f:
            f.write(f"{timestamp}, {duration_hours} hours\n")
    else:
        with open(log_file_path, "a") as f:
            f.write(f"{timestamp}, {duration_hours} hours\n")

    print(f"Logged 1-minute usage: {timestamp}, {duration_hours} hours")

def read_duration_hours(minute_start,filename, log_total_path):
    timestamp = minute_start.strftime('%Y-%m-%d %H:%M')
    duration_hours_list = []
    try:
        with open(filename, 'r') as file:
            for line in file:
                # 假设每行的格式是 "timestamp, duration_hours hours"
                parts = line.strip().split(', ')
                if len(parts) == 2:
                    # 提取 duration_hours
                    duration_str = parts[1].split(' ')[0]
                    try:
                        duration_hours = float(duration_str)
                        duration_hours_list.append(duration_hours)
                    except ValueError:
                        print(f"无法解析时间：{duration_str}")
            total_duration_hours = sum(duration_hours_list)
            if not os.path.exists(log_total_path):
                with open(log_total_path, 'w') as f:
                    f.write(f"{timestamp}, {total_duration_hours} hours\n")
            else:
                with open(log_total_path, "a") as f:
                    f.write(f"{timestamp}, {total_duration_hours} hours\n")
            file.close()
            os.remove(filename)
            
    except FileNotFoundError:
        print(f"{filename} 文件不存在。")
    
    return duration_hours_list

# Windows API to get the last input time
class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

def is_locked():
    """Checks if the system is 'locked' based on inactivity duration."""
    last_input_info = LASTINPUTINFO()
    last_input_info.cbSize = ctypes.sizeof(LASTINPUTINFO)
    ctypes.windll.user32.GetLastInputInfo(ctypes.byref(last_input_info))
    millis = ctypes.windll.kernel32.GetTickCount() - last_input_info.dwTime
    idle_time = millis / 1000.0  # Convert to seconds
    return idle_time > idle_threshold  # Return True if idle time exceeds threshold

# Main monitoring function
def monitor_usage():
    global start_time, minute_usage_time, current_minute_start, previous_locked_state

    # Initialize start time and current minute start time
    start_time = datetime.now()
    current_minute_start = start_time.replace(second=0, microsecond=0)

    while True:
        current_locked_state = is_locked()  # Check if the system is locked
        print("Locked:", current_locked_state)

        # Only track time if the system is unlocked
        if not current_locked_state:  
            if previous_locked_state:
                # If just unlocked, reset start time and continue tracking
                start_time = datetime.now()
                print(f"System unlocked, resuming tracking at {start_time}")

            # Calculate the duration since the last 5-second interval
            end_time = datetime.now()
            session_duration = end_time - start_time
            minute_usage_time += session_duration  # Accumulate for this minute
            start_time = end_time  # Reset start time for the next interval

            # Check if a new minute has started
            if end_time.minute != current_minute_start.minute:
                # Log the total usage for the previous minute
                log_minute_usage(current_minute_start, minute_usage_time)

                # Reset for the new minute
                current_minute_start = end_time.replace(second=0, microsecond=0)
                minute_usage_time = timedelta()  # Reset minute usage time


        else:
            # If system is locked, reset start time but do not log until end of minute
            #if not previous_locked_state and minute_usage_time > timedelta(0):
            print(f"System locked at {datetime.now()}, pausing tracking")
            start_time = None  # Reset start time on idle
            print(minute_usage_time)
            # At the end of each minute, if locked and there was activity recorded
            #if datetime.now().minute != current_minute_start.minute and minute_usage_time > timedelta(0):
            if datetime.now().minute != current_minute_start.minute:
                log_minute_usage(current_minute_start, minute_usage_time)
                current_minute_start = datetime.now().replace(second=0, microsecond=0)
                minute_usage_time = timedelta()

        total_time_cal=datetime.now()
        log_total_path = "G:/yehpage2/plugin-page/heatmap_record/"+total_time_cal.strftime("%Y-%m-%d") + ".txt"
        pre_date=total_time_cal - timedelta(days=1)
        log_total_path_pre="G:/yehpage2/plugin-page/heatmap_record/"+pre_date.strftime("%Y-%m-%d") + ".txt"

        # Every two minutes, combine records
        if total_time_cal.minute == 0 and 0 <= total_time_cal.second <= 9:
            read_duration_hours(total_time_cal,log_file_path, log_total_path)

        if total_time_cal.hour == up_load_hour and total_time_cal.minute == up_load_min and 0 <= total_time_cal.second <= 9:
            commit_message = f'Automated heatmap update on {total_time_cal.strftime("%Y-%m-%d %H:%M:%S")}'
            add_data_to_html(html_file_path,log_total_path_pre, local_repo_path, commit_message)
        # Update the previous locked state
        previous_locked_state = current_locked_state

        # Wait 5 seconds before next check to detect lock state changes quickly
        time.sleep(10)

if __name__ == "__main__":
    monitor_usage()
    