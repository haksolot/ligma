import ollama
from config import DEFAULT_MODEL

class MemoryManager:
    def __init__(self, default_model=DEFAULT_MODEL, limit=10):
        self.history = {}  # {channel_id: [messages]}
        self.summaries = {}  # {channel_id: "summary"}
        self.limit = limit
        self.default_model = default_model
        self.client = ollama.AsyncClient()

    async def add_message(self, channel_id, role, content, message_id=None, author_name=None):
        if channel_id not in self.history:
            self.history[channel_id] = []
        
        # We store metadata to help the AI target messages
        entry = {'role': role, 'content': content}
        if message_id: entry['id'] = message_id
        if author_name: entry['author'] = author_name
            
        self.history[channel_id].append(entry)
        
        # Compress if too many messages
        if len(self.history[channel_id]) > self.limit:
            await self.compress(channel_id)

    async def get_context(self, channel_id, personality, user_message):
        import time
        messages = []
        
        # 1. System Prompt (Identity & Instructions) FIRST
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        system_content = f"{personality}\n\n### TEMPORAL CONTEXT\nCurrent Date and Time: {current_time}"
        messages.append({'role': 'system', 'content': system_content})

        # 2. Add summary if it exists (as a recap of the past)
        if channel_id in self.summaries:
            messages.append({'role': 'system', 'content': f"Summary of older conversation: {self.summaries[channel_id]}"})
        
        # 3. Add recent history with clear separation
        if channel_id in self.history:
            for msg in self.history[channel_id]:
                role = msg['role']
                content = msg['content']
                author = msg.get('author', 'Unknown')
                msg_id = msg.get('id', 'N/A')

                # Format content based on role
                if role == "assistant":
                    # For assistant, we don't necessarily need the name prefix in the content 
                    # if the role is already 'assistant', but the ID is still useful for context.
                    formatted_content = f"(ID: {msg_id}) {content}"
                else:
                    # For users, we clearly state who is talking
                    formatted_content = f"(ID: {msg_id}) {author}: {content}"
                
                messages.append({
                    'role': role, 
                    'content': formatted_content
                })
            
        # 4. Current User Message
        messages.append({'role': 'user', 'content': user_message})
        return messages

    async def compress(self, channel_id):
        """Compresses old messages to avoid overloading memory."""
        try:
            old_summary = self.summaries.get(channel_id, "")
            messages_to_compress = self.history[channel_id][:-2]  # Keep the last 2
            
            prompt = f"""
            Here is the previous context: {old_summary}
            Here are new exchanges (format: ID | Author: Content): {messages_to_compress}
            Instruction: Make an extremely concise summary of this information. Keep track of important IDs if relevant.
            """
            
            response = await self.client.chat(model=self.default_model, messages=[
                {'role': 'system', 'content': 'You are an expert in raw text synthesis.'},
                {'role': 'user', 'content': prompt}
            ])
            
            self.summaries[channel_id] = response['message']['content']
            self.history[channel_id] = self.history[channel_id][-2:]
            print(f"[Memory] Compression completed for {channel_id}.")
            
        except Exception as e:
            print(f"[Memory] Compression error: {e}")

    def get_stats(self, channel_id):
        history = self.history.get(channel_id, [])
        summary = self.summaries.get(channel_id, "")
        history_chars = sum(len(m['content']) for m in history)
        summary_chars = len(summary)
        
        return {
            "history_count": len(history),
            "history_chars": history_chars,
            "summary_chars": summary_chars,
            "total_volatile_chars": history_chars + summary_chars
        }

    def clear(self, channel_id):
        if channel_id in self.history:
            self.history[channel_id] = []
        if channel_id in self.summaries:
            del self.summaries[channel_id]
