import re
import glob
import gzip
import sys
from collections import defaultdict
from datetime import datetime
from statistics import mode

# Regular expression to match the specific cron log entries
cron_regex = re.compile(r'^(\S*) .*CRON\[\d+\]:\s+\((.*?)\)\s+CMD\s+\((.*)\)$')

def process_file(file, cron_jobs, debug=False):
    for line in file:
        match = cron_regex.search(line)
        if match:
            timestamp_str = match.group(1)
            username = match.group(2)
            command = match.group(3)
            cron_jobs[username].append((timestamp_str, command))
            if debug:
                print(f"Found cron job: {username} -> {command} at {timestamp_str}")


def extract_cron_jobs(log_files, debug=False):
    cron_jobs = defaultdict(list)

    for log_file in log_files:
        if debug:
            print(f"Processing log file: {log_file}")

        if log_file.endswith('.gz'):
            # Read gzip-compressed log files
            with gzip.open(log_file, 'rt') as file:
                process_file(file, cron_jobs, debug)
        else:
            # Read regular log files
            with open(log_file, 'r') as file:
                process_file(file, cron_jobs, debug)

    return cron_jobs

def extrapolate_schedule(entries):
    command_timestamps = defaultdict(list)

    # Populate command_timestamps dictionary
    for timestamp_str, command in entries:
        timestamp = datetime.fromisoformat(timestamp_str)
        command_timestamps[command].append(timestamp)

    schedules = {}

    # Calculate schedule for each command
    for command, timestamps in command_timestamps.items():
        if len(timestamps) < 2:
            schedules[command] = "*   *  *  *  *"  # Default to every minute if not enough data
            continue

        # Calculate intervals
        intervals = [(timestamps[i] - timestamps[i-1]).total_seconds() / 60 for i in range(1, len(timestamps))]
        average_interval = round(sum(intervals) / len(intervals))

        if average_interval == 1:
            schedules[command] = "* * * * *"  # Every minute
        elif average_interval < 60:
            schedules[command] = f"*/{average_interval} * * * *"  # N-minute intervals within the hour
        else:
            # Calculate the most common minute of the hour
            minute_list = [ts.minute for ts in timestamps]
            try:
                common_minute = mode(minute_list)  # Use mode for the most common minute
            except:
                common_minute = 0  # Default to 0 if mode cannot be calculated

            if average_interval < 1440:
                # Calculate hours for intervals under one day
                hour_set = {ts.hour for ts in timestamps}
                hour_string = ','.join(f"{hour:02}" for hour in sorted(hour_set))
                schedules[command] = f"{common_minute} {hour_string} * * *"  # At specified minute of the hours
            else:
                # Default to daily at the most common hour and minute
                day_set = {ts.day for ts in timestamps}
                day_string = ','.join(f"{day:02}" for day in sorted(day_set))
                schedules[command] = f"{common_minute} {day_string} * * *"

    return schedules

def write_crontabs(cron_jobs):
    for username, entries in cron_jobs.items():
        command_schedules = extrapolate_schedule(entries)

        with open(f'crontab_{username}', 'w') as crontab_file:
            for command, schedule in command_schedules.items():
                crontab_file.write(f'{schedule} {command.strip()}\n')

if __name__ == "__main__":
    debug_mode = len(sys.argv) > 1 and sys.argv[1] == '--debug'
    log_files = glob.glob('/var/log/syslog*')
    cron_jobs = extract_cron_jobs(log_files, debug_mode)
    write_crontabs(cron_jobs)
    print("Crontabs recreated and saved for each user.")
