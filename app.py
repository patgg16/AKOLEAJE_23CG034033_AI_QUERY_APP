import os
import sqlite3
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, g
from google import genai # Library for Gemini AI

# Load environment variables (API key) from .env file
load_dotenv()

app = Flask(__name__)

# --- Database Setup (SQLite) ---
DATABASE = 'queries.db' # The database file name [cite: 13]

def get_db():
    """Connects to the specific database."""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        # Use sqlite3.Row objects for dict-like access
        db.row_factory = sqlite3.Row 
    return db

def init_db():
    """Initializes the database table if it doesn't exist."""
    with app.app_context():
        db = get_db()
        # Create a table to store the queries
        db.execute('''
            CREATE TABLE IF NOT EXISTS queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        db.commit()

# Ensure the database is initialized when the app starts
init_db()

@app.teardown_appcontext
def close_connection(exception):
    """Closes the database connection at the end of the request."""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# --- Gemini AI Configuration ---
# Get API key from environment variables (important for local and Render deployment)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") 

if not GEMINI_API_KEY:
    print("FATAL ERROR: GEMINI_API_KEY not found. Check .env and Render variables.")

# Initialize the Gemini client
try:
    client = genai.Client(api_key=GEMINI_API_KEY)
except Exception as e:
    # Handle case where API key is missing or invalid on startup
    print(f"Error initializing Gemini client: {e}")

# --- Flask Routes ---

@app.route('/')
def index():
    """Serves the main HTML page to the user."""
    # Renders the templates/index.html file 
    return render_template('index.html') 

@app.route('/api/query', methods=['POST'])
def handle_query():
    """Receives the question, queries the AI, and returns the answer."""
    data = request.get_json()
    user_question = data.get('question', '').strip()

    if not user_question:
        return jsonify({"error": "No question provided."}), 400

    print(f"Received question: {user_question}")
    
    ai_answer = ""
    
    try:
        # Call the external AI API 
        response = client.models.generate_content(
            model='gemini-2.5-flash', # A good model for quick chat-like responses
            contents=user_question
        )
        ai_answer = response.text
        
        # Store the query and answer in the database [cite: 32]
        db = get_db()
        db.execute(
            "INSERT INTO queries (question, answer) VALUES (?, ?)", 
            (user_question, ai_answer)
        )
        db.commit()
        
        print("Query saved to database.")

        # Send the AI's answer back to the frontend 
        return jsonify({"answer": ai_answer})

    except Exception as e:
        print(f"Error during AI query or database operation: {e}")
        return jsonify({"error": "An error occurred while contacting the AI."}), 500

if __name__ == '__main__':
    # Flask's built-in development server
    # Note: Render uses gunicorn, not this section 
    app.run(debug=True)