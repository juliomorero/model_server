#!/bin/bash

#Ubuntu
#MIN_LINES_COV=76.3
#MIN_FUNCTION_COV=88.3

#Rhel
MIN_LINES_COV=75.0
MIN_FUNCTION_COV=75.6

LINES_COV=`cat genhtml/index.html | grep "headerCovTableEntry.*%" | grep -oP  ">\K(\d*.\d*) " | head -n 1`
FUNC_COV=`cat genhtml/index.html | grep "headerCovTableEntry.*%" | grep -oP  ">\K(\d*.\d*) " | tail -n 1`

if (( $(echo "$MIN_LINES_COV > $LINES_COV" | bc -l) )); then
    echo "Error: $LINES_COV % Lines coverage is lower than minimal $MIN_LINES_COV %"
    exit 1
fi

if (( $(echo "$MIN_FUNCTION_COV > $FUNC_COV" | bc -l) )); then
    echo "Error: $FUNCTION_COV % Functions coverage is lower than minimal $MIN_FUNCTION_COV %"
    exit 1
fi

echo "Coverage check success"
exit 0
