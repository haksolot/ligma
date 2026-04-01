from typing import List, Optional, Tuple, Dict, Any

class SkillManager:
    def __init__(self, skills: Optional[List] = None):
        # We store skills in a dictionary for easy access/toggle
        self.skills = {}
        if skills:
            for skill in skills:
                self.skills[skill.name] = skill

    def get_active_prompts(self) -> str:
        prompts = []
        counter = 1
        # Sort by name for consistency
        sorted_skills = sorted(self.skills.items())
        for name, skill in sorted_skills:
            if skill.is_active:
                prompts.append(f"{counter}. {skill.get_prompt_injection()}")
                counter += 1
        
        if not prompts:
            return ""
            
        header = (
            "### YOUR DISCORD CAPABILITIES:\n"
            "You have access to the following skills. Use them naturally when needed.\n"
            "0. **PINGING**: Use <@USER_ID> syntax only to mention users.\n"
        )
        return header + "\n".join(prompts)

    def toggle_skill(self, name: str, state: bool) -> bool:
        if name in self.skills:
            self.skills[name].is_active = state
            return True
        return False

    def list_all(self):
        # Return sorted list for UI
        return sorted([(name, skill.is_active, skill.description) for name, skill in self.skills.items()])

    async def run_reflections(self, response: str, message):
        """Runs reflection loops for active skills. Returns the context string if a reflection triggers."""
        for skill in self.skills.values():
            if not skill.is_active: continue
            reflection_context = await skill.execute_reflection(response, message)
            if reflection_context:
                return reflection_context
        return None

    async def run_actions(self, response: str, message):
        """Runs final actions for active skills. Returns the cleaned string and combined context dictionary."""
        combined_context = {}
        cleaned_response = response
        
        for skill in self.skills.values():
            if not skill.is_active: continue
            cleaned_response, ctx = await skill.execute_action(cleaned_response, message)
            combined_context.update(ctx)
            
        return cleaned_response, combined_context
