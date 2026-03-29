# Secure Processor Architecture Simulator

This project is a full-stack Flask application simulating a secure processor for a Computer Organization and Architecture project.

Features:
- Authentication (Admin/User) with session login and secure password hashing
- Secure memory simulation stored in SQLite
- AES/Fernet encryption using `cryptography` (data encrypted at rest)
- Role-based access control (Admin can access all; User only assigned addresses)
- Unauthorized access logging (failed logins, invalid addresses, role violations)
- Modern dark theme with glassmorphism UI and responsive layout

Quick start (Windows):

1. Create a virtualenv and install requirements

```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

2. Run the app

```powershell
python app.py
```

3. Open http://127.0.0.1:5000

Default accounts: `admin` / `adminpass`, `user` / `userpass`.

Notes:
- On first run the app will generate a `secret.key` for Fernet and create `data.db`.
- Admin can view logs at `/logs` and access `/admin` dashboard.
