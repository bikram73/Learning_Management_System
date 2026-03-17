# Learning Management System (LMS)

<p align="center">
  <img src="static/img/lms-logo.svg" alt="Learning Management System logo" width="130" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Flask-3.x-111111?logo=flask&logoColor=white" alt="Flask" />
  <img src="https://img.shields.io/badge/PostgreSQL-14+-336791?logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/SQLAlchemy-2.0+-D71F00?logo=sqlalchemy&logoColor=white" alt="SQLAlchemy" />
  <img src="https://img.shields.io/badge/Auth-JWT-0A0A0A?logo=jsonwebtokens&logoColor=white" alt="JWT" />
  <img src="https://img.shields.io/badge/Frontend-Vanilla%20JS-F7DF1E?logo=javascript&logoColor=black" alt="JavaScript" />
</p>

A full-featured web-based Learning Management System where students can discover, enroll in, and complete structured courses with video lessons, while teachers/admins create and manage course content. Includes secure authentication, payment processing for paid courses, real-time progress tracking, and comprehensive course search.

## ✨ Features

### 🎓 Student Features
- Browse and search all courses by title, description, or instructor
- Enroll in free courses instantly or paid courses with secure payment links
- Watch video lessons in proper 16:9 aspect ratio format
- Complete lessons and unlock the next lesson sequentially
- Track progress across all enrolled courses
- Reset forgotten passwords with secure email links (1-hour expiry)
- Responsive dashboard showing enrolled courses
- Password visibility toggle for secure credential entry

### 👨‍🏫 Teacher/Admin Features
- Create courses with title, description, instructor name, and custom thumbnails
- Manage course pricing (free or paid with custom price)
- Create ordered lessons with video embeds (YouTube, etc.)
- Edit course details including title, description, and thumbnail URL
- Delete courses and manage lesson order
- Track enrollments and completion rates
- View all courses and search functionality on dashboard
- Edit pricing and course metadata in real-time

### 🔐 Security & Authentication
- Student signup with email, username, and password validation
  - Email must be @gmail.com with proper format
  - Password minimum 10 characters with confirmation
- Admin signup with secret code `ADMIN2026`
- JWT-based stateless authentication
- Secure password reset flow with 1-hour expiring email links
- Rate-limited link generation (1 new link per hour per user)
- Logout functionality with token invalidation
- Role-based access control (student vs admin)

### 💳 Payment & Enrollment
- Paid course support with admin-configurable pricing
- Secure payment link generation and email delivery
- Payment links expire after 1 hour for security
- Only 1 active payment link per user per course per hour
- Automatic enrollment upon successful payment
- Free course instant enrollment

### 📧 Email Notifications
- Welcome email upon signup (student and admin)
- Course enrollment confirmation for paid courses
- Password reset email with secure token
- New lesson notification to enrolled students
- Payment receipt upon successful transaction

### 🔍 Search & Discovery
- Real-time course search across all courses
- Filter by title, description, or instructor name
- Available on public index page and student/admin dashboards
- Case-insensitive filtering with instant results

## 🧱 Tech Stack

- **Backend:** Python 3.10+, Flask 3.x, Flask-CORS
- **Database:** PostgreSQL (production), SQLite (local development)
- **ORM:** SQLAlchemy 2.0 with Flask-SQLAlchemy
- **Authentication:** JWT (PyJWT) with token expiry
- **Email:** SMTP with Jinja2 templating
- **Frontend:** HTML5, CSS3, Vanilla JavaScript (no frameworks)
- **Deployment:** Vercel (serverless) with automatic schema migrations

## 📁 Project Structure

