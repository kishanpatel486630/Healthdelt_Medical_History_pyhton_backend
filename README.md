# Healthdelt Medical History — Python Backend

<p align="center">
  <img src="https://img.shields.io/badge/FastAPI-0.136-009688?style=for-the-badge&logo=fastapi&logoColor=white"/>
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/SQLAlchemy-2.0-red?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Deployed_on-Render-46E3B7?style=for-the-badge&logo=render&logoColor=white"/>
</p>

A robust **FastAPI** backend powering the Healthdelt Medical History Ecosystem. Handles patient records, doctor management, appointments, prescriptions, medical reports, and JWT-based authentication.

---

## 🚀 Live Deployment (Render)

| Resource | URL |
|----------|-----|
| API Base URL | `https://healthdelt-medical-history-pyhton-backend.onrender.com` |
| Health Check | `GET /api/health` |
| API Docs | `GET /docs` (Swagger UI) |
| ReDoc | `GET /redoc` |

> **Note:** The Render free tier spins down after inactivity. The first request may take ~30 seconds to wake up.

---

## 📁 Project Structure

```
python-backend/
├── app/
│   ├── __init__.py
│   ├── main.py            # FastAPI app entry point, CORS, router registration
│   ├── config.py          # Pydantic settings (reads from .env)
│   ├── database.py        # SQLAlchemy engine & session factory
│   ├── models.py          # Database models (ORM)
│   ├── dependencies.py    # Auth & shared dependencies
│   ├── security.py        # JWT encode/decode, password hashing
│   └── routers/
│       ├── auth.py            # Login, register, refresh token
│       ├── users.py           # Patient profile management
│       ├── doctors.py         # Doctor search & profiles
│       ├── doctor_me.py       # Doctor self-management
│       ├── history.py         # Medical history records
│       ├── appointments.py    # Appointment booking & management
│       ├── prescriptions.py   # Prescription management
│       ├── reports.py         # Medical report uploads & retrieval
│       └── notifications.py   # User notifications
├── uploads/               # Uploaded files (ephemeral on Render)
├── seed.py                # Database seeder script
├── requirements.txt       # Python dependencies
├── .env.example           # Environment variable template
└── .gitignore
```

---

## ⚙️ Local Development Setup

### Prerequisites
- Python 3.11+
- pip

### 1. Clone the repository
```bash
git clone https://github.com/kishanpatel486630/Healthdelt_Medical_History_pyhton_backend.git
cd Healthdelt_Medical_History_pyhton_backend
```

### 2. Create a virtual environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables
```bash
# Copy the example file
cp .env.example .env

# Edit .env with your local values
```

For local development, the default SQLite config works out of the box:
```env
DATABASE_URL=sqlite:///./healthdelt.db
JWT_ACCESS_SECRET=your-local-dev-secret
JWT_REFRESH_SECRET=your-local-dev-refresh-secret
```

### 5. Run the development server
```bash
uvicorn app.main:app --reload --port 5000
```

API is now available at: `http://localhost:5000`  
Swagger docs at: `http://localhost:5000/docs`

---

## ☁️ Deploying to Render

