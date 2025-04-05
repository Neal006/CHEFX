from flask import Flask, redirect, render_template, request, make_response, session, abort, jsonify, url_for
from flask_cors import CORS, cross_origin
from flask_session import Session
import secrets
from functools import wraps
import firebase_admin
from firebase_admin import credentials, firestore, auth
from datetime import timedelta, datetime
import os, re, json
from dotenv import load_dotenv
from tutorials import RecipeTutorialFinder, QuotaExceededException
from aimeasurement import DynamicKitchenConverter
import google.generativeai as genai
from cleanedtext import clean_dynamic_text
# Load environment variables
load_dotenv()

# Get API keys from environment variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
SECRET_KEY = os.getenv('SECRET_KEY')

if not all([GEMINI_API_KEY, YOUTUBE_API_KEY, SECRET_KEY]):
    raise ValueError("Missing required environment variables. Please check your .env file.")

finder = RecipeTutorialFinder(YOUTUBE_API_KEY)
converter = DynamicKitchenConverter(GEMINI_API_KEY)

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Configure CORS with credentials support
CORS(app, supports_credentials=True, resources={
    r"/*": {"origins": "*", 
           "methods": ["GET", "POST", "OPTIONS"],
           "allow_headers": ["Content-Type", "Authorization"]}
})

# Ensure session directory exists
session_dir = './flask_session'
if not os.path.exists(session_dir):
    os.makedirs(session_dir)

# Configure Flask-Session for server-side storage
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = True
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_FILE_DIR'] = session_dir
app.config['SESSION_FILE_THRESHOLD'] = 500  # Maximum number of sessions stored
app.config['SESSION_FILE_MODE'] = 0o600  # More secure file permissions

# Configure session cookie settings
app.config['SESSION_COOKIE_SECURE'] = True  # Only send over HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JavaScript access
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)  # Longer session lifetime
app.config['SESSION_REFRESH_EACH_REQUEST'] = True  # Keep session fresh
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Prevent CSRF 

# Initialize Flask-Session
Session(app)

