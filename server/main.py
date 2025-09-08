import os
import logging

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient

# Load environment variables from .env file
load_dotenv()

# Initialize MongoDB client
uri = os.getenv("MONGODB_URI")

client = MongoClient(uri)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Access the cluster and create a collection with validation
db = client["reminder-bot-cluster"]

# Ensure the collection exists or create it with schema validation
if "reminders" not in db.list_collection_names():
    remindersCollection = db.create_collection(
        "reminders",
        validator={
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["user_id", "content", "date", "time"],
                "properties": {
                    "user_id": {
                        "bsonType": "int", 
                        "description": "User ID must be an integer."
                    },
                    "content": {
                        "bsonType": "string",
                        "description": "Reminder content must be a string."
                    },
                    "date": {
                        "bsonType": "string",
                        "description": "Date must be a string in YYYY-MM-DD format."
                    },
                    "time": {
                        "bsonType": "string",
                        "description": "Time must be a string in HH:MM format."
                    }
                }
            }
        }
    )
else:
    remindersCollection = db["reminders"]

# Route to store reminders
@app.route("/storeReminders", methods=["POST"])
def store_reminder():
    """Stores a new reminder in the MongoDB database.

    This endpoint expects a JSON payload with user_id, content, date, and time.
    It inserts the data into the 'reminders' collection.

    Returns:
        A JSON response with a success message and the reminder's ID (status 201),
        or an error message if the data is invalid (status 400) or a server error occurs (status 500).
    """
    try:
        data = request.json
        user_id = int(data.get("user_id"))
        content = data.get("content")
        date = data.get("date")
        time = data.get("time")

        if not user_id or not content or not date or not time:
            return jsonify({"error": "All fields (user_id, content, date, and time) are required"}), 400

        reminder = {"user_id": user_id, "content": content, "date": date, "time": time}
        result = remindersCollection.insert_one(reminder)

        return jsonify({"message": "Reminder stored successfully!", "id": str(result.inserted_id)}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

logging.basicConfig(level=logging.INFO)

@app.route("/viewReminders", methods=["GET"])
def view_reminders():
    """Fetches reminders for a specific user and date.

    This endpoint expects 'user_id' and 'date' as query parameters.
    It queries the database and returns a list of all matching reminders.

    Returns:
        A JSON response containing the list of reminders (status 200), or an
        error message if parameters are missing (status 400) or a server error occurs (status 500).
    """
    try:
        user_id = int(request.args.get("user_id"))  # Convert user_id to integer
        date = request.args.get("date")

        # Validate required parameters
        if not user_id or not date:
            return jsonify({"error": "Both user_id and date are required"}), 400

        # Query reminders based on user_id and date
        reminders = list(remindersCollection.find({"user_id": user_id, "date": date}))

        # Convert ObjectId to string
        for reminder in reminders:
            reminder["_id"] = str(reminder["_id"])

        # Log fetched reminders
        logging.info(f"Fetched reminders for user_id {user_id} and date {date}: {reminders}")

        return jsonify({"data": reminders}), 200
    except Exception as e:
        logging.error(f"Error occurred while fetching reminders: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/", methods=["GET", "HEAD"])
def health_check():
    """Provides a simple health check for the API.

    This endpoint returns a 200 status code to indicate the service is running.
    """
    if request.method == "HEAD":
        return "", 200
    elif request.method == "GET":
        return jsonify({"message": "Reminder Bot API is running!"}), 200

# Running the Flask app
if __name__ == "__main__":
    """Main entry point for the Flask application.

    This block runs the Flask development server, listening on the specified port.
    """
    port = int(os.environ.get("PORT", 10000))  
    app.run(host="0.0.0.0", port=port, debug=True)
