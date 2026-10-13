import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.config import settings
settings.graph_backend = "networkx"  # force fallback backend so tests need no external DB

from app.services import graph_store
from app.services.code_parser import CodeEntity, new_id


def _sample_entities():
    file_id = new_id()
    controller_id = new_id()
    service_id = new_id()
    login_method_id = new_id()
    check_method_id = new_id()

    file_ent = CodeEntity(id=file_id, type="File", name="app.py", file_path="app.py", start_line=1, end_line=50)
    controller = CodeEntity(id=controller_id, type="Class", name="LoginController", file_path="app.py",
                             start_line=1, end_line=20, parent_id=file_id)
    service = CodeEntity(id=service_id, type="Class", name="AuthService", file_path="app.py",
                          start_line=21, end_line=40, parent_id=file_id)
    login_method = CodeEntity(id=login_method_id, type="Method", name="login", file_path="app.py",
                               start_line=2, end_line=5, parent_id=controller_id, calls=["check"])
    check_method = CodeEntity(id=check_method_id, type="Method", name="check", file_path="app.py",
                               start_line=22, end_line=25, parent_id=service_id)
    return [file_ent, controller, service, login_method, check_method]


def test_build_graph_and_stats():
    entities = _sample_entities()
    graph_store.build_graph("repo-test-1", entities)
    stats = graph_store.get_stats("repo-test-1")
    assert stats["num_files"] == 1
    assert stats["num_classes"] == 2
    assert stats["num_functions"] == 2
    assert stats["num_relationships"] > 0


def test_calls_relationship_expansion():
    entities = _sample_entities()
    graph_store.build_graph("repo-test-2", entities)
    login_id = next(e.id for e in entities if e.name == "login")
    neighbors = graph_store.expand_neighbors("repo-test-2", {login_id}, hops=1)
    names = [n["name"] for n in neighbors]
    assert "check" in names
