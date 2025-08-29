import json
import os
from config import app_cfg

class JsonManager:
    """
    A class to manage JSON file operations, with one JSON file per module.
    """

    def __init__(self, json_directory: str = app_cfg["JSON_PATH"]):
        
        self.json_directory = json_directory
        # Create the directory if it doesn't exist
        if not os.path.exists(self.json_directory):
            os.makedirs(self.json_directory)

    def _get_json_file_path(self, module_name: str) -> str:
        
        # Sanitize module_name to remove characters that might be invalid in a filename
        sanitized_module_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in module_name)
        return os.path.join(self.json_directory, f"{sanitized_module_name}.json")

    def load_json(self, module_name: str) -> dict:
        
        file_path = self._get_json_file_path(module_name)
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError as e:
            return {"exceptions": [{"type": "FileNotFoundError", "message": str(e), "ai_explanation": None}]}
        except json.JSONDecodeError as e:
            return {"exceptions": [{"type": "JSONDecodeError", "message": str(e), "ai_explanation": None}]}

    def save_json(self, module_name: str, data: dict):
        
        file_path = self._get_json_file_path(module_name)
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=4)  # Use indent=4 for readability
        except Exception as e:
            print(f"Error saving JSON for module '{module_name}': {e}")

    def add_exceptions(self, module_name: str, exceptions_data: list):

        file_path = self._get_json_file_path(module_name)

        # Check if the file exists.  If not, initialize an empty dictionary.
        if os.path.exists(file_path):
            data = self.load_json(module_name)  # Load existing JSON data for this module
        else:
            data = {"exceptions": []}  # Initialize with an empty list of exceptions

        # Convert existing exceptions to a set for efficient duplicate checking
        existing_exceptions = set(json.dumps(ex, sort_keys=True) for ex in data.get("exceptions", []))
        new_exceptions = []
        for exception in exceptions_data:
            # Initialize 'ai_explanation' if it doesn't exist
            if "prompt" not in exception:
                exception["prompt"] = None
            if "ai_explanation" not in exception:
                exception["ai_explanation"] = None
            if json.dumps(exception, sort_keys=True) not in existing_exceptions:
                new_exceptions.append(exception)

        # Add the new exceptions
        if new_exceptions:
            data["exceptions"] = data.get("exceptions", []) + new_exceptions  # Append, don't overwrite

        self.save_json(module_name, data)  # Save the updated JSON for this module
        print(f"Exceptions for '{module_name}' added/updated in '{self._get_json_file_path(module_name)}'.")

    def module_exists(self, module_name: str) -> bool:
        
        file_path = self._get_json_file_path(module_name)
        return os.path.exists(file_path)

    def update_json_value(self, module_name: str, condition_id: str, group: str, to_change: str, value: str):
        
        data = self.load_json(module_name)
        if "exceptions" in data:
            for i, exception in enumerate(data["exceptions"]):
                if ("condition_id" in exception and exception["condition_id"] == condition_id and
                    "condition_group" in exception and exception["condition_group"] == group):  # Added group check
                    exception[to_change] = value
                    self.save_json(module_name, data)
                    print(f"Exception updated with condition_id '{condition_id}' and group '{group}' in '{module_name}'.")
                    return  # Exit after the first match
                
            print(f"Error: Exception with condition_id '{condition_id}' and group '{group}' not found in '{module_name}'.")
        else:
            print(f"Error: No exceptions found in '{module_name}'.")

    def get_exception_value(self, module_name: str, condition_id: str, group: str, value_name: str):

        data = self.load_json(module_name)
        if "exceptions" in data:
            for exception in data["exceptions"]:
                if ("condition_id" in exception and exception["condition_id"] == condition_id and
                    "condition_group" in exception and exception["condition_group"] == group):  # Added group check
                    if value_name in exception:
                        return exception[value_name]
                    else:
                        print(f"Error: Value '{value_name}' not found in exception with condition_id '{condition_id}' and group '{group}' of '{module_name}'.")
                        return None
            print(f"Error: Exception with condition_id '{condition_id}' and group '{group}' not found in '{module_name}'.")
            return None
        else:
            print(f"Error: No exceptions found in '{module_name}'.")
            return None
        
    def change_stp_list(stp_list: list, json_path: str = app_cfg['JSON_PATH']):
        json_path = os.path.normpath(os.path.join(json_path, 'stp_list.json'))
        try:
            if os.path.exists(json_path):
                with open(json_path, 'r') as f:
                    try:
                        data = json.load(f)
                    except json.JSONDecodeError:
                        print(f"Erreur: Le fichier JSON '{json_path}' est corrompu.  Il sera réinitialisé.")
                        data = {"stp_list": []}
            else:
                data = {"stp_list": []}

            data["stp_list"] = stp_list

            with open(json_path, 'w') as f:
                json.dump(data, f, indent=2)  

            print(f"La liste 'stp_list' a été mise à jour dans '{json_path}'.")

        except Exception as e:
            print(f"Une erreur s'est produite : {e}")

    def get_stp_list(json_path: str = app_cfg['JSON_PATH']):
        json_path = os.path.normpath(os.path.join(json_path, 'stp_list.json'))
        try:
            if os.path.exists(json_path):
                with open(json_path, 'r') as f:
                    try:
                        data = json.load(f)
                        if "stp_list" in data:
                            return data["stp_list"]
                        else:
                            print(f"Avertissement: Le fichier JSON '{json_path}' ne contient pas la clé 'stp_list'. Retourne une liste vide.")
                            return []
                    except json.JSONDecodeError:
                        print(f"Erreur: Le fichier JSON '{json_path}' est corrompu. Retourne une liste vide.")
                        return []
            else:
                print(f"Avertissement: Le fichier JSON '{json_path}' n'existe pas. Retourne une liste vide.")
                return []
        except Exception as e:
            print(f"Une erreur s'est produite : {e}. Retourne une liste vide.")
            return []
