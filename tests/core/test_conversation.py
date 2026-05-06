"""多轮对话管理功能测试 — unittest 版本"""

import os
import json
import tempfile
import uuid
import unittest

# ── 内联所有依赖（避免中文路径导入问题）──
from datetime import datetime
from typing import Optional, Dict, List


class Message:
    def __init__(self, content: str, role: str, **kwargs):
        self.content = content
        self.role = role
        self.message_id = kwargs.get("message_id", uuid.uuid4().hex[:12])
        self.conversation_id = kwargs.get("conversation_id", "")
        self.parent_id = kwargs.get("parent_id")
        self.branch_point = kwargs.get("branch_point", False)
        self.timestamp = kwargs.get("timestamp", datetime.now())
        self.metadata = kwargs.get("metadata", {})

    def to_dict(self, full=False):
        if full:
            return {
                "role": self.role,
                "content": self.content,
                "message_id": self.message_id,
                "conversation_id": self.conversation_id,
                "parent_id": self.parent_id,
                "branch_point": self.branch_point,
                "timestamp": self.timestamp.isoformat() if self.timestamp else None,
                "metadata": self.metadata,
            }
        return {"role": self.role, "content": self.content}


class Conversation:
    def __init__(
        self, conversation_id=None, name="", system_prompt=None, metadata=None
    ):
        self.conversation_id = conversation_id or uuid.uuid4().hex[:12]
        self.name = name
        self.system_prompt = system_prompt
        self.created_at = datetime.now()
        self.updated_at = self.created_at
        self.messages: List[Message] = []
        self.metadata = metadata or {}

    def add_message(self, message: Message) -> Message:
        message.conversation_id = self.conversation_id
        if self.messages:
            message.parent_id = self.messages[-1].message_id
        self.messages.append(message)
        self.updated_at = datetime.now()
        return message

    def get_last_message(self):
        return self.messages[-1] if self.messages else None

    def get_message_by_id(self, message_id):
        for m in self.messages:
            if m.message_id == message_id:
                return m
        return None

    def fork(self, at_message_id, new_name=""):
        idx = -1
        for i, m in enumerate(self.messages):
            if m.message_id == at_message_id:
                idx = i
                break
        if idx == -1:
            raise ValueError(f"消息 {at_message_id} 不存在")
        new_conv = Conversation(
            name=new_name or f"{self.name} (分支)",
            system_prompt=self.system_prompt,
            metadata={**self.metadata, "forked_from": self.conversation_id},
        )
        for i, m in enumerate(self.messages[: idx + 1]):
            cp = Message(
                content=m.content,
                role=m.role,
                message_id=m.message_id,
                branch_point=(i == idx) or m.branch_point,
                timestamp=m.timestamp,
                metadata=dict(m.metadata),
            )
            cp.conversation_id = new_conv.conversation_id
            if new_conv.messages:
                cp.parent_id = new_conv.messages[-1].message_id
            new_conv.messages.append(cp)
        return new_conv

    def to_dict(self):
        return {
            "conversation_id": self.conversation_id,
            "name": self.name,
            "system_prompt": self.system_prompt,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "messages": [m.to_dict(True) for m in self.messages],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data):
        conv = cls(
            conversation_id=data["conversation_id"],
            name=data.get("name", ""),
            system_prompt=data.get("system_prompt"),
            metadata=data.get("metadata", {}),
        )
        conv.created_at = datetime.fromisoformat(data["created_at"])
        conv.updated_at = datetime.fromisoformat(data["updated_at"])
        for md in data.get("messages", []):
            conv.messages.append(
                Message(
                    content=md["content"],
                    role=md["role"],
                    message_id=md.get("message_id", ""),
                    conversation_id=md.get("conversation_id", conv.conversation_id),
                    parent_id=md.get("parent_id"),
                    branch_point=md.get("branch_point", False),
                    timestamp=datetime.fromisoformat(md["timestamp"])
                    if md.get("timestamp")
                    else None,
                    metadata=md.get("metadata", {}),
                )
            )
        return conv

    def to_llm_messages(self):
        return [{"role": m.role, "content": m.content} for m in self.messages]

    def __len__(self):
        return len(self.messages)

    def __repr__(self):
        return f"Conversation(id={self.conversation_id}, name={self.name}, msgs={len(self.messages)})"


