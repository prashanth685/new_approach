from pymongo import MongoClient, ASCENDING
import datetime
from bson.objectid import ObjectId
import logging
import re

class Database:
    def __init__(self, connection_string="mongodb://localhost:27017/", email="user@example.com"):
        self.connection_string = connection_string
        self.email = email
        self.email_safe = email.replace('@', '_').replace('.', '_')
        self.client = None
        self.db = None
        self.projects_collection = None
        self.messages_collection = None
        self.timeview_collection = None
        self.projects = []
        self.connect()

    def connect(self):
        try:
            self.client = MongoClient(self.connection_string, serverSelectionTimeoutMS=5000)
            self.client.server_info()  # Test connection
            self.db = self.client["changed_db"]
            self.projects_collection = self.db["projects"]
            self.messages_collection = self.db["mqttmessage"]
            self.timeview_collection = self.db["timeview_messages"]
            self._create_timeview_indexes()
            logging.info(f"Database initialized for {self.email}")
        except Exception as e:
            logging.error(f"Failed to connect to MongoDB: {str(e)}")
            raise

    def is_connected(self):
        if self.client is None:
            return False
        try:
            self.client.admin.command('ping')
            return True
        except Exception:
            return False

    def reconnect(self):
        try:
            if self.client is not None:
                self.client.close()
            self.connect()
            logging.info("Reconnected to MongoDB")
        except Exception as e:
            logging.error(f"Failed to reconnect to MongoDB: {str(e)}")
            raise

    def _create_timeview_indexes(self):
        try:
            self.timeview_collection.create_index([("topic", ASCENDING)])
            self.timeview_collection.create_index([("filename", ASCENDING)])
            self.timeview_collection.create_index([("frameIndex", ASCENDING)])
            self.timeview_collection.create_index([("topic", ASCENDING), ("filename", ASCENDING)])
            logging.info("Indexes created for timeview_messages collection")
        except Exception as e:
            logging.error(f"Failed to create indexes for timeview_messages: {str(e)}")

    def close_connection(self):
        if self.client:
            try:
                self.client.close()
                self.client = None
                self.db = None
                self.projects_collection = None
                self.messages_collection = None
                self.timeview_collection = None
                logging.info("MongoDB connection closed")
            except Exception as e:
                logging.error(f"Error closing MongoDB connection: {str(e)}")

    def load_projects(self):
        self.projects = []
        try:
            for project in self.projects_collection.find({"email": self.email}):
                project_name = project.get("project_name")
                if project_name and project_name not in self.projects:
                    self.projects.append(project_name)
            logging.info(f"Loaded projects: {self.projects}")
            return self.projects
        except Exception as e:
            logging.error(f"Error loading projects: {str(e)}")
            return []

    def create_project(self, project_name, models):
        if not project_name:
            return False, "Project name cannot be empty!"
        if self.projects_collection.find_one({"project_name": project_name, "email": self.email}):
            return False, "Project already exists!"

        if not isinstance(models, list):
            logging.error(f"Models must be a list, received: {type(models)}")
            return False, f"Models must be a list, received: {type(models)}"

        for model in models:
            if not isinstance(model, dict) or "name" not in model or "channels" not in model:
                logging.error(f"Each model must be a dictionary with 'name' and 'channels' fields, received: {model}")
                return False, f"Each model must be a dictionary with 'name' and 'channels' fields, received: {model}"
            for channel in model["channels"]:
                if not isinstance(channel, dict) or "channelName" not in channel:
                    logging.error(f"Each channel must be a dictionary with a 'channelName' field, received: {channel}")
                    return False, f"Each channel must be a dictionary with a 'channelName' field, received: {channel}"

        project_data = {
            "_id": ObjectId(),
            "project_name": project_name,
            "email": self.email,
            "createdAt": datetime.datetime.now().isoformat(),
            "models": models
        }
        try:
            result = self.projects_collection.insert_one(project_data)
            logging.info(f"Inserted project {project_name} with ID: {result.inserted_id}")
            if project_name not in self.projects:
                self.projects.append(project_name)
            logging.info(f"Project {project_name} created with {len(models)} models")
            return True, f"Project {project_name} created successfully!"
        except Exception as e:
            logging.error(f"Failed to create project: {str(e)}")
            return False, f"Failed to create project: {str(e)}"

    def edit_project(self, old_project_name, new_project_name, models=None):
        if new_project_name == old_project_name and models is None:
            return True, "No change made"
        if new_project_name != old_project_name and self.projects_collection.find_one({"project_name": new_project_name, "email": self.email}):
            return False, "Project already exists!"

        update_data = {"project_name": new_project_name}
        if models is not None:
            if not isinstance(models, list):
                logging.error(f"Models must be a list, received: {type(models)}")
                return False, f"Models must be a list, received: {type(models)}"
            for model in models:
                if not isinstance(model, dict) or "name" not in model or "channels" not in model:
                    logging.error(f"Each model must be a dictionary with 'name' and 'channels' fields, received: {model}")
                    return False, f"Each model must be a dictionary with 'name' and 'channels' fields, received: {model}"
                for channel in model["channels"]:
                    if not isinstance(channel, dict) or "channelName" not in channel:
                        logging.error(f"Each channel must be a dictionary with a 'channelName' field, received: {channel}")
                        return False, f"Each channel must be a dictionary with a 'channelName' field, received: {channel}"
            update_data["models"] = models

        try:
            result = self.projects_collection.update_one(
                {"project_name": old_project_name, "email": self.email},
                {"$set": update_data}
            )
            logging.info(f"Updated project: matched {result.matched_count}, modified {result.modified_count}")
            if old_project_name in self.projects:
                self.projects[self.projects.index(old_project_name)] = new_project_name
            self.messages_collection.update_many(
                {"project_name": old_project_name, "email": self.email},
                {"$set": {"project_name": new_project_name}}
            )
            self.timeview_collection.update_many(
                {"project_name": old_project_name, "email": self.email},
                {"$set": {"project_name": new_project_name}}
            )
            logging.info(f"Project renamed from {old_project_name} to {new_project_name}")
            return True, f"Project renamed to {new_project_name} successfully!"
        except Exception as e:
            logging.error(f"Failed to edit project: {str(e)}")
            return False, f"Failed to edit project: {str(e)}"

    def delete_project(self, project_name):
        try:
            result = self.projects_collection.delete_one({"project_name": project_name, "email": self.email})
            logging.info(f"Deleted project {project_name}: {result.deleted_count} documents")
            self.messages_collection.delete_many({"project_name": project_name, "email": self.email})
            self.timeview_collection.delete_many({"project_name": project_name, "email": self.email})
            if project_name in self.projects:
                self.projects.remove(project_name)
            logging.info(f"Project {project_name} deleted")
            return True, f"Project {project_name} deleted successfully!"
        except Exception as e:
            logging.error(f"Failed to delete project: {str(e)}")
            return False, f"Failed to delete project: {str(e)}"

    def get_project_data(self, project_name):
        try:
            data = self.projects_collection.find_one({"project_name": project_name, "email": self.email})
            logging.debug(f"Project data for {project_name}: {data}")
            return data
        except Exception as e:
            logging.error(f"Error fetching project data: {str(e)}")
            return None

    def parse_tag_string(self, tag_string):
        if not tag_string or not isinstance(tag_string, str):
            logging.error(f"Tag string must be a non-empty string, received: {tag_string}")
            return None
        return {"tag_name": tag_string.strip()}

    def add_tag(self, project_name, model_name, tag_data, channel_names=None):
        if not self.get_project_data(project_name):
            return False, "Project not found!"
        project_data = self.get_project_data(project_name)
        if model_name not in [m["name"] for m in project_data.get("models", [])]:
            return False, "Model not found in project!"

        if not tag_data or "tag_name" not in tag_data:
            logging.error(f"Invalid tag_data: {tag_data}. Must be a dictionary with a 'tag_name' key.")
            return False, "Tag data must be a dictionary with a 'tag_name' key."

        tag_name = tag_data.get("tag_name")
        if not tag_name or not isinstance(tag_name, str):
            logging.error(f"Tag name must be a non-empty string, received: {tag_name}")
            return False, "Tag name must be a non-empty string."

        if channel_names:
            model = next((m for m in project_data["models"] if m["name"] == model_name), None)
            model_channels = [ch["channelName"] for ch in model.get("channels", [])]
            invalid_channels = [ch for ch in channel_names if ch not in model_channels]
            if invalid_channels:
                logging.error(f"Invalid channel names provided: {invalid_channels}")
                return False, f"Invalid channel names: {invalid_channels}"

        existing_tag = next((m["tagName"] for m in project_data["models"] if m["name"] == model_name), "")
        if existing_tag:
            return False, "Tag already exists in this project and model!"

        try:
            update_data = {f"models.$.tagName": tag_name}
            if channel_names:
                model = next((m for m in project_data["models"] if m["name"] == model_name), None)
                update_data[f"models.$.channels"] = [{"channelName": ch} for ch in channel_names]

            result = self.projects_collection.update_one(
                {"project_name": project_name, "email": self.email, "models.name": model_name},
                {"$set": update_data}
            )
            logging.info(f"Update result for adding tag {tag_name}: matched {result.matched_count}, modified {result.modified_count}")
            if result.modified_count == 0:
                logging.warning(f"Tag {tag_name} was not added to {project_name}/{model_name}.")
                return False, "Failed to add tag: database was not modified."
            logging.info(f"Tag {tag_name} added to {project_name}/{model_name} with channels {channel_names}")
            return True, "Tag added successfully!"
        except Exception as e:
            logging.error(f"Failed to add tag: {str(e)}")
            return False, f"Failed to add tag: {str(e)}"

    def edit_tag(self, project_name, model_name, new_tag_data, channel_names=None):
        project_data = self.get_project_data(project_name)
        if not project_data:
            return False, "Project not found!"
        if model_name not in [m["name"] for m in project_data.get("models", [])]:
            return False, "Model not found in project!"

        if not new_tag_data or "tag_name" not in new_tag_data:
            logging.error(f"Invalid new_tag_data: {new_tag_data}. Must be a dictionary with a 'tag_name' key.")
            return False, "New tag data must be a dictionary with a 'tag_name' key."

        new_tag_name = new_tag_data.get("tag_name")
        if not new_tag_name or not isinstance(new_tag_name, str):
            logging.error(f"New tag name must be a non-empty string, received: {new_tag_name}")
            return False, "New tag name must be a non-empty string."

        if channel_names:
            model = next((m for m in project_data["models"] if m["name"] == model_name), None)
            model_channels = [ch["channelName"] for ch in model.get("channels", [])]
            invalid_channels = [ch for ch in channel_names if ch not in model_channels]
            if invalid_channels:
                logging.error(f"Invalid channel names provided: {invalid_channels}")
                return False, f"Invalid channel names: {invalid_channels}"

        current_tag_name = next((m["tagName"] for m in project_data["models"] if m["name"] == model_name), "")

        try:
            update_data = {f"models.$.tagName": new_tag_name}
            if channel_names is not None:
                update_data[f"models.$.channels"] = [{"channelName": ch} for ch in channel_names]

            result = self.projects_collection.update_one(
                {"project_name": project_name, "email": self.email, "models.name": model_name},
                {"$set": update_data}
            )
            logging.info(f"Update result for editing tag {current_tag_name}: matched {result.matched_count}, modified {result.modified_count}")
            self.messages_collection.update_many(
                {"project_name": project_name, "model_name": model_name, "tag_name": current_tag_name, "email": self.email},
                {"$set": {"tag_name": new_tag_name}}
            )
            self.timeview_collection.update_many(
                {"project_name": project_name, "model_name": model_name, "topic": current_tag_name, "email": self.email},
                {"$set": {"topic": new_tag_name}}
            )
            logging.info(f"Tag {current_tag_name} updated to {new_tag_name} in {project_name}/{model_name}")
            return True, "Tag updated successfully!"
        except Exception as e:
            logging.error(f"Failed to edit tag: {str(e)}")
            return False, f"Failed to edit tag: {str(e)}"

    def delete_tag(self, project_name, model_name):
        project_data = self.get_project_data(project_name)
        if not project_data:
            return False, "Project not found!"
        if model_name not in [m["name"] for m in project_data.get("models", [])]:
            return False, "Model not found in project!"

        tag_name = next((m["tagName"] for m in project_data["models"] if m["name"] == model_name), "")
        if not tag_name:
            return False, "No tag to delete!"

        try:
            result = self.projects_collection.update_one(
                {"project_name": project_name, "email": self.email, "models.name": model_name},
                {"$set": {f"models.$.tagName": ""}}
            )
            logging.info(f"Update result for deleting tag {tag_name}: matched {result.matched_count}, modified {result.modified_count}")
            self.messages_collection.delete_many(
                {"project_name": project_name, "model_name": model_name, "tag_name": tag_name, "email": self.email}
            )
            self.timeview_collection.delete_many(
                {"project_name": project_name, "model_name": model_name, "topic": tag_name, "email": self.email}
            )
            logging.info(f"Tag {tag_name} deleted from {project_name}/{model_name}")
            return True, "Tag deleted successfully!"
        except Exception as e:
            logging.error(f"Failed to delete tag: {str(e)}")
            return False, f"Failed to delete tag: {str(e)}"

    def update_tag_value(self, project_name, model_name, tag_name, values, timestamp=None):
        if not self.get_project_data(project_name):
            logging.error(f"Project {project_name} not found!")
            return False, "Project not found!"

        project_data = self.get_project_data(project_name)
        if model_name not in [m["name"] for m in project_data.get("models", [])]:
            return False, "Model not found in project!"
        current_tag_name = next((m["tagName"] for m in project_data["models"] if m["name"] == model_name), "")
        if current_tag_name != tag_name:
            logging.error(f"Tag {tag_name} not found for project {project_name} and model {model_name}!")
            return False, "Tag not found!"

        timestamp_str = timestamp if timestamp else datetime.datetime.now().isoformat()
        logging.debug(f"Received {len(values)} values for {tag_name} in {project_name}/{model_name} at {timestamp_str}")
        return True, "Tag values received but not saved to mqttmessage collection"

    def get_tag_values(self, project_name, model_name, tag_name):
        try:
            messages = list(self.messages_collection.find(
                {"project_name": project_name, "model_name": model_name, "tag_name": tag_name, "email": self.email}
            ).sort("timestamp", 1))
            if not messages:
                logging.debug(f"No messages found for {tag_name} in {project_name}/{model_name}")
                return []

            for msg in messages:
                if "timestamp" not in msg or "values" not in msg:
                    logging.warning(f"Invalid message format for {tag_name}: {msg}")
                    msg["timestamp"] = msg.get("timestamp", datetime.datetime.now().isoformat())
                    msg["values"] = msg.get("values", [])

            logging.debug(f"Retrieved {len(messages)} messages for {tag_name} in {project_name}/{model_name}")
            return messages
        except Exception as e:
            logging.error(f"Error fetching tag values for {tag_name} in {project_name}/{model_name}: {str(e)}")
            return []

    def save_tag_values(self, project_name, model_name, tag_name, data):
        if not self.get_project_data(project_name):
            logging.error(f"Project {project_name} not found!")
            return False, "Project not found!"

        project_data = self.get_project_data(project_name)
        if model_name not in [m["name"] for m in project_data.get("models", [])]:
            return False, "Model not found in project!"
        current_tag_name = next((m["tagName"] for m in project_data["models"] if m["name"] == model_name), "")
        if current_tag_name != tag_name:
            logging.error(f"Tag {tag_name} not found for project {project_name} and model {model_name}!")
            return False, "Tag not found!"

        message_data = {
            "_id": ObjectId(),
            "topic": tag_name,
            "values": data["values"],
            "project_name": project_name,
            "model_name": model_name,
            "tag_name": tag_name,
            "email": self.email,
            "timestamp": data["timestamp"]
        }
        try:
            result = self.messages_collection.insert_one(message_data)
            logging.debug(f"Saved {len(data['values'])} values for {tag_name} at {data['timestamp']}: {result.inserted_id}")
            return True, "Tag values saved successfully!"
        except Exception as e:
            logging.error(f"Error saving tag values for {tag_name}: {str(e)}")
            return False, f"Failed to save tag values: {str(e)}"

    def save_timeview_message(self, project_name, model_name, message_data):
        if not self.get_project_data(project_name):
            logging.error(f"Project {project_name} not found!")
            return False, "Project not found!"

        required_fields = ["topic", "filename", "frameIndex", "message"]
        for field in required_fields:
            if field not in message_data or message_data[field] is None:
                logging.error(f"Missing or invalid required field {field} in timeview message")
                return False, f"Missing or invalid required field: {field}"

        project_data = self.get_project_data(project_name)
        if model_name not in [m["name"] for m in project_data.get("models", [])]:
            return False, "Model not found in project!"
        current_tag_name = next((m["tagName"] for m in project_data["models"] if m["name"] == model_name), "")
        if current_tag_name != message_data["topic"]:
            logging.error(f"Tag {message_data['topic']} not found for project {project_name} and model {model_name}!")
            return False, "Tag not found!"

        message_data.setdefault("numberOfChannels", 1)
        message_data.setdefault("samplingRate", None)
        message_data.setdefault("samplingSize", None)
        message_data.setdefault("messageFrequency", None)
        message_data.setdefault("createdAt", datetime.datetime.now().isoformat())

        message_data["project_name"] = project_name
        message_data["model_name"] = model_name
        message_data["email"] = self.email
        message_data["_id"] = ObjectId()

        try:
            result = self.timeview_collection.insert_one(message_data)
            logging.info(f"Saved timeview message for {message_data['topic']} in {project_name}/{model_name} with filename {message_data['filename']}: {result.inserted_id}")
            return True, "Timeview message saved successfully!"
        except Exception as e:
            logging.error(f"Error saving timeview message: {str(e)}")
            return False, f"Failed to save timeview message: {str(e)}"

    def get_timeview_messages(self, project_name, model_name=None, topic=None, filename=None):
        if not self.get_project_data(project_name):
            logging.error(f"Project {project_name} not found!")
            return []

        query = {"project_name": project_name, "email": self.email}
        if model_name:
            query["model_name"] = model_name
        if topic:
            query["topic"] = topic
        if filename:
            query["filename"] = filename

        try:
            messages = list(self.timeview_collection.find(query).sort("createdAt", 1))
            if not messages:
                logging.debug(f"No timeview messages found for project {project_name}")
                return []

            logging.debug(f"Retrieved {len(messages)} timeview messages for project {project_name}")
            return messages
        except Exception as e:
            logging.error(f"Error fetching timeview messages: {str(e)}")
            return []

    def get_distinct_filenames(self, project_name, model_name=None):
        if not self.get_project_data(project_name):
            logging.error(f"Project {project_name} not found!")
            return []

        query = {"project_name": project_name, "email": self.email}
        if model_name:
            query["model_name"] = model_name

        try:
            filenames = self.timeview_collection.distinct("filename", query)
            sorted_filenames = sorted(filenames, key=lambda x: int(re.match(r"data(\d+)", x).group(1)) if re.match(r"data(\d+)", x) else 0)
            logging.debug(f"Retrieved {len(sorted_filenames)} distinct filenames for project {project_name}")
            return sorted_filenames
        except Exception as e:
            logging.error(f"Error fetching distinct filenames: {str(e)}")
            return []