# Firebase Admin SDK setup
cred = credentials.Certificate("firebase-auth.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

def get_user_stats(user_id):
    """Get user's feature usage stats from Firestore"""
    try:
        doc_ref = db.collection('user_stats').document(user_id)
        doc = doc_ref.get()
        if doc.exists:
            return doc.to_dict()
        else:
            # Initialize stats if they don't exist
            default_stats = {
                'measurements_converted': 0,
                'recipes_generated': 0,
                'tutorials_watched': 0,
                'last_updated': datetime.now().isoformat()
            }
            doc_ref.set(default_stats)
            return default_stats
    except Exception as e:
        app.logger.error(f"Error getting user stats: {str(e)}")
        return None

def increment_user_stat(user_id, stat_name):
    """Increment a specific stat for the user"""
    try:
        doc_ref = db.collection('user_stats').document(user_id)
        doc_ref.set({
            stat_name: firestore.Increment(1),
            'last_updated': datetime.now().isoformat()
        }, merge=True)
        return True
    except Exception as e:
        app.logger.error(f"Error incrementing user stat: {str(e)}")
        return False

# Helper function to check if session is valid
def is_session_valid():
    if 'user' not in session:
        return False
    
    # Check if session has expiry time
    if 'expires_at' not in session:
        return False
    
    # Check if session has expired
    expires_at = datetime.fromisoformat(session['expires_at'])
    if datetime.now() > expires_at:
        return False
    
    return True

########################################
""" Authentication and Authorization """

# Decorator for routes that require authentication
def auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is authenticated
        if not is_session_valid():
            # Clear any invalid session
            session.clear()
            return redirect(url_for('login'))
        
        # Refresh session expiry
        session['expires_at'] = (datetime.now() + app.config['PERMANENT_SESSION_LIFETIME']).isoformat()
        return f(*args, **kwargs)
        
    return decorated_function


@app.route('/auth', methods=['POST'])
def authorize():
    token = request.headers.get('Authorization')
    if not token or not token.startswith('Bearer '):
        return jsonify({"error": "Missing or invalid authorization header"}), 401

    token = token[7:]  # Strip off 'Bearer '

    try:
        # Validate token and check if revoked
        decoded_token = auth.verify_id_token(token, check_revoked=True, clock_skew_seconds=60)
        
        # Create session with limited user data
        session.clear()  # Clear any existing session first
        session['user'] = {
            'uid': decoded_token['uid'],
            'email': decoded_token.get('email', ''),
            'name': decoded_token.get('name', '')
        }
        session.permanent = True
        
        # Set session expiry
        session['expires_at'] = (datetime.now() + app.config['PERMANENT_SESSION_LIFETIME']).isoformat()
        
        # Set last activity timestamp
        session['last_activity'] = datetime.now().isoformat()
        
        return jsonify({"message": "Authentication successful"}), 200
    
    except auth.RevokedIdTokenError:
        return jsonify({"error": "Token has been revoked. Please reauthenticate"}), 401
    except auth.ExpiredIdTokenError:
        return jsonify({"error": "Token has expired. Please reauthenticate"}), 401
    except auth.InvalidIdTokenError:
        return jsonify({"error": "Invalid token"}), 401
    except Exception as e:
        app.logger.error(f"Authentication error: {str(e)}")
        return jsonify({"error": "Authentication failed"}), 401


#####################
""" Public Routes """

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login')
def login():
    if is_session_valid():
        return redirect(url_for('dashboard'))
    else:
        session.clear()
        return render_template('login.html')

@app.route('/signup')
def signup():
    if is_session_valid():
        return redirect(url_for('dashboard'))
    else:
        session.clear()
        return render_template('signup.html')

@app.route('/reset-password')
def reset_password():
    if is_session_valid():
        return redirect(url_for('dashboard'))
    else:
        session.clear()
        return render_template('forgot_password.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/aboutus')
def aboutus():
    return render_template('aboutus.html')

@app.route('/logout')
def logout():
    try:
        # Get user data for logging
        user_data = session.get('user', {})
        user_id = user_data.get('uid', 'unknown')
        
        # Log the logout
        app.logger.info(f"User {user_id} logged out")
        
        # Clear the session completely
        session.clear()
        
        # Create response with redirect
        response = make_response(redirect(url_for('home')))
        
        # Explicitly set cookie expiration for all cookies
        for cookie in request.cookies:
            response.delete_cookie(cookie)
        
        return response
    except Exception as e:
        app.logger.error(f"Logout error: {str(e)}")
        # Force redirect even if there's an error
        session.clear()
        return redirect(url_for('home'))


##############################################
""" Private Routes (Require authorization) """

@app.route('/dashboard')
@auth_required
def dashboard():
    try:
        user_data = session.get('user', {})
        user_id = user_data.get('uid')
        user_stats = get_user_stats(user_id)
        session['last_activity'] = datetime.now().isoformat()
        return render_template('dashboard.html', user=user_data, stats=user_stats)
    except Exception as e:
        app.logger.error(f"Dashboard error: {str(e)}")
        return redirect(url_for('login'))

@app.route('/search', methods=['GET', 'POST'])
@auth_required
def tutorial():
    if request.method == 'POST':
        recipe = request.form.get('recipe')
        if not recipe:
            return jsonify({'error': 'No recipe provided'}), 400
        videos = finder.search_videos(recipe)
        user_id = session.get('user', {}).get('uid')
        if user_id and videos:
            store_tutorial_history(user_id, recipe, videos)
            increment_user_stat(user_id, 'tutorials_watched')
        return jsonify({
            'videos': videos,
            'history': get_user_history(user_id, 'tutorial_history', 'searches') if user_id else []
        })
    else:
        user_id = session.get('user', {}).get('uid')
        history = get_user_history(user_id, 'tutorial_history', 'searches') if user_id else []
        return render_template('tutorial.html', history=history)
    
@app.route("/api/convert", methods=["POST"])
@cross_origin()
@auth_required
def convert_measurement():
    """API endpoint to convert measurements using AI"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        measurement = data.get("measurement")
        ingredient = data.get("ingredient")

        if not measurement or not ingredient:
            return jsonify({"error": "Measurement and ingredient are required"}), 400

        if len(measurement) > 100 or len(ingredient) > 100:
            return jsonify({"error": "Input too long. Maximum length is 100 characters"}), 400

        # Initialize converter with API key
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            app.logger.error("Missing GEMINI_API_KEY environment variable")
            return jsonify({"error": "Service configuration error"}), 500
            
        converter = DynamicKitchenConverter(api_key)
        result = converter.convert_measurement(measurement, ingredient)
        
        # Store measurement history and increment stats
        user_id = session.get('user', {}).get('uid')
        if user_id:
            store_measurement_history(user_id, measurement, ingredient, result)
            increment_user_stat(user_id, 'measurements_converted')
            
        return jsonify(result)

    except ValueError as e:
        app.logger.warning(f"Validation error: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        app.logger.error(f"Conversion error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    
@app.route('/aimeasure', methods=['GET', 'POST'])
@auth_required
def aimeasure():
    user_id = session.get('user', {}).get('uid')
    history = get_user_history(user_id, 'measurement_history', 'conversions') if user_id else []
    return render_template('aimeasure.html', history=history)

@app.route('/ai', methods=['GET', 'POST'])
@auth_required
def AI():
    return render_template('AI.html')

@app.route('/chat', methods=['POST'])
@auth_required
def chat():
    content_type = request.headers.get('Content-Type', '')
    if 'application/json' not in content_type:
        return jsonify({
            "error": "Unsupported Media Type",
            "message": "Content-Type must be 'application/json'",
            "received": content_type
        }), 415

    try:
        data = request.get_json()
        if data is None:
            return jsonify({"error": "Invalid JSON format"}), 400

        user_message = data.get("message")
        if not user_message:
            return jsonify({"error": "Message field is required"}), 400

        if len(user_message) > 500:
            return jsonify({"error": "Message too long. Maximum length is 500 characters"}), 400

        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        prompt = f'''Create a detailed recipe for "{user_message}" following this exact format:

# {user_message}

[Brief 2-3 sentence introduction about the dish, its origin, and what makes it special]

## Preparation Time
- Prep Time: [time]
- Cook Time: [time]
- Total Time: [time]
- Servings: [number]

## Ingredients
[List all ingredients with precise measurements in both metric and imperial units]
- First ingredient
- Second ingredient
[etc.]

## Instructions
1. [First step with clear, detailed instruction]
2. [Second step]
[Continue with numbered steps]

## Tips and Notes
- [Important tips about technique]
- [Storage recommendations]
- [Possible variations]
- [Common mistakes to avoid]

## Nutrition Information (Per Serving)
- Calories: [number] kcal
- Protein: [number]g
- Carbohydrates: [number]g
- Fat: [number]g

Please ensure all measurements are precise and instructions are clear and detailed.'''
        
        try:
            response = model.generate_content(prompt)
            if not response or not response.text:
                raise ValueError("No response from AI model")
            
            formatted_response = clean_dynamic_text(response.text)
            
            # Store chat history
            user_id = session.get('user', {}).get('uid')
            if user_id:
                store_chat_history(user_id, user_message, formatted_response)
                increment_user_stat(user_id, 'recipes_generated')
                
            return jsonify({
                "response": formatted_response,
                "history": get_user_history(user_id, 'chat_history', 'messages') if user_id else []
            })
            
        except Exception as e:
            app.logger.error(f"AI generation error: {str(e)}")
            return jsonify({"error": "Failed to generate response"}), 500

    except Exception as e:
        app.logger.error(f"Chat endpoint error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/validate_session', methods=['POST'])
@auth_required
def validate_session():
    """Endpoint to validate and refresh the session"""
    try:
        # Get the current user data
        user_data = session.get('user', {})
        user_id = user_data.get('uid')
        
        # Get user stats
        user_stats = get_user_stats(user_id)
        
        # Update last activity timestamp
        session['last_activity'] = datetime.now().isoformat()
        
        # Refresh session expiry
        session['expires_at'] = (datetime.now() + app.config['PERMANENT_SESSION_LIFETIME']).isoformat()
        
        return jsonify({
            "valid": True,
            "user": {
                "uid": user_data.get('uid'),
                "email": user_data.get('email'),
                "name": user_data.get('name')
            },
            "stats": user_stats,
            "expires_at": session['expires_at']
        }), 200
    except Exception as e:
        app.logger.error(f"Session validation error: {str(e)}")
        return jsonify({"valid": False, "error": "Session validation failed"}), 401

# Add routes to get history
@app.route('/api/history/<collection>', methods=['GET'])
@cross_origin()
@auth_required
def get_history(collection):
    """Get user's history for a specific collection"""
    try:
        # Get user ID from session correctly
        user_id = session.get('user', {}).get('uid')
        if not user_id:
            return jsonify({'error': 'User not authenticated'}), 401

        # Map collection names to their Firestore paths and subcollections
        collection_map = {
            'measurements': ('measurement_history', 'conversions'),
            'recipes': ('chat_history', 'messages'),
            'tutorials': ('tutorial_history', 'searches')
        }

        if collection not in collection_map:
            return jsonify({'error': 'Invalid collection type'}), 400

        # Get history from Firestore using the correct collection and subcollection
        collection_name, subcollection = collection_map[collection]
        history = get_user_history(user_id, collection_name, subcollection)
        return jsonify(history)

    except Exception as e:
        app.logger.error(f"Error fetching history: {str(e)}")
        return jsonify({'error': 'Failed to fetch history'}), 500

def get_user_history(user_id, collection_name, subcollection, limit=10):
    """Retrieve user history from a specific collection"""
    try:
        history_ref = db.collection(collection_name).document(user_id).collection(subcollection)
        query = history_ref.order_by('timestamp', direction=firestore.Query.DESCENDING).limit(limit)
        
        history = []
        for doc in query.stream():
            data = doc.to_dict()
            # Convert timestamp to ISO format for JSON serialization
            if 'timestamp' in data and data['timestamp']:
                data['timestamp'] = data['timestamp'].isoformat()
            history.append(data)
            
        return history
    except Exception as e:
        app.logger.error(f"Error retrieving history: {str(e)}")
        return []

def store_chat_history(user_id, message, response):
    """Store chat history in Firestore"""
    try:
        chat_ref = db.collection('chat_history').document(user_id).collection('messages')
        chat_ref.add({
            'message': message,
            'response': response,
            'timestamp': firestore.SERVER_TIMESTAMP
        })
        return True
    except Exception as e:
        app.logger.error(f"Error storing chat history: {str(e)}")
        return False

def store_measurement_history(user_id, measurement, ingredient, result):
    """Store measurement conversion history in Firestore"""
    try:
        measure_ref = db.collection('measurement_history').document(user_id).collection('conversions')
        measure_ref.add({
            'measurement': measurement,
            'ingredient': ingredient,
            'result': result,
            'timestamp': firestore.SERVER_TIMESTAMP
        })
        return True
    except Exception as e:
        app.logger.error(f"Error storing measurement history: {str(e)}")
        return False

def store_tutorial_history(user_id, recipe, videos):
    """Store tutorial search history in Firestore"""
    try:
        tutorial_ref = db.collection('tutorial_history').document(user_id).collection('searches')
        tutorial_ref.add({
            'recipe': recipe,
            'videos': videos,
            'timestamp': firestore.SERVER_TIMESTAMP
        })
        return True
    except Exception as e:
        app.logger.error(f"Error storing tutorial history: {str(e)}")
        return False

if __name__ == '__main__':
    app.run(debug=True)