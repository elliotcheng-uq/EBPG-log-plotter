# -*- coding: utf-8 -*-
"""
Beam Drift Plotter from the EBPG logfile
The Log file must contain JMAN LOGFILE in the first line
Tested for beams v9_14 to v9_16
Created on Fri Nov 15 11:03:14 2024

@author: Elliot Cheng @ University of Queensland
@Email: h.cheng6@uq.edu.au

"""

import os
import re
import sys
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import filedialog

def open_file():
    # Open file dialog to select a file
    file_path = filedialog.askopenfilename(title="Select a file to open", filetypes=[("Text Files", "*.log"), ("All Files", "*.*")])
    
    # Check if a file was selected
    if file_path:
        with open(file_path, 'r') as file:
            content = file.read()  # Read the contents of the file
            return content, file_path

#  Tkinter root window
root = tk.Tk()
root.withdraw()  

# Call the open_file function and store the file content in a path
path, file_path = open_file()

# Check if the first line contains the expected text "JMAN LOGFILE"
with open(file_path, 'r') as file:
    first_line = file.readline().strip()
    if "JMAN LOGFILE" not in first_line:
        print("Error: This is not a valid EBPG logfile")
        sys.exit()

# Define the regular expression patterns used for logfile search
wafer_centre_position = r"--centre=([0-9.-]+),([0-9.-]+).*--size=([0-9.-]+),([0-9.-]+)"
date_pattern = r"([A-Za-z]{3})\s([A-Za-z]{3})\s(\d{1,2})\s(\d{2}:\d{2}:\d{2})\s([A-Z]{3,4})\s(\d{4})"
drift_pattern = r"cal drift (\d+):(\d+)\s*;\s*(-?\d+\.?\d*)_nm,(-?\d+\.?\d*)_nm\s+(-?\d+\.?\d*)_nm/min,(-?\d+\.?\d*)_nm/min"
drift_position = r"block:\s(\d+)\s+Abs\scoord:\s([-+]?[0-9]*\.?[0-9]+)_mm,([-+]?[0-9]*\.?[0-9]+)_mm"

regex_wafer_centre = re.compile(wafer_centre_position)
regex_date = re.compile(date_pattern)
regex = re.compile(drift_pattern)
regex_drft_pos = re.compile(drift_position)

# Lists to store the parsed values
timestamps = []
dxdt_values = []
dydt_values = []
drift_pos_data = []
wafer_centre = []

# Variables to store the extracted date and time for the plot label
run_date = None
run_start_time = None

# Store the previous timestamp for day transition detection
previous_timestamp = None

# A flag to check if any drift data was found
drift_data_found = False

for line in path.splitlines():
    
    # Wafer centre absolution position parse
    centrematch = regex_wafer_centre.search(line)
    if centrematch:
        # Convert wafer center from micrometers (µm) to millimeters (mm)
        centre_x = float(centrematch.group(1)) / 1000  # Convert µm to mm
        centre_y = float(centrematch.group(2)) / 1000  # Convert µm to mm
        size_x = float(centrematch.group(3)) / 1000  # Convert µm to mm
        size_y = float(centrematch.group(4)) / 1000  # Convert µm to mm
        print(f"Centre: ({centre_x}, {centre_y})")
        print(f"Size: ({size_x}, {size_y})")
        wafer_centre = [centre_x, centre_y]
    
    # Look for date information from the log file
    datematch = regex_date.match(line)

    if datematch:
        dweek, dmonth, dday, dtime, dtzone, dyear = datematch.groups()
        
        # Store the first date and time found for the label
        if run_date is None:
            run_date = f"{dyear}-{dmonth}-{dday}"  # e.g., "2024-Nov-14"
            run_start_time = dtime  # e.g., "17:30:26"

    # Match the line against the drift data regular expression
    match = regex.search(line)
    
    if match:
        drift_data_found = True
        
        # Extract drift rate values
        hour, minute, _, _, dxdt, dydt = match.groups()

        # Use the date info from the match to create a complete timestamp
        timestamp = datetime.strptime(f'{dyear}-{dmonth}-{dday} {hour}:{minute}:00', '%Y-%b-%d %H:%M:%S')

        # Check if the logfile contains data cross two days
        if previous_timestamp and timestamp < previous_timestamp:
            timestamp += timedelta(days=1)  # Add one day

        # Store the current timestamp as the previous one for the next iteration
        previous_timestamp = timestamp

        # Convert drift values to floats
        dxdt = float(dxdt.replace('_nm/min', ''))
        dydt = float(dydt.replace('_nm/min', ''))

        # Append parsed values to lists
        timestamps.append(timestamp)
        dxdt_values.append(dxdt)
        dydt_values.append(dydt)
    
    # Match the drift calib stops position with regular expression
    driftpos_match = regex_drft_pos.search(line)
    if driftpos_match:
        # Extract block number and coordinates
        block_number = int(driftpos_match.group(1))  # Convert block number to integer
        x_coord = float(driftpos_match.group(2))  # Convert X coordinate to float (mm)
        y_coord = float(driftpos_match.group(3))  # Convert Y coordinate to float (mm)
        drift_pos_data.append((block_number, x_coord, y_coord))

