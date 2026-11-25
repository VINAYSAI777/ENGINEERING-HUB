# Engineering Hub

A Flask-based student resource library.

## Features
- Public browsing and downloads for approved resources
- Student registration and sign-in
- Upload submissions for notes, question papers, lab materials and lesson links
- Administrator approval before resources become public
- Search and branch filtering
- SQLite database and password hashing

## Run on your computer
1. Install Python 3.
2. Open a terminal in this folder.
3. Run `python -m pip install -r requirements.txt`
4. Run `python app.py`
5. Open http://127.0.0.1:5000

## Administrator account
Set environment variables `ADMIN_EMAIL` and `ADMIN_PASSWORD` before the first run to create an administrator account. Use a strong, unique password and keep it private.

## Deploy
The included `render.yaml` is a starting point for deployment on Render. It configures persistent storage for the database and uploaded files. A persistent disk may require a paid Render plan. Set `ADMIN_EMAIL` and `ADMIN_PASSWORD` in the service environment before deployment.
