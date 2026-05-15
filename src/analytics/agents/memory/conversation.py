"""
Conversation Memory
===================
Manages conversation history for the depopulation analysis agent.
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import json


@dataclass
class Message:
    """A single message in the conversation."""
    role: str  # 'user', 'assistant', 'system', 'tool'
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    tool_calls: Optional[List[Dict]] = None
    tool_results: Optional[Dict] = None
    metadata: Dict = field(default_factory=dict)


@dataclass
class ConversationMemory:
    """
    Manages conversation history for contextual responses.

    Keeps track of:
    - User questions and assistant responses
    - Tool calls and their results
    - Important context for follow-up questions
    """

    messages: List[Message] = field(default_factory=list)
    max_messages: int = 20  # Keep last N messages
    summary: str = ""  # Summary of older messages
    context: Dict[str, Any] = field(default_factory=dict)  # Extracted context

    def add_message(self, role: str, content: str, **kwargs) -> None:
        """Add a message to the conversation history."""
        message = Message(
            role=role,
            content=content,
            tool_calls=kwargs.get('tool_calls'),
            tool_results=kwargs.get('tool_results'),
            metadata=kwargs.get('metadata', {})
        )
        self.messages.append(message)

        # Trim if exceeds max
        if len(self.messages) > self.max_messages:
            self._summarize_and_trim()

        # Extract context from the message
        self._extract_context(message)

    def add_user_message(self, content: str) -> None:
        """Add a user message."""
        self.add_message('user', content)

    def add_assistant_message(self, content: str, tool_calls: Optional[List] = None) -> None:
        """Add an assistant message."""
        self.add_message('assistant', content, tool_calls=tool_calls)

    def add_tool_result(self, tool_name: str, result: str) -> None:
        """Add a tool result."""
        self.add_message('tool', result, metadata={'tool_name': tool_name})

    def get_messages_for_llm(self, include_system: bool = True) -> List[Dict]:
        """
        Get messages formatted for LLM consumption.

        Returns a list of message dicts with 'role' and 'content'.
        """
        formatted = []

        # Add summary as system context if available
        if self.summary and include_system:
            formatted.append({
                'role': 'system',
                'content': f"Previous conversation summary: {self.summary}"
            })

        # Add recent messages
        for msg in self.messages[-10:]:  # Last 10 for context
            formatted.append({
                'role': msg.role if msg.role != 'tool' else 'assistant',
                'content': msg.content
            })

        return formatted

    def get_context(self) -> Dict[str, Any]:
        """Get extracted context from the conversation."""
        return self.context

    def _extract_context(self, message: Message) -> None:
        """Extract important context from a message."""
        content = message.content.lower()

        # Extract mentioned provinces
        provinces = [
            'teruel', 'soria', 'cuenca', 'guadalajara', 'zamora',
            'palencia', 'avila', 'segovia', 'huesca', 'lleida',
            'madrid', 'barcelona', 'valencia', 'sevilla', 'malaga'
        ]
        for province in provinces:
            if province in content:
                self.context['last_province'] = province.title()

        # Extract mentioned years
        import re
        years = re.findall(r'\b(19[89]\d|20[0-2]\d)\b', content)
        if years:
            self.context['mentioned_years'] = [int(y) for y in years]

        # Extract topic focus
        if any(word in content for word in ['despobla', 'vaciad', 'depopulat']):
            self.context['topic'] = 'depopulation'
        elif any(word in content for word in ['crec', 'repobla', 'grow']):
            self.context['topic'] = 'repopulation'
        elif any(word in content for word in ['paro', 'desempleo', 'unemploy']):
            self.context['topic'] = 'unemployment'
        elif any(word in content for word in ['industri', 'pib', 'gdp', 'econom']):
            self.context['topic'] = 'economy'

    def _summarize_and_trim(self) -> None:
        """Summarize old messages and keep only recent ones."""
        # Keep the last max_messages/2
        keep_count = self.max_messages // 2
        old_messages = self.messages[:-keep_count]
        self.messages = self.messages[-keep_count:]

        # Create summary of old messages
        topics_discussed = set()
        provinces_mentioned = set()

        for msg in old_messages:
            if msg.role == 'user':
                # Extract key topics from questions
                content = msg.content.lower()
                if 'despobla' in content or 'depopulat' in content:
                    topics_discussed.add('depopulation trends')
                if 'factor' in content or 'causa' in content or 'cause' in content:
                    topics_discussed.add('depopulation factors')
                if 'compar' in content:
                    topics_discussed.add('temporal comparisons')

        if topics_discussed:
            self.summary = f"Previously discussed: {', '.join(topics_discussed)}."
            if self.context.get('last_province'):
                self.summary += f" Focus on {self.context['last_province']} province."

    def clear(self) -> None:
        """Clear conversation history."""
        self.messages = []
        self.summary = ""
        self.context = {}

    def to_dict(self) -> Dict:
        """Serialize conversation to dictionary."""
        return {
            'messages': [
                {
                    'role': m.role,
                    'content': m.content,
                    'timestamp': m.timestamp.isoformat(),
                    'metadata': m.metadata
                }
                for m in self.messages
            ],
            'summary': self.summary,
            'context': self.context
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'ConversationMemory':
        """Deserialize conversation from dictionary."""
        memory = cls()
        memory.summary = data.get('summary', '')
        memory.context = data.get('context', {})

        for msg_data in data.get('messages', []):
            message = Message(
                role=msg_data['role'],
                content=msg_data['content'],
                timestamp=datetime.fromisoformat(msg_data['timestamp']),
                metadata=msg_data.get('metadata', {})
            )
            memory.messages.append(message)

        return memory

    def save_to_file(self, filepath: str) -> None:
        """Save conversation to a JSON file."""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load_from_file(cls, filepath: str) -> 'ConversationMemory':
        """Load conversation from a JSON file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)

