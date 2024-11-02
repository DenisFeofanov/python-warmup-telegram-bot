import sqlite3
from datetime import datetime

class Database:
    def __init__(self):
        self.conn = sqlite3.connect('workout.db', check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        
        # Create challenges table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS challenges (
                user_id INTEGER,
                exercise TEXT,
                target_reps INTEGER,
                PRIMARY KEY (user_id, exercise)
            )
        ''')

        # Create completed exercises table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS completed_exercises (
                user_id INTEGER,
                exercise TEXT,
                reps INTEGER,
                date DATE,
                PRIMARY KEY (user_id, exercise, date)
            )
        ''')
        
        self.conn.commit()

    def set_challenge(self, user_id, exercise, target_reps):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO challenges (user_id, exercise, target_reps)
            VALUES (?, ?, ?)
        ''', (user_id, exercise, target_reps))
        self.conn.commit()

    def get_challenges(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT exercise, target_reps FROM challenges WHERE user_id = ?', (user_id,))
        return cursor.fetchall()

    def mark_exercise_complete(self, user_id, exercise, reps):
        today = datetime.now().date()
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO completed_exercises (user_id, exercise, reps, date)
            VALUES (?, ?, ?, ?)
        ''', (user_id, exercise, reps, today))
        self.conn.commit()

    def get_incomplete_exercises(self, user_id):
        today = datetime.now().date()
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT c.exercise, c.target_reps
            FROM challenges c
            LEFT JOIN completed_exercises e 
                ON c.user_id = e.user_id 
                AND c.exercise = e.exercise 
                AND e.date = ?
            WHERE c.user_id = ? AND e.exercise IS NULL
        ''', (today, user_id))
        return cursor.fetchall() 