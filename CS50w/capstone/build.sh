#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Convert static asset files for WhiteNoise
python manage.py collectstatic --no-input

# Make and apply database migrations
python manage.py makemigrations
python manage.py migrate