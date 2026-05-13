import sys
sys.path.insert(0, '.')
from unittest.mock import MagicMock

def _make_response(text="", fn_calls=None):
    parts = []
    for name, args in (fn_calls or []):
        fc = MagicMock()
        fc.name = name
        fc.args = args
        part = MagicMock()
        part.function_call = fc
        parts.append(part)
    if not parts:
        part = MagicMock()
        part.function_call = None
        parts.append(part)
    content = MagicMock()
    content.parts = parts
    candidate = MagicMock()
    candidate.content = content
    resp = MagicMock()
    resp.candidates = [candidate]
    resp.text = text
    return resp

resp = _make_response(fn_calls=[("list_file_types", {})])
print("candidates:", resp.candidates)
print("parts:", resp.candidates[0].content.parts)
for p in resp.candidates[0].content.parts:
    print("part:", p)
    print("function_call:", p.function_call)
    print("getattr:", getattr(p, "function_call", None))
    print("truthy:", bool(getattr(p, "function_call", None)))
    if getattr(p, "function_call", None):
        print("name:", p.function_call.name)
        print("name truthy:", bool(p.function_call.name))

fn_calls_list = [
    p.function_call
    for p in resp.candidates[0].content.parts
    if getattr(p, "function_call", None) and p.function_call.name
]
print("fn_calls:", fn_calls_list)