### Step 1 — Create a PostgreSQL Database on Render
1. Go to [Render Dashboard](https://dashboard.render.com/) → **New → PostgreSQL**
2. Name it `healthdelt-db`, select the **Free** plan
3. Copy the **Internal Database URL** (used for `DATABASE_URL`)

### Step 2 — Create a Web Service
1. **New → Web Service** → connect your GitHub repo
2. Configure the service:

| Setting | Value |
|---------|-------|
| **Runtime** | Python 3 |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT` |
| **Instance Type** | Free (or paid for always-on) |

> **Why `gunicorn` instead of `uvicorn` directly?**  
> Gunicorn acts as a process manager and spawns multiple `uvicorn` worker processes (`-w 4`), making your app far more stable and performant in production. The `-k uvicorn.workers.UvicornWorker` flag tells Gunicorn to use ASGI-compatible workers (required for FastAPI).  
> For Render's **free tier** (limited RAM), you can reduce to `-w 2` to avoid memory issues.

### Step 3 — Set Environment Variables
In your Render Web Service → **Environment** tab, add the following variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL Internal URL from Render | `postgresql://user:pass@dpg-xxx/db` |
| `JWT_ACCESS_SECRET` | Strong random secret for access tokens | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `JWT_REFRESH_SECRET` | Strong random secret for refresh tokens | *(same method)* |
| `ALGORITHM` | JWT signing algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime | `15` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token lifetime | `7` |
| `CLIENT_URL` | Your frontend's deployed URL | `https://your-frontend.onrender.com` |
| `UPLOAD_DIR` | File upload directory | `./uploads` |
| `MAX_FILE_SIZE` | Max upload size in bytes | `10485760` |
| `ENVIRONMENT` | Runtime environment tag | `production` |

> ⚠️ **Do NOT set `PORT`** — Render injects this automatically.

### Step 4 — Deploy
Click **Deploy** — Render will build and start your service automatically.

---

## 🔑 API Endpoints Overview

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login & receive JWT tokens |
| POST | `/api/auth/refresh` | Refresh access token |
| POST | `/api/auth/logout` | Invalidate refresh token |

### Users / Patients
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/users/me` | Get current user profile |
| PUT | `/api/users/me` | Update profile |
| POST | `/api/users/me/avatar` | Upload profile picture |

### Doctors
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/doctors` | List all doctors |
| GET | `/api/doctors/{id}` | Get doctor by ID |
| GET | `/api/doctors/me` | Doctor self-profile |
| PUT | `/api/doctors/me` | Update doctor profile |

### Medical Records
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/history` | Get medical history |
| POST | `/api/history` | Add history record |
| GET | `/api/prescriptions` | List prescriptions |
| POST | `/api/prescriptions` | Add prescription |
| GET | `/api/reports` | List medical reports |
| POST | `/api/reports` | Upload report |

### Appointments & Notifications
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/appointments` | List appointments |
| POST | `/api/appointments` | Book appointment |
| PUT | `/api/appointments/{id}` | Update appointment status |
| GET | `/api/notifications` | Get notifications |

> 📄 Full interactive documentation available at `/docs` (Swagger UI) when the server is running.

---

## 🔐 Authentication

This API uses **JWT (JSON Web Tokens)** with a dual-token strategy:

- **Access Token** — Short-lived (15 min), sent in `Authorization: Bearer <token>` header
- **Refresh Token** — Long-lived (7 days), used to obtain a new access token

JWT secrets must match any companion Node.js backend if token compatibility is required.

---

## 📦 Key Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `fastapi` | 0.136 | Web framework |
| `uvicorn` | 0.47 | ASGI server |
| `sqlalchemy` | 2.0 | ORM & database abstraction |
| `alembic` | 1.18 | Database migrations |
| `pydantic` | 2.13 | Data validation & settings |
| `pyjwt` | 2.12 | JWT token handling |
| `bcrypt` | 5.0 | Password hashing |
| `passlib` | 1.7 | Password utilities |
| `python-multipart` | 0.0.29 | File upload support |
| `pillow` | 12.2 | Image processing |
| `reportlab` | 4.5 | PDF generation |

---

## ⚠️ Important Notes for Production (Render)

1. **Ephemeral Filesystem** — Render's free tier does **not** persist files between deploys. Uploaded files (`/uploads`) will be lost on redeploy. Integrate **Cloudinary** or **AWS S3** for persistent file storage.

2. **SQLite → PostgreSQL** — SQLite is for local dev only. Render requires PostgreSQL. Update `DATABASE_URL` in environment variables.

3. **CORS Origins** — Update `allow_origins` in `app/main.py` to include your production frontend URL, or set it via `CLIENT_URL` env var.

4. **Free Tier Spin-Down** — Free Render services sleep after 15 minutes of inactivity. Upgrade to a paid plan for always-on availability.

---

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is part of the **Healthdelt Medical History Ecosystem**.  
© 2024 Kishan Patel. All rights reserved.
