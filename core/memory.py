import ollama
from config import DEFAULT_MODEL


class MemoryManager:
    def __init__(self, default_model=DEFAULT_MODEL, limit=10):
        self.history = {}  # {channel_id: [messages]}
        self.summaries = {}  # {channel_id: "summary"}
        self.limit = limit
        self.default_model = default_model
        self._provider = None
        self._client = ollama.AsyncClient()

    def set_provider(self, provider):
        self._provider = provider

    async def add_message(
        self, channel_id, role, content, message_id=None, author_name=None
    ):
        if channel_id not in self.history:
            self.history[channel_id] = []

        # We store metadata to help the AI target messages
        entry = {"role": role, "content": content}
        if message_id:
            entry["id"] = message_id
        if author_name:
            entry["author"] = author_name

        self.history[channel_id].append(entry)

        # Compress if too many messages
        if len(self.history[channel_id]) > self.limit:
            await self.compress(channel_id)

    async def get_context(
        self, channel_id, personality, user_message, author_name=None
    ):
        import time

        messages = []

        # 1. System Prompt (Identity & Instructions) FIRST
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        system_content = f"{personality}\n\n### TEMPORAL CONTEXT\nCurrent Date and Time: {current_time}"
        messages.append({"role": "system", "content": system_content})

        # 2. Add summary if it exists (as a recap of the past)
        if channel_id in self.summaries:
            messages.append(
                {
                    "role": "system",
                    "content": f"Summary of older conversation: {self.summaries[channel_id]}",
                }
            )

        # 3. Add recent history with clear separation
        if channel_id in self.history:
            history_messages = self.history[channel_id]
            # AVOID DUPLICATION: If the last message in history is the same as the current user_message,
            # we skip it in the history loop because it will be added at the end.
            if (
                history_messages
                and history_messages[-1]["role"] == "user"
                and history_messages[-1]["content"] == user_message
            ):
                history_messages = history_messages[:-1]

            for msg in history_messages:
                role = msg["role"]
                content = msg["content"]
                author = msg.get("author", "Unknown")
                msg_id = msg.get("id", "N/A")

                # Format content based on role
                prefix = f"(ID: {msg_id}) " if msg_id and msg_id != "N/A" else ""

                if role == "assistant":
                    formatted_content = f"{prefix}{content}"
                else:
                    formatted_content = f"{prefix}{author}: {content}"

                messages.append({"role": role, "content": formatted_content})

        # 4. Current User Message (Formatted with author for consistency)
        final_user_content = (
            f"{author_name}: {user_message}" if author_name else user_message
        )
        messages.append({"role": "user", "content": final_user_content})
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

            if self._provider:
                response = await self._provider.chat(
                    model=self.default_model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert in raw text synthesis.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                )
            else:
                response = await self._client.chat(
                    model=self.default_model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert in raw text synthesis.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                )

            self.summaries[channel_id] = response["message"]["content"]
            self.history[channel_id] = self.history[channel_id][-2:]
            print(f"[Memory] Compression completed for {channel_id}.")

        except Exception as e:
            print(f"[Memory] Compression error: {e}")

    def get_stats(self, channel_id):
        history = self.history.get(channel_id, [])
        summary = self.summaries.get(channel_id, "")
        history_chars = sum(len(m["content"]) for m in history)
        summary_chars = len(summary)

        return {
            "history_count": len(history),
            "history_chars": history_chars,
            "summary_chars": summary_chars,
            "total_volatile_chars": history_chars + summary_chars,
        }

    def clear(self, channel_id):
        if channel_id in self.history:
            self.history[channel_id] = []
        if channel_id in self.summaries:
            del self.summaries[channel_id]
