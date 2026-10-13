import os
import sys
import tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.code_parser import parse_file


def _write(tmpdir, name, content):
    path = os.path.join(tmpdir, name)
    with open(path, "w") as f:
        f.write(content)
    return path


def test_parse_python_class_and_methods():
    with tempfile.TemporaryDirectory() as tmp:
        src = (
            "class AuthService:\n"
            "    def login(self, user, password):\n"
            "        return JwtUtil.generate(user)\n"
        )
        path = _write(tmp, "auth.py", src)
        entities = parse_file(path, "auth.py", "python")
        types = [e.type for e in entities]
        names = [e.name for e in entities]
        assert "File" in types
        assert "Class" in types
        assert "AuthService" in names
        method = next(e for e in entities if e.type == "Method")
        assert method.name == "login"
        assert "generate" in method.calls


def test_parse_python_imports():
    with tempfile.TemporaryDirectory() as tmp:
        src = "import os\nfrom typing import List\n"
        path = _write(tmp, "m.py", src)
        entities = parse_file(path, "m.py", "python")
        file_entity = entities[0]
        assert "os" in file_entity.imports
        assert any("List" in i for i in file_entity.imports)


def test_parse_java_class_extends():
    with tempfile.TemporaryDirectory() as tmp:
        src = "public class LoginController extends BaseController {\n  public void login() {\n  }\n}\n"
        path = _write(tmp, "LoginController.java", src)
        entities = parse_file(path, "LoginController.java", "java")
        cls = next(e for e in entities if e.type == "Class")
        assert cls.name == "LoginController"
        assert "BaseController" in cls.extends


def test_parse_js_function():
    with tempfile.TemporaryDirectory() as tmp:
        src = "function loginUser(u, p) {\n  return authService.check(u, p);\n}\n"
        path = _write(tmp, "auth.js", src)
        entities = parse_file(path, "auth.js", "javascript")
        fn = next(e for e in entities if e.type == "Function")
        assert fn.name == "loginUser"