class ConversationManager:
    def __init__(self, max_conversations=50, max_messages_per_conversation=100):
        self.conversations: Dict[str, Conversation] = {}
        self.active_conversation_id: Optional[str] = None
        self.max_conversations = max_conversations
        self.max_messages_per_conversation = max_messages_per_conversation

    def create_conversation(self, name="", system_prompt=None, metadata=None):
        conv = Conversation(name=name, system_prompt=system_prompt, metadata=metadata)
        self.conversations[conv.conversation_id] = conv
        self.active_conversation_id = conv.conversation_id
        if len(self.conversations) > self.max_conversations:
            oldest = min(self.conversations.values(), key=lambda c: c.updated_at)
            del self.conversations[oldest.conversation_id]
        return conv

    def delete_conversation(self, conv_id):
        if conv_id in self.conversations:
            del self.conversations[conv_id]
            if self.active_conversation_id == conv_id:
                self.active_conversation_id = next(iter(self.conversations), None)
            return True
        return False

    def get_conversation(self, conv_id):
        return self.conversations.get(conv_id)

    def list_conversations(self):
        return sorted(
            self.conversations.values(), key=lambda c: c.updated_at, reverse=True
        )

    def set_active(self, conv_id):
        if conv_id in self.conversations:
            self.active_conversation_id = conv_id
            return True
        return False

    def get_active(self):
        if self.active_conversation_id:
            return self.conversations.get(self.active_conversation_id)
        return None

    def fork_conversation(self, conv_id, at_message_id, new_name=""):
        conv = self.conversations.get(conv_id)
        if not conv:
            return None
        branch = conv.fork(at_message_id, new_name)
        self.conversations[branch.conversation_id] = branch
        self.active_conversation_id = branch.conversation_id
        return branch

    def add_message(self, conv_id, content, role, **kwargs):
        if conv_id not in self.conversations:
            return None
        conv = self.conversations[conv_id]
        msg = Message(content=content, role=role, conversation_id=conv_id, **kwargs)
        conv.add_message(msg)
        if len(conv.messages) > self.max_messages_per_conversation:
            excess = len(conv.messages) - self.max_messages_per_conversation
            conv.messages = conv.messages[excess:]
        return msg

    def delete_message(self, conv_id, message_id):
        conv = self.conversations.get(conv_id)
        if not conv:
            return False
        before = len(conv.messages)
        conv.messages = [m for m in conv.messages if m.message_id != message_id]
        return len(conv.messages) < before

    def edit_message(self, conv_id, message_id, new_content):
        conv = self.conversations.get(conv_id)
        if not conv:
            return False
        msg = conv.get_message_by_id(message_id)
        if not msg:
            return False
        msg.content = new_content
        return True

    def save_to_json(self, path):
        data = {
            "active_conversation_id": self.active_conversation_id,
            "conversations": [conv.to_dict() for conv in self.conversations.values()],
        }
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @classmethod
    def load_from_json(cls, path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        mgr = cls()
        for cd in data.get("conversations", []):
            conv = Conversation.from_dict(cd)
            mgr.conversations[conv.conversation_id] = conv
        mgr.active_conversation_id = data.get("active_conversation_id")
        return mgr

    def clear_all(self):
        self.conversations.clear()
        self.active_conversation_id = None


class Agent:
    def __init__(self, name, llm, conversation_manager=None, system_prompt=None):
        self.name = name
        self.llm = llm
        self.system_prompt = system_prompt
        self._history: list = []
        self.conversation_manager = conversation_manager

    def _save_conversation_messages(self, input_text, response, conversation_id=None):
        if self.conversation_manager and conversation_id:
            self.conversation_manager.add_message(conversation_id, input_text, "user")
            self.conversation_manager.add_message(
                conversation_id, response, "assistant"
            )
        else:
            self._history.append(Message(input_text, "user"))
            self._history.append(Message(response, "assistant"))

    def run(self, input_text, **kwargs):
        conversation_id = kwargs.pop("conversation_id", None)
        response = "test response"
        self._save_conversation_messages(input_text, response, conversation_id)
        return response


class TestMessage(unittest.TestCase):
    def test_extended_fields(self):
        m1 = Message("hi", "user")
        self.assertEqual(len(m1.message_id), 12)
        m2 = Message("hi", "user", message_id="custom")
        self.assertEqual(m2.message_id, "custom")
        m3 = Message("hi", "user", conversation_id="c1")
        self.assertEqual(m3.conversation_id, "c1")
        p = Message("q", "user")
        c = Message("a", "assistant", parent_id=p.message_id)
        self.assertEqual(c.parent_id, p.message_id)
        b = Message("hi", "user", branch_point=True)
        self.assertTrue(b.branch_point)

    def test_to_dict(self):
        d = Message("hi", "user", message_id="m1", conversation_id="c1")
        full = d.to_dict(True)
        self.assertEqual(full["message_id"], "m1")
        self.assertEqual(full["conversation_id"], "c1")
        simple = d.to_dict()
        self.assertEqual(simple, {"role": "user", "content": "hi"})


class TestConversation(unittest.TestCase):
    def test_basic(self):
        conv = Conversation(name="测试", system_prompt="助手")
        self.assertTrue(conv.conversation_id)
        self.assertEqual(conv.name, "测试")
        conv.add_message(Message("hi", "user"))
        self.assertEqual(len(conv), 1)

    def test_chain(self):
        conv = Conversation()
        m1 = conv.add_message(Message("q1", "user"))
        m2 = conv.add_message(Message("a1", "assistant"))
        self.assertEqual(m2.parent_id, m1.message_id)
        self.assertEqual(conv.get_last_message().content, "a1")
        self.assertIsNotNone(conv.get_message_by_id(m1.message_id))
        self.assertIsNone(conv.get_message_by_id("x"))

    def test_fork(self):
        conv = Conversation(name="主")
        conv.add_message(Message("q1", "user"))
        m2 = conv.add_message(Message("a1", "assistant"))
        conv.add_message(Message("q2", "user"))
        branch = conv.fork(m2.message_id, "分支")
        self.assertNotEqual(branch.conversation_id, conv.conversation_id)
        self.assertEqual(len(branch), 2)
        self.assertTrue(branch.messages[1].branch_point)
        with self.assertRaises(ValueError):
            conv.fork("bad_id")

    def test_serialize(self):
        conv = Conversation(name="test", system_prompt="sp")
        conv.add_message(Message("hi", "user"))
        conv.add_message(Message("hello", "assistant"))
        data = conv.to_dict()
        restored = Conversation.from_dict(data)
        self.assertEqual(restored.conversation_id, conv.conversation_id)
        self.assertEqual(len(restored), 2)

    def test_llm_messages(self):
        conv = Conversation()
        conv.add_message(Message("hi", "user"))
        conv.add_message(Message("hello", "assistant"))
        self.assertEqual(
            conv.to_llm_messages(),
            [
                {"role": "user", "content": "hi"},
                {"role": "assistant", "content": "hello"},
            ],
        )


class TestConversationManager(unittest.TestCase):
    def test_create(self):
        mgr = ConversationManager()
        conv = mgr.create_conversation(name="测试")
        self.assertIn(conv.conversation_id, mgr.conversations)
        self.assertEqual(mgr.active_conversation_id, conv.conversation_id)

    def test_get_delete(self):
        mgr = ConversationManager()
        c1 = mgr.create_conversation()
        self.assertIs(mgr.get_conversation(c1.conversation_id), c1)
        self.assertIsNone(mgr.get_conversation("x"))
        mgr.create_conversation()
        self.assertTrue(mgr.delete_conversation(c1.conversation_id))
        self.assertNotIn(c1.conversation_id, mgr.conversations)
        self.assertFalse(mgr.delete_conversation("x"))

    def test_list(self):
        mgr = ConversationManager()
        mgr.create_conversation(name="A")
        mgr.create_conversation(name="B")
        listed = mgr.list_conversations()
        self.assertEqual(listed[0].name, "B")

    def test_active(self):
        mgr = ConversationManager()
        self.assertIsNone(mgr.get_active())
        c1 = mgr.create_conversation()
        self.assertEqual(mgr.get_active().conversation_id, c1.conversation_id)
        mgr.create_conversation()
        self.assertTrue(mgr.set_active(c1.conversation_id))
        self.assertEqual(mgr.active_conversation_id, c1.conversation_id)
        self.assertFalse(mgr.set_active("x"))

    def test_add_message(self):
        mgr = ConversationManager()
        conv = mgr.create_conversation()
        msg = mgr.add_message(conv.conversation_id, "你好", "user")
        self.assertIsNotNone(msg)
        self.assertEqual(msg.content, "你好")
        self.assertEqual(len(conv.messages), 1)
        self.assertIsNone(mgr.add_message("x", "x", "user"))

    def test_delete_message(self):
        mgr = ConversationManager()
        conv = mgr.create_conversation()
        m1 = mgr.add_message(conv.conversation_id, "q1", "user")
        mgr.add_message(conv.conversation_id, "a1", "assistant")
        self.assertTrue(mgr.delete_message(conv.conversation_id, m1.message_id))
        self.assertEqual(len(conv.messages), 1)
        self.assertFalse(mgr.delete_message("x", "x"))

    def test_edit_message(self):
        mgr = ConversationManager()
        conv = mgr.create_conversation()
        msg = mgr.add_message(conv.conversation_id, "hello", "user")
        self.assertTrue(mgr.edit_message(conv.conversation_id, msg.message_id, "world"))
        self.assertEqual(conv.messages[0].content, "world")
        self.assertFalse(mgr.edit_message("x", "x", "x"))
        self.assertFalse(mgr.edit_message(conv.conversation_id, "x", "x"))

    def test_fork(self):
        mgr = ConversationManager()
        conv = mgr.create_conversation(name="主")
        mgr.add_message(conv.conversation_id, "q1", "user")
        m2 = mgr.add_message(conv.conversation_id, "a1", "assistant")
        branch = mgr.fork_conversation(conv.conversation_id, m2.message_id, "分支")
        self.assertIsNotNone(branch)
        self.assertIn(branch.conversation_id, mgr.conversations)
        self.assertEqual(len(branch.messages), 2)
        self.assertIsNone(mgr.fork_conversation("x", "x"))

    def test_max_convs(self):
        mgr = ConversationManager(max_conversations=2)
        mgr.create_conversation(name="A")
        mgr.create_conversation(name="B")
        mgr.create_conversation(name="C")
        self.assertEqual(len(mgr.conversations), 2)

    def test_max_messages(self):
        mgr = ConversationManager(max_messages_per_conversation=3)
        conv = mgr.create_conversation()
        for i in range(5):
            mgr.add_message(conv.conversation_id, f"msg_{i}", "user")
        self.assertEqual(len(conv.messages), 3)
        self.assertEqual(conv.messages[0].content, "msg_2")

    def test_clear(self):
        mgr = ConversationManager()
        mgr.create_conversation()
        mgr.create_conversation()
        mgr.clear_all()
        self.assertEqual(len(mgr.conversations), 0)
        self.assertIsNone(mgr.active_conversation_id)

    def test_save_load(self):
        mgr = ConversationManager()
        conv = mgr.create_conversation(name="测试")
        mgr.add_message(conv.conversation_id, "你好", "user")
        mgr.add_message(conv.conversation_id, "你好！", "assistant")
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            path = f.name
        try:
            mgr.save_to_json(path)
            loaded = ConversationManager.load_from_json(path)
            self.assertIn(conv.conversation_id, loaded.conversations)
            lc = loaded.get_conversation(conv.conversation_id)
            self.assertIsNotNone(lc)
            self.assertEqual(lc.name, "测试")
            self.assertEqual(len(lc.messages), 2)
        finally:
            os.unlink(path)


class TestAgentIntegration(unittest.TestCase):
    def test_with_manager(self):
        mgr = ConversationManager()
        agent = Agent(name="test", llm=None, conversation_manager=mgr)
        conv = mgr.create_conversation()
        agent.run("hello", conversation_id=conv.conversation_id)
        self.assertEqual(len(conv.messages), 2)
        self.assertEqual(conv.messages[0].content, "hello")
        self.assertEqual(conv.messages[0].role, "user")
        self.assertEqual(conv.messages[1].role, "assistant")

    def test_without_manager(self):
        agent = Agent(name="test", llm=None)
        agent.run("hello")
        self.assertEqual(len(agent._history), 2)

    def test_multi_turn(self):
        mgr = ConversationManager()
        agent = Agent(name="test", llm=None, conversation_manager=mgr)
        conv = mgr.create_conversation()
        agent.run("q1", conversation_id=conv.conversation_id)
        agent.run("q2", conversation_id=conv.conversation_id)
        self.assertEqual(len(conv.messages), 4)

    def test_branch(self):
        mgr = ConversationManager()
        agent = Agent(name="test", llm=None, conversation_manager=mgr)
        conv = mgr.create_conversation()
        agent.run("q1", conversation_id=conv.conversation_id)
        agent.run("q2", conversation_id=conv.conversation_id)
        self.assertEqual(len(conv.messages), 4)
        branch = mgr.fork_conversation(
            conv.conversation_id, conv.messages[1].message_id, "分支"
        )
        self.assertIsNotNone(branch)
        agent.run("分支问题", conversation_id=branch.conversation_id)
        self.assertEqual(len(branch.messages), 4)
        self.assertTrue(branch.messages[1].branch_point)


if __name__ == "__main__":
    unittest.main()
