import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.code_parser import CodeEntity, new_id
from app.services.chunker import build_chunks


def test_build_chunks_skips_file_entities():
    file_id = new_id()
    file_ent = CodeEntity(id=file_id, type="File", name="a.py", file_path="a.py", start_line=1, end_line=10)
    fn_ent = CodeEntity(id=new_id(), type="Function", name="foo", file_path="a.py",
                         start_line=1, end_line=3, parent_id=file_id, language="python",
                         signature="def foo():", source="def foo():\n    return 1\n")
    chunks = build_chunks([file_ent, fn_ent])
    assert len(chunks) == 1
    assert chunks[0].entity_name == "foo"
    assert "foo" in chunks[0].text


def test_build_chunks_splits_long_entity():
    long_source = "\n".join(f"line {i}" for i in range(200))
    fn_ent = CodeEntity(id=new_id(), type="Function", name="bigfn", file_path="b.py",
                         start_line=1, end_line=200, language="python", source=long_source)
    chunks = build_chunks([fn_ent])
    assert len(chunks) > 1