```text
Learning_Management_System/
├── backend/
│   ├── app.py                    # Flask app initialization & schema migration
│   ├── database.py               # SQLAlchemy setup & DB URI handling
│   ├── models.py                 # ORM models (User, Course, Lesson, etc.)
│   ├── routes/
│   │   ├── __init__.py
│   │   └── api.py                # All API endpoints
│   └── services/
│       ├── __init__.py
│       ├── auth_service.py       # JWT token generation & verification
│       └── email_service.py      # Email sending & template rendering
├── frontend/
│   ├── index.html                # Public course browsing
│   ├── login.html                # Login with password toggle
│   ├── signup.html               # Student signup with validation
│   ├── dashboard.html            # Student/Admin dashboard with search
│   ├── course.html               # Course details & enrollment
│   ├── lesson.html               # Video lesson player & completion
│   ├── profile.html              # User profile management
│   ├── forgot_password.html      # Password reset request
│   ├── reset_password.html       # New password entry
│   ├── forgot_password_mail.html # Email template for reset
│   ├── course_payment_mail.html  # Email template for payment link
│   └── welcome_*_mail.html       # Welcome email templates
├── static/
│   ├── css/
│   │   └── style.css             # Global styles with responsive design
│   ├── js/
│   │   └── app.js                # Utility functions & shared logic
│   └── img/
│       └── lms-logo.svg
├── database/
│   └── lms.db                    # SQLite database (local only)
├── requirements.txt              # Python dependencies
├── vercel.json                   # Vercel serverless config
└── README.md
```

## 🚀 Quick Start (Windows PowerShell)

### 1. Clone and enter project

```powershell
git clone https://github.com/bikram73/Learning_Management_System.git
cd Learning_Management_System
```

### 2. Create and activate virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

### 4. Set up environment variables

```powershell
Copy-Item .env.example .env
# Edit .env and set:
# - SECRET_KEY (JWT signing key)
# - MAIL_HOST, MAIL_PORT, MAIL_USERNAME, MAIL_PASSWORD (SMTP)
# - MAIL_FROM, SUPPORT_EMAIL (email addresses)
# - DATABASE_URL (PostgreSQL connection in production)
```

### 5. Run the app

```powershell
.\.venv\Scripts\python.exe backend/app.py
```

### 6. Open in browser

- http://127.0.0.1:5000

## 🔐 Authentication & Signup

### Student Signup
- Email must be @gmail.com format (validated client & server)
- Username required
- Password minimum 10 characters
- Password confirmation must match
- Endpoint: POST /api/signup/student

### Admin Signup
- Requires secret admin code: `ADMIN2026`
- Same email/password requirements as students
- Endpoint: POST /api/signup/admin

### Login
- Email and password
- Returns JWT token valid for 7 days
- Endpoint: POST /api/login

### Password Reset
1. Click "Forgot Password?" on login page
2. Enter @gmail.com email address
3. Receive reset email with 1-hour expiring link
4. Set new password and auto-redirect to login
5. Reset links expire after 1 hour
6. Can only request 1 new link per hour (rate limited)

## 📚 Core API Endpoints

### Authentication
- `POST /api/signup/student` - Student registration
- `POST /api/signup/admin` - Admin registration (requires ADMIN2026)
- `POST /api/login` - Login & get JWT token
- `POST /api/logout` - Invalidate session
- `POST /api/forgot-password` - Request password reset email
- `GET /api/reset-password/<token>` - Verify reset token & return user email
- `POST /api/reset-password` - Set new password

### Courses
- `GET /api/courses` - List all courses (public)
- `GET /api/course/<id>` - Get course details
- `POST /api/course` - Create course (admin only)
- `PUT /api/course/<id>` - Update course (owner admin only)
- `DELETE /api/course/<id>` - Delete course (owner admin only)
- `GET /api/my-courses` - Get user's enrolled/created courses

### Lessons
- `GET /api/course/<course_id>/lessons` - Get all lessons for course
- `POST /api/lesson` - Create lesson (owner admin only)
- `PUT /api/lesson/<id>` - Update lesson (owner admin only)
- `DELETE /api/lesson/<id>` - Delete lesson (owner admin only)

### Enrollment & Progress
- `POST /api/enroll` - Enroll in course (student)
- `GET /api/payment/<token>` - Get payment link details
- `POST /api/payment/<token>` - Process payment
- `POST /api/lesson/complete` - Mark lesson as complete
- `GET /api/course-progress/<course_id>` - Get course completion progress

