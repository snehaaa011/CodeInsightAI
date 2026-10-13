"""
CodeInsight AI - Code Analysis / Parsing
NEW (CodeInsight AI) implementation, conceptually aligned with CodeRAG's
entity/relationship model (File, Class, Function/Method + CONTAINS, IMPORTS,
CALLS, EXTENDS, IMPLEMENTS, DEFINED_IN) since the original CodeRAG TypeScript
parser internals were not accessible in this environment (see README).

Python files are parsed with the real `ast` module (accurate).
JS/TS/Java files are parsed with documented regex heuristics (best-effort;
this is a deliberate, documented simplification vs. CodeRAG's tree-sitter/
ts-morph based parsing, acceptable for an academic-scope demonstration).
"""
import ast
import os
import re
import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class CodeEntity:
    id: str
    type: str            # File | Class | Interface | Function | Method
    name: str
    file_path: str
    start_line: int
    end_line: int
    parent_id: Optional[str] = None
    language: str = ""
    signature: str = ""
    source: str = ""
    calls: List[str] = field(default_factory=list)      # names of functions/methods called
    extends: List[str] = field(default_factory=list)    # base class names
    implements: List[str] = field(default_factory=list)  # interface names
    imports: List[str] = field(default_factory=list)


def new_id() -> str:
    return uuid.uuid4().hex[:12]




def parse_python_file(file_path: str, rel_path: str, source: str) -> List[CodeEntity]:
    entities: List[CodeEntity] = []
    file_id = new_id()
    lines = source.splitlines()
    file_entity = CodeEntity(
        id=file_id, type="File", name=os.path.basename(file_path),
        file_path=rel_path, start_line=1, end_line=len(lines) or 1,
        language="python", source=""
    )
    entities.append(file_entity)

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return entities

    # imports
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            for alias in node.names:
                imports.append(f"{mod}.{alias.name}" if mod else alias.name)
    file_entity.imports = imports

    def get_calls(fn_node) -> List[str]:
        calls = []
        for n in ast.walk(fn_node):
            if isinstance(n, ast.Call):
                if isinstance(n.func, ast.Name):
                    calls.append(n.func.id)
                elif isinstance(n.func, ast.Attribute):
                    calls.append(n.func.attr)
        return calls

    def get_snippet(node) -> str:
        start = getattr(node, "lineno", 1) - 1
        end = getattr(node, "end_lineno", start + 1)
        return "\n".join(lines[start:end])

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            class_id = new_id()
            bases = []
            for b in node.bases:
                if isinstance(b, ast.Name):
                    bases.append(b.id)
                elif isinstance(b, ast.Attribute):
                    bases.append(b.attr)
            class_entity = CodeEntity(
                id=class_id, type="Class", name=node.name, file_path=rel_path,
                start_line=node.lineno, end_line=getattr(node, "end_lineno", node.lineno),
                parent_id=file_id, language="python", extends=bases,
                signature=f"class {node.name}({', '.join(bases)})",
                source=get_snippet(node)
            )
            entities.append(class_entity)
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    args = [a.arg for a in item.args.args]
                    method_entity = CodeEntity(
                        id=new_id(), type="Method", name=item.name, file_path=rel_path,
                        start_line=item.lineno, end_line=getattr(item, "end_lineno", item.lineno),
                        parent_id=class_id, language="python",
                        signature=f"def {item.name}({', '.join(args)})",
                        source=get_snippet(item), calls=get_calls(item)
                    )
                    entities.append(method_entity)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = [a.arg for a in node.args.args]
            fn_entity = CodeEntity(
                id=new_id(), type="Function", name=node.name, file_path=rel_path,
                start_line=node.lineno, end_line=getattr(node, "end_lineno", node.lineno),
                parent_id=file_id, language="python",
                signature=f"def {node.name}({', '.join(args)})",
                source=get_snippet(node), calls=get_calls(node)
            )
            entities.append(fn_entity)

    return entities




_CLASS_RE = {
    "java": re.compile(r'\b(?:public|private|protected)?\s*(?:abstract\s+)?class\s+(\w+)'
                        r'(?:\s+extends\s+(\w+))?(?:\s+implements\s+([\w,\s]+))?'),
    "javascript": re.compile(r'\bclass\s+(\w+)(?:\s+extends\s+(\w+))?'),
    "typescript": re.compile(r'\bclass\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([\w,\s]+))?'),
}
_INTERFACE_RE = re.compile(r'\binterface\s+(\w+)(?:\s+extends\s+([\w,\s]+))?')
_FUNCTION_RE = {
    "javascript": re.compile(r'\bfunction\s+(\w+)\s*\('),
    "typescript": re.compile(r'\bfunction\s+(\w+)\s*\('),
    "java": re.compile(r'\b(?:public|private|protected|static|final)\s+[\w<>\[\]]+\s+(\w+)\s*\([^;{]*\)\s*\{'),
}
_METHOD_JS_RE = re.compile(r'^\s*(?:async\s+)?(\w+)\s*\([^)]*\)\s*\{')
_IMPORT_RE = {
    "javascript": re.compile(r'\bimport\s+.*?from\s+[\'"]([^\'"]+)[\'"]|require\([\'"]([^\'"]+)[\'"]\)'),
    "typescript": re.compile(r'\bimport\s+.*?from\s+[\'"]([^\'"]+)[\'"]'),
    "java": re.compile(r'\bimport\s+([\w.]+);'),
}
_CALL_RE = re.compile(r'\b([A-Za-z_]\w*)\s*\(')


