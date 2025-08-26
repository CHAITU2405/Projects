#!/usr/bin/env python3
"""
Database setup script for Online Exam System
This script creates sample questions and a student user for testing purposes.
"""

from app import app, db, User, Question
from werkzeug.security import generate_password_hash
from datetime import datetime

def create_sample_data():
    """Create sample questions and student user"""
    
    with app.app_context():
        # Create student user
        student = User.query.filter_by(username='student1').first()
        if not student:
            student = User(
                username='student1',
                email='student1@exam.com',
                password_hash=generate_password_hash('student123'),
                role='student',
                domain='web_dev'
            )
            db.session.add(student)
            print("✓ Created student user: student1 / student123")
        
        # Sample questions for Web Development
        web_dev_questions = [
            {
                'question_text': 'What does HTML stand for?',
                'option_a': 'Hyper Text Markup Language',
                'option_b': 'High Tech Modern Language',
                'option_c': 'Home Tool Markup Language',
                'option_d': 'Hyperlink and Text Markup Language',
                'correct_answer': 'A'
            },
            {
                'question_text': 'Which CSS property controls the text size?',
                'option_a': 'font-style',
                'option_b': 'text-size',
                'option_c': 'font-size',
                'option_d': 'text-style',
                'correct_answer': 'C'
            },
            {
                'question_text': 'How do you write "Hello World" in an alert box?',
                'option_a': 'msg("Hello World")',
                'option_b': 'alertBox("Hello World")',
                'option_c': 'msgBox("Hello World")',
                'option_d': 'alert("Hello World")',
                'correct_answer': 'D'
            },
            {
                'question_text': 'Which HTML element is used to specify a footer for a document or section?',
                'option_a': '<footer>',
                'option_b': '<bottom>',
                'option_c': '<section>',
                'option_d': '<div>',
                'correct_answer': 'A'
            },
            {
                'question_text': 'What is the correct way to write a JavaScript array?',
                'option_a': 'var colors = 1 = ("red") 2 = ("green") 3 = ("blue")',
                'option_b': 'var colors = ["red", "green", "blue"]',
                'option_c': 'var colors = (1:"red", 2:"green", 3:"blue")',
                'option_d': 'var colors = "red", "green", "blue"',
                'correct_answer': 'B'
            }
        ]
        
        # Sample questions for Machine Learning
        ml_questions = [
            {
                'question_text': 'What is supervised learning?',
                'option_a': 'Learning without any guidance',
                'option_b': 'Learning with labeled training data',
                'option_c': 'Learning through trial and error',
                'option_d': 'Learning from unlabeled data',
                'correct_answer': 'B'
            },
            {
                'question_text': 'Which algorithm is used for classification problems?',
                'option_a': 'Linear Regression',
                'option_b': 'Logistic Regression',
                'option_c': 'K-Means Clustering',
                'option_d': 'Principal Component Analysis',
                'correct_answer': 'B'
            },
            {
                'question_text': 'What is overfitting in machine learning?',
                'option_a': 'When a model performs well on training data but poorly on new data',
                'option_b': 'When a model is too simple to capture patterns',
                'option_c': 'When a model has too few parameters',
                'option_d': 'When a model is perfectly balanced',
                'correct_answer': 'A'
            },
            {
                'question_text': 'Which of the following is NOT a type of machine learning?',
                'option_a': 'Supervised Learning',
                'option_b': 'Unsupervised Learning',
                'option_c': 'Reinforcement Learning',
                'option_d': 'Static Learning',
                'correct_answer': 'D'
            },
            {
                'question_text': 'What is the purpose of cross-validation?',
                'option_a': 'To increase the dataset size',
                'option_b': 'To evaluate model performance on unseen data',
                'option_c': 'To reduce computational cost',
                'option_d': 'To speed up training',
                'correct_answer': 'B'
            }
        ]
        
        # Sample questions for Data Science
        ds_questions = [
            {
                'question_text': 'What is the primary purpose of data visualization?',
                'option_a': 'To make data look pretty',
                'option_b': 'To communicate insights effectively',
                'option_c': 'To reduce data size',
                'option_d': 'To encrypt data',
                'correct_answer': 'B'
            },
            {
                'question_text': 'Which statistical measure indicates the spread of data?',
                'option_a': 'Mean',
                'option_b': 'Median',
                'option_c': 'Standard Deviation',
                'option_d': 'Mode',
                'correct_answer': 'C'
            },
            {
                'question_text': 'What is the purpose of exploratory data analysis (EDA)?',
                'option_a': 'To make final conclusions',
                'option_b': 'To understand data patterns and relationships',
                'option_c': 'To clean data only',
                'option_d': 'To visualize data only',
                'correct_answer': 'B'
            },
            {
                'question_text': 'Which Python library is commonly used for data manipulation?',
                'option_a': 'Matplotlib',
                'option_b': 'Pandas',
                'option_c': 'Scikit-learn',
                'option_d': 'TensorFlow',
                'correct_answer': 'B'
            },
            {
                'question_text': 'What is correlation in statistics?',
                'option_a': 'A measure of causation between variables',
                'option_b': 'A measure of the strength of relationship between variables',
                'option_c': 'A measure of the mean of variables',
                'option_d': 'A measure of the variance of variables',
                'correct_answer': 'B'
            }
        ]
        
        # Add questions to database
        domains_questions = [
            ('web_dev', web_dev_questions),
            ('ml', ml_questions),
            ('data_science', ds_questions)
        ]
        
        for domain, questions in domains_questions:
            existing_count = Question.query.filter_by(domain=domain).count()
            if existing_count == 0:
                for q_data in questions:
                    question = Question(
                        domain=domain,
                        question_text=q_data['question_text'],
                        option_a=q_data['option_a'],
                        option_b=q_data['option_b'],
                        option_c=q_data['option_c'],
                        option_d=q_data['option_d'],
                        correct_answer=q_data['correct_answer']
                    )
                    db.session.add(question)
                print(f"✓ Added {len(questions)} questions for {domain.replace('_', ' ').title()}")
            else:
                print(f"✓ {domain.replace('_', ' ').title()} questions already exist ({existing_count} questions)")
        
        # Commit all changes
        db.session.commit()
        print("\n✓ Database setup completed successfully!")
        print("\nSample credentials:")
        print("Admin: admin / admin123")
        print("Student: student1 / student123")
        print("\nYou can now run the application with: python app.py")

if __name__ == '__main__':
    create_sample_data()
