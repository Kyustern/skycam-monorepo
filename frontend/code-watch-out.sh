#!/bin/bash

# Create the reports directory if it doesn't exist
mkdir -p ~/code-crashes-reports

# Generate a unique filename with the current date, hour, and minute
timestamp=$(date +"%Y-%m-%d_%H-%M")
report_file="/home/leon/code-crashes-reports/report_${timestamp}.txt"

#create the file first
echo $report_file
touch $report_file

# Launch VS Code with the unique report file
code . --verbose > "$report_file"