def _extract_block(all_lines: List[str], start_idx: int) -> (int, str):
    """Given a 0-indexed line containing an opening '{', return (end_idx, text) of the balanced block."""
    depth = 0
    collected = []
    started = False
    for i in range(start_idx, min(start_idx + 400, len(all_lines))):
        line = all_lines[i]
        collected.append(line)
        depth += line.count("{") - line.count("}")
        if "{" in line:
            started = True
        if started and depth <= 0:
            return i, "\n".join(collected)
    return min(start_idx + 400, len(all_lines) - 1), "\n".join(collected)


def parse_generic_file(file_path: str, rel_path: str, source: str, language: str) -> List[CodeEntity]:
    entities: List[CodeEntity] = []
    lines = source.splitlines()
    file_id = new_id()
    file_entity = CodeEntity(
        id=file_id, type="File", name=os.path.basename(file_path),
        file_path=rel_path, start_line=1, end_line=len(lines) or 1, language=language
    )
    entities.append(file_entity)

    imports = []
    import_re = _IMPORT_RE.get(language)
    if import_re:
        for m in import_re.finditer(source):
            groups = [g for g in m.groups() if g]
            if groups:
                imports.append(groups[0])
    file_entity.imports = imports

    class_re = _CLASS_RE.get(language)
    if class_re:
        for m in class_re.finditer(source):
            name = m.group(1)
            extends = [m.group(2)] if m.lastindex and m.lastindex >= 2 and m.group(2) else []
            implements = []
            if m.lastindex and m.lastindex >= 3 and m.group(3):
                implements = [x.strip() for x in m.group(3).split(",") if x.strip()]
            start_line = source[:m.start()].count("\n") + 1
            start_idx = start_line - 1
            end_idx, block_text = _extract_block(lines, start_idx)
            class_id = new_id()
            entities.append(CodeEntity(
                id=class_id, type="Class", name=name, file_path=rel_path,
                start_line=start_line, end_line=end_idx + 1, parent_id=file_id,
                language=language, extends=extends, implements=implements,
                signature=m.group(0), source=block_text
            ))
            # naive method extraction inside the class block for JS/TS
            if language in ("javascript", "typescript"):
                block_lines = block_text.splitlines()
                for j, bl in enumerate(block_lines[1:], start=1):
                    mm = _METHOD_JS_RE.match(bl)
                    if mm and mm.group(1) not in ("if", "for", "while", "switch", "catch"):
                        m_start = start_line + j
                        m_end_idx, m_text = _extract_block(block_lines, j)
                        calls = list(set(_CALL_RE.findall(m_text)) - {mm.group(1)})
                        entities.append(CodeEntity(
                            id=new_id(), type="Method", name=mm.group(1), file_path=rel_path,
                            start_line=m_start, end_line=start_line + m_end_idx,
                            parent_id=class_id, language=language,
                            signature=bl.strip(), source=m_text, calls=calls
                        ))

    if language == "java":
        # methods inside classes: naive scan for method signatures with a following '{'
        for m in _FUNCTION_RE["java"].finditer(source):
            name = m.group(1)
            start_line = source[:m.start()].count("\n") + 1
            start_idx = start_line - 1
            end_idx, block_text = _extract_block(lines, start_idx)
            calls = list(set(_CALL_RE.findall(block_text)) - {name})
            entities.append(CodeEntity(
                id=new_id(), type="Method", name=name, file_path=rel_path,
                start_line=start_line, end_line=end_idx + 1, parent_id=file_id,
                language=language, signature=m.group(0), source=block_text, calls=calls
            ))
    else:
        fn_re = _FUNCTION_RE.get(language)
        if fn_re:
            for m in fn_re.finditer(source):
                name = m.group(1)
                start_line = source[:m.start()].count("\n") + 1
                start_idx = start_line - 1
                end_idx, block_text = _extract_block(lines, start_idx)
                calls = list(set(_CALL_RE.findall(block_text)) - {name})
                entities.append(CodeEntity(
                    id=new_id(), type="Function", name=name, file_path=rel_path,
                    start_line=start_line, end_line=end_idx + 1, parent_id=file_id,
                    language=language, signature=m.group(0), source=block_text, calls=calls
                ))

    for iface_m in _INTERFACE_RE.finditer(source):
        name = iface_m.group(1)
        extends = [x.strip() for x in (iface_m.group(2) or "").split(",") if x.strip()]
        start_line = source[:iface_m.start()].count("\n") + 1
        entities.append(CodeEntity(
            id=new_id(), type="Interface", name=name, file_path=rel_path,
            start_line=start_line, end_line=start_line, parent_id=file_id,
            language=language, extends=extends, signature=iface_m.group(0)
        ))

    return entities


def parse_file(file_path: str, rel_path: str, language: str) -> List[CodeEntity]:
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            source = f.read()
    except Exception:
        return []
    if language == "python":
        return parse_python_file(file_path, rel_path, source)
    return parse_generic_file(file_path, rel_path, source, language)