## 🖥️ UI Pages

| Page | Route | Purpose |
|------|-------|---------|
| Home | `/index.html` | Browse all courses with search |
| Signup | `/signup.html` | Student/Admin registration |
| Login | `/login.html` | Authentication with password toggle |
| Dashboard | `/dashboard.html` | Student courses / Admin controls |
| Profile | `/profile.html` | User profile & settings |
| Course | `/course.html?id=<id>` | Course details & enrollment |
| Lesson | `/lesson.html?id=<id>&course=<id>` | Video lesson player |
| Forgot Password | `/forgot_password.html` | Password reset request |
| Reset Password | `/reset_password.html?token=<token>` | New password entry |

## 💳 Paid Courses & Payments

### Creating a Paid Course
1. Login as admin
2. Go to Dashboard > Admin Panel > Create Course
3. Select "Paid" for pricing type
4. Enter course price in USD
5. Courses automatically get thumbnail, title, and description

### Enrolling in Paid Course
1. Click "Open Course" from course card
2. For paid courses, "Enroll" sends payment link to email
3. Click "Pay Now" button in email (valid for 1 hour)
4. Process payment
5. Automatic enrollment upon successful payment
6. If payment link expires, can request new one (1 per hour)

## 🎬 Lesson Video Format

- Videos are embedded in 16:9 aspect ratio containers
- Supports iframe embeds (YouTube, Vimeo, etc.)
- "Next Lesson" button appears after lesson completion
- Students must complete lesson to unlock next one
- Completion marked by clicking "Mark Complete" button

## 🧪 Example Admin Workflow

1. Signup: Go to `/signup.html`, select Admin, enter code `ADMIN2026`
2. Login: Use credentials from signup
3. Create Course: Dashboard > Admin Panel > Create Course
   - Title: "Python Basics"
   - Description: "Learn Python fundamentals"
   - Instructor: "John Doe"
   - Pricing: "Paid" with price "49.99"
   - Thumbnail: Paste image URL
4. Add Lessons: Click course, add lesson with video embed
5. Test Student Path: Logout, signup as student, enroll, complete lessons

## 🛠️ Troubleshooting

### App does not start
```powershell
# Ensure you're using the correct Python interpreter
.\.venv\Scripts\python.exe backend/app.py
```

### Module not found errors
```powershell
# Reinstall dependencies
pip install --upgrade -r requirements.txt
```

### Database column missing error
The app automatically migrates schema when it starts. If you see "column X does not exist":
1. Ensure `DATABASE_URL` is correct
2. App will auto-create missing columns on next startup
3. No manual migration needed

### SMTP email not sending
1. Check `.env` has correct MAIL_HOST, MAIL_USERNAME, MAIL_PASSWORD
2. Gmail requires "App Passwords" for SMTP (not regular password)
3. Verify MAIL_FROM address is authorized to send

### JWT token expired
- Tokens valid for 7 days
- Reset links valid for 1 hour
- Payment links valid for 1 hour
- After expiry, user must login again or request new reset link

### Required Vercel Environment Variables
```
SECRET_KEY=<random-secret>
DATABASE_URL=postgresql://user:pass@host/dbname
MAIL_HOST=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=<app-password>
MAIL_FROM=noreply@lms.com
SUPPORT_EMAIL=support@lms.com
CRON_SECRET=<random-secret>
APP_BASE_URL=https://your-vercel-domain.com
```

## 📝 Git Workflow

```powershell
# Commit changes
git add .
git commit -m "feat: add course search functionality"

# Push to GitHub
git push -u origin main
```

## 🤝 Contributing

1. Create features on feature branches
2. Test locally before pushing
3. Update README for major features
4. Keep code DRY and maintainable

## 📄 License

This project is open-source and available under the MIT License.

If you already created a remote and get an error, verify remotes with:

```powershell
git remote -v
```

## 📌 Future Improvements

- Quiz and assignments
- Certificates
- Discussion forums
- Analytics dashboard enhancements
- Better deployment pipeline (CI/CD)

---

Built for learning and experimentation with full-stack web development.
