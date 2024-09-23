from pymongo import MongoClient
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv




##intialise connection to mongodb
load_dotenv()
uri = os.getenv("MONGODB_URI")
client = MongoClient(uri)

##initialise flask app 
app = Flask(__name__)
CORS(app)  

##access cluster and collection
dataBase = client["reminder-bot-cluster"]
remindersCollection = dataBase.create_collection(
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
    })

##Store reminders
@app.route("/storeReminders", methods=["POST"])

def store_reminder():
    try:
        data = request.json
        content = data.get("content")
        date = data.get("date")
        time = data.get("time")

        if not content or not date or not time:
            return jsonify({
                "error": "All fields (content, date, and time) are required"}), 400
        

        reminder = {
            "content": content,
            "date": date,
            "time": time
        }

        result = remindersCollection.insert_one(reminder)
        
        return jsonify({"message": "Reminder stored successfully!", "id": str(result.inserted_id)}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


##View reminders


if __name__ == "__main__":
    app.run(debug=True)