# Check if no drift data was found
if not drift_data_found:
    print("Error: Log file is correct, but it contains no drift calibration points")
    sys.exit()

# Sort the drift calibration positions by block number, then by x coordinate, and y coordinate
sorted_drift_pos_data = sorted(drift_pos_data, key=lambda x: (x[0], x[1], x[2]))

# Now we calculate the relative drift positions with respect to the wafer center
relative_drift_pos_data = []

for block_number, x_coord, y_coord in sorted_drift_pos_data:
    # Calculate relative positions to the wafer center (in mm)
    rel_x = x_coord - wafer_centre[0]
    rel_y = y_coord - wafer_centre[1]
    
    # Store the relative drift positions along with the block number
    relative_drift_pos_data.append((block_number, rel_x, rel_y))

# Print the relative drift positions
print('Relative Drift Calibration Absolution Positions')

# Optionally, sort the relative drift positions if needed
sorted_relative_drift_pos_data = sorted(relative_drift_pos_data, key=lambda x: (x[0], x[1], x[2]))

# Print the sorted relative positions
for _, rel_x, rel_y in sorted_relative_drift_pos_data:
    print(f"Relative X: {rel_x}, Relative Y: {rel_y}")

# Create a separate plot for the wafer and drift calibration positions
plt.figure(figsize=(8, 8))

# Plot wafer size as the bounding box (in mm)
plt.xlim(-size_x/2, size_x/2)
plt.ylim(-size_y/2, size_y/2)

# Plot the relative drift calibration positions
for _, rel_x, rel_y in sorted_relative_drift_pos_data:
    plt.scatter(rel_x, rel_y, color='red', marker='x')

# Mark the wafer center
plt.scatter(0, 0, color='blue', label='Wafer Center', zorder=5)

# Add labels and title
plt.xlabel('X (mm)')
plt.ylabel('Y (mm)')
plt.title('Drift Calibration Positions Relative to Wafer Center')
plt.legend()
plt.grid(True)

# Show the plot
plt.show()

# Convert the timestamps to minutes since the start of the experiment
start_time = timestamps[0]
time_values = [(t - start_time).total_seconds()/60 for t in timestamps]

# Determine the "min" and "max" drift values for x and y (min should be closest to zero)
min_dx = min(dxdt_values, key=abs)
max_dx = max(dxdt_values, key=abs)
min_dy = min(dydt_values, key=abs)
max_dy = max(dydt_values, key=abs)

# Plot the drift rates as a function of time, using the extracted date and time in the label
plt.plot(time_values, dxdt_values, label='x drift')
plt.plot(time_values, dydt_values, label='y drift')

# Add a text box with min/max drift values at the bottom center
textstr = f'X Min/Max: {min_dx:.2f} / {max_dx:.2f} nm\nY Min/Max: {min_dy:.2f} / {max_dy:.2f} nm'
print(f'For logfile name: {file_path}\n{textstr}')

# Place the text box at the bottom center
plt.gca().text(0.5, 0.05, textstr, transform=plt.gca().transAxes, fontsize=8,
               horizontalalignment='center', verticalalignment='bottom', bbox=dict(facecolor='white', alpha=0.5))

plt.xlabel('Minutes (min)')
plt.ylabel('Beam Drift (nm/min)')
plt.title(f'Start time {run_date},{run_start_time}')
plt.legend()
plt.grid(True)
plt.show()
