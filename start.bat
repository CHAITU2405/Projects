@echo off
echo Starting Online Exam System...
echo.
echo Installing dependencies...
pip install -r requirements.txt
echo.
echo Setting up database...
python setup_db.py
echo.
echo Starting the application...
echo.
echo The exam system will be available at: http://localhost:5000
echo.
echo Default credentials:
echo Admin: admin / admin123
echo Student: student1 / student123
echo.
echo Press Ctrl+C to stop the server
echo.
python app.py
pause
