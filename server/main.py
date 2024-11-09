import os

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
                "required": ["content", "date", "time"],
                "properties": {
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
    try:
        data = request.json
        content = data.get("content")
        date = data.get("date")
        time = data.get("time")

        if not content or not date or not time:
            return jsonify({"error": "All fields (content, date, and time) are required"}), 400

        reminder = {"content": content, "date": date, "time": time}
        result = remindersCollection.insert_one(reminder)

        return jsonify({"message": "Reminder stored successfully!", "id": str(result.inserted_id)}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

# Route to view reminders
@app.route("/viewReminders", methods=["GET"])
def view_reminder():
    try:
        data = request.args
        date = data.get("date")
        if not date:
            return jsonify({"error": "A valid date is required"}), 400

        reminders = list(remindersCollection.find({"date": date}))
        
        for reminder in reminders:
            reminder["_id"] = str(reminder["_id"])

        return jsonify({"message": "Here are your reminders!", "data": reminders}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Running the Flask app
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))  
    app.run(host="0.0.0.0", port=port, debug=True)



