import sys
from unittest.mock import MagicMock, patch
import os

# Create dummy modules for google and google.genai
mock_google = MagicMock()
mock_genai = MagicMock()
mock_types = MagicMock()

sys.modules['google'] = mock_google
sys.modules['google.genai'] = mock_genai
sys.modules['google.genai.types'] = mock_types

sys.path.insert(0, '.')
os.environ['GEMINI_API_KEY'] = 'test-key'

import src.llm_agent as llm_module
llm_module.genai = mock_genai
llm_module.types = mock_types
llm_module.get_gemini_tool_declarations = lambda: []
llm_module.load_dotenv = lambda: None

agent = llm_module.CBOAgent(api_key='test-key')
print("Agent created:", agent)
print("_client:", agent._client)
print("expected client:", mock_genai.Client.return_value)
print("same?", agent._client is mock_genai.Client.return_value)

chat_mock = mock_genai.Client.return_value.chats.create.return_value
print("chat_mock:", chat_mock)

def _make_fn_call_response(name, args):
    fc = MagicMock()
    fc.name = name
    fc.args = args
    part = MagicMock()
    part.function_call = fc
    content = MagicMock()
    content.parts = [part]
    candidate = MagicMock()
    candidate.content = content
    resp = MagicMock()
    resp.candidates = [candidate]
    resp.text = ""
    return resp

def _make_text_response(text):
    part = MagicMock()
    part.function_call = None
    content = MagicMock()
    content.parts = [part]
    candidate = MagicMock()
    candidate.content = content
    resp = MagicMock()
    resp.candidates = [candidate]
    resp.text = text
    return resp

chat_mock.send_message.side_effect = [
    _make_fn_call_response("list_file_types", {}),
    _make_text_response("done"),
]

llm_module.get_tool = lambda name: lambda **_: [{"file_type": "x"}]

result = agent.ask("list types")
print("result:", result)
print("last_trace:", agent.last_trace)
print("len:", len(agent.last_trace))
