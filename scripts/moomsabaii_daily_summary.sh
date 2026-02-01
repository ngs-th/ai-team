#!/bin/bash
# Moomsabaii Daily Report - Split Message Version
# Sends report in multiple smaller messages to avoid Telegram limits

set -e

SCRIPT_DIR="/Users/ngs/Library/CloudStorage/OneDrive-Personal/obsidian-vault/Scripts/moomsabaii"
DB_PATH="$SCRIPT_DIR/moomsabaii.db"
TEMPLATE_PATH="$SCRIPT_DIR/daily_finance_report_template.txt"

# Get yesterday's date
YESTERDAY=$(date -v-1d +%Y-%m-%d)

# Generate report to temp file
TEMP_REPORT=$(mktemp)
python3 "$SCRIPT_DIR/daily_finance_report.py" --date "$YESTERDAY" > "$TEMP_REPORT" 2>&1

# Extract key data using grep/sed for summary
INCOME=$(grep "Income (excl. CashExchange)" "$TEMP_REPORT" | grep -o '[0-9,]*\.[0-9]*' | head -1 || echo "0.00")
EXPENSE=$(grep "Expense" "$TEMP_REPORT" | grep -o '[0-9,]*\.[0-9]*' | head -1 || echo "0.00")
NET=$(grep "Net" "$TEMP_REPORT" | grep -o '[+-][0-9,]*\.[0-9]*' | head -1 || echo "+0.00")

# Send Message 1: Header + Overview
echo "📊 MOOMSABAIi Daily Report"
echo "Date: $YESTERDAY"
echo ""
echo "💰 OVERVIEW"
echo "• Income: ฿$INCOME"
echo "• Expense: ฿$EXPENSE"
echo "• Net: ฿$NET"

# Send Message 2: Payment Methods (if data exists)
if grep -q "Cash\|Transfer" "$TEMP_REPORT"; then
    echo ""
    echo "💳 PAYMENT METHODS"
    grep -A5 "PAYMENT METHODS" "$TEMP_REPORT" | grep "|" | tail -n +3 | head -n 2 || true
fi

# Send Message 3: Top Categories (if data exists)
if grep -q "Membership\|Beverages\|MeetingRoom" "$TEMP_REPORT"; then
    echo ""
    echo "📈 TOP CATEGORIES"
    grep -A10 "INCOME BY CATEGORY" "$TEMP_REPORT" | grep "|" | tail -n +3 | head -n 4 || true
fi

# Cleanup
rm -f "$TEMP_REPORT"
