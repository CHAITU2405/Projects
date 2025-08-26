# Online Exam System

A comprehensive web-based examination platform built with Flask, featuring secure exam taking, tab switching prevention, automatic timing, and role-based access control.

## Features

### 🔐 Security Features
- **Tab Switching Prevention**: Students cannot switch tabs during exams
- **30-Minute Timer**: Automatic exam submission when time expires
- **Session Management**: Secure user authentication and authorization
- **Anti-Cheating Measures**: Multiple tab switching attempts are logged

### 👥 User Management
- **Admin Role**: Create questions, manage domains, view results
- **Student Role**: Take exams, view results, track performance
- **Separate Logins**: Easy verification and management per domain

### 📚 Domain Support
- **Web Development**: HTML, CSS, JavaScript, modern web technologies
- **Machine Learning**: Algorithms, statistics, ML frameworks
- **Data Science**: Data analysis, visualization, statistical methods

### 📊 Analytics & Reporting
- **Real-time Results**: Immediate scoring and feedback
- **Performance Analytics**: Detailed performance breakdowns
- **Admin Dashboard**: Comprehensive overview of all exam results
- **Export Capabilities**: Download results for further analysis

## Technology Stack

- **Backend**: Flask (Python)
- **Database**: SQLite with SQLAlchemy ORM
- **Frontend**: Bootstrap 5, HTML5, CSS3, JavaScript
- **Authentication**: Flask-Login with password hashing
- **Security**: Session management, CSRF protection

## Installation & Setup

### Prerequisites
- Python 3.7 or higher
- pip (Python package installer)

### Step 1: Clone/Download
```bash
# If using git
git clone <repository-url>
cd Exam

# Or download and extract the files
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Setup Database
```bash
python setup_db.py
```

### Step 4: Run the Application
```bash
python app.py
```

The application will be available at `http://localhost:5000`

## Default Credentials

### Admin Access
- **Username**: `admin`
- **Password**: `admin123`
- **Capabilities**: Manage questions, view all results, system administration

### Student Access
- **Username**: `student1`
- **Password**: `student123`
- **Capabilities**: Take exams, view personal results

## Usage Guide

### For Administrators

1. **Login** with admin credentials
2. **Dashboard**: Overview of all domains and system statistics
3. **Manage Questions**: Add/edit questions for each domain
4. **View Results**: Monitor student performance across all domains
5. **Analytics**: Track performance trends and identify areas for improvement

### For Students

1. **Login** with student credentials
2. **Select Domain**: Choose from Web Development, ML, or Data Science
3. **Take Exam**: 30-minute timed assessment with multiple-choice questions
4. **View Results**: Immediate feedback with detailed performance analysis
5. **Track Progress**: Monitor performance across different domains

## Exam Features

### Security Measures
- **Tab Switching Detection**: Alerts and logs when students attempt to switch tabs
- **Automatic Submission**: Exams submit automatically when time expires
- **Session Validation**: Prevents unauthorized access and multiple sessions
- **Keyboard Shortcut Prevention**: Blocks common navigation shortcuts

### User Experience
- **Responsive Design**: Works on desktop, tablet, and mobile devices
- **Real-time Timer**: Countdown display with visual alerts
- **Progress Tracking**: Clear indication of answered vs. unanswered questions
- **Immediate Feedback**: Instant scoring and detailed explanations

## File Structure

```
Exam/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── setup_db.py           # Database initialization script
├── README.md             # This file
├── templates/            # HTML templates
│   ├── base.html         # Base template with navigation
│   ├── index.html        # Home page
│   ├── login.html        # Login form
│   ├── admin_dashboard.html      # Admin main page
│   ├── admin_questions.html     # Question management
│   ├── add_question.html        # Add question form
│   ├── student_dashboard.html   # Student main page
│   ├── take_exam.html           # Exam interface
│   ├── exam_results.html        # Student results
│   └── admin_results.html       # Admin results overview
└── exam.db               # SQLite database (created automatically)
```

## Database Schema

### Users Table
- `id`: Primary key
- `username`: Unique username
- `email`: User email address
- `password_hash`: Encrypted password
- `role`: 'admin' or 'student'
- `domain`: User's primary domain (optional)
- `created_at`: Account creation timestamp

### Questions Table
- `id`: Primary key
- `domain`: Question domain (web_dev, ml, data_science)
- `question_text`: The question content
- `option_a/b/c/d`: Multiple choice options
- `correct_answer`: Correct option (A, B, C, or D)
- `created_at`: Question creation timestamp

### Exam Sessions Table
- `id`: Primary key
- `user_id`: Reference to user
- `domain`: Exam domain
- `start_time`: Exam start timestamp
- `end_time`: Exam end timestamp
- `is_completed`: Completion status
- `score`: Number of correct answers
- `total_questions`: Total questions in exam

### Exam Responses Table
- `id`: Primary key
- `exam_session_id`: Reference to exam session
- `question_id`: Reference to question
- `user_answer`: Student's selected answer
- `is_correct`: Whether answer is correct
- `answered_at`: Answer timestamp

## Customization

### Adding New Domains
1. Update the `domains` list in `app.py`
2. Add domain-specific styling in templates
3. Create sample questions for the new domain
4. Update navigation and routing

### Modifying Exam Duration
1. Change the `timedelta(minutes=30)` in `start_exam()` function
2. Update the JavaScript timer in `take_exam.html`
3. Adjust the auto-submit timeout

### Styling Changes
1. Modify CSS in `base.html` and individual templates
2. Update Bootstrap classes for different color schemes
3. Customize icons and visual elements

## Security Considerations

### Current Security Features
- Password hashing using Werkzeug
- Session-based authentication
- Tab switching detection and prevention
- Automatic session timeout
- CSRF protection

### Recommended Enhancements
- HTTPS implementation for production
- Rate limiting for login attempts
- IP address logging and restrictions
- Advanced anti-cheating measures
- Database encryption

## Troubleshooting

### Common Issues

1. **Database Errors**
   - Ensure `setup_db.py` has been run
   - Check file permissions for `exam.db`
   - Verify SQLite is properly installed

2. **Template Errors**
   - Check that all template files are in the `templates/` directory
   - Verify Jinja2 syntax in templates
   - Ensure proper template inheritance

3. **Login Issues**
   - Verify credentials are correct
   - Check that the database contains user records
   - Ensure Flask-Login is properly configured

4. **Exam Timer Issues**
   - Check JavaScript console for errors
   - Verify browser supports required JavaScript features
   - Ensure no conflicting JavaScript libraries

### Performance Optimization
- Use a production WSGI server (Gunicorn, uWSGI)
- Implement database connection pooling
- Add caching for frequently accessed data
- Optimize database queries

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source and available under the [MIT License](LICENSE).

## Support

For questions or issues:
1. Check the troubleshooting section above
2. Review the code comments and documentation
3. Create an issue in the repository
4. Contact the development team

## Future Enhancements

- [ ] Real-time proctoring with webcam
- [ ] Advanced question types (essay, coding)
- [ ] Integration with learning management systems
- [ ] Mobile app development
- [ ] Advanced analytics and reporting
- [ ] Multi-language support
- [ ] Cloud deployment options
- [ ] API endpoints for external integrations

---

**Note**: This system is designed for educational purposes and should be deployed in a secure environment for production use.
