#!/bin/bash

# Remember to source this script to run it in the same 
# environment instead of bash it


# activate venv 
echo "Activating venv..."
source .venv/bin/activate

# set profile n sso login
echo "Setting profile as shiwei for this session..." 
export AWS_PROFILE=shiwei

echo "using sso to login..."
aws sso login


