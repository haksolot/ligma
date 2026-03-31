import os
import re

class PersonalityManager:
    """Manages bot personalities stored as text files in a dedicated directory."""
    
    def __init__(self, directory="personalities", default_name="default"):
        self.directory = directory
        self.default_name = default_name
        self.current_name = default_name
        
        if not os.path.exists(self.directory):
            os.makedirs(self.directory)
            # Create a default if it doesn't exist
            self.save("default", "You are a helpful and professional AI assistant.")

        self.current_personality = self.load(self.current_name)

    def sanitize_name(self, name):
        """Removes characters that are invalid for filenames."""
        # Remove everything except alphanumeric, spaces, hyphens, and underscores
        return re.sub(r'[^\w\s-]', '', name).strip()

    def get_path(self, name):
        """Returns the full file path for a given personality name."""
        sanitized = self.sanitize_name(name)
        return os.path.join(self.directory, f"{sanitized}.txt")

    def load(self, name):
        """Retrieves a personality by name from its text file."""
        path = self.get_path(name)
        if not os.path.exists(path):
            # Fallback to default if not found
            path = self.get_path("default")
            self.current_name = "default"
        else:
            self.current_name = self.sanitize_name(name)

        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            self.current_personality = content
            return content

    def save(self, name, content):
        """Creates or updates a personality file."""
        sanitized = self.sanitize_name(name)
        if not sanitized:
            raise ValueError("Invalid personality name.")
            
        path = self.get_path(sanitized)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
            
        if sanitized == self.current_name:
            self.current_personality = content

    def delete(self, name):
        """Deletes a personality file. Cannot delete the 'default' one."""
        sanitized = self.sanitize_name(name)
        if sanitized == "default":
            return False
            
        path = self.get_path(sanitized)
        if os.path.exists(path):
            os.remove(path)
            # If current was deleted, switch to default
            if self.current_name == sanitized:
                self.load("default")
            return True
        return False

    def list_all(self):
        """Lists all available personality names (without .txt extension)."""
        if not os.path.exists(self.directory):
            return ["default"]
        files = [f for f in os.listdir(self.directory) if f.endswith(".txt")]
        return [f[:-4] for f in files]
