"""
Project type detection module.

Automatically detects project type based on files and folder structure.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set
import json

from .config import ProjectType


@dataclass
class ProjectAnalysis:
    """Result of project analysis."""
    project_type: ProjectType = ProjectType.UNKNOWN
    frameworks: List[str] = field(default_factory=list)
    languages: List[str] = field(default_factory=list)
    has_frontend: bool = False
    has_backend: bool = False
    is_monorepo: bool = False
    package_manager: Optional[str] = None
    suggested_extensions: List[str] = field(default_factory=list)
    suggested_excludes: Set[str] = field(default_factory=set)


# Framework detection patterns
FRONTEND_INDICATORS = {
    "react": ["react", "react-dom", "next", "@remix-run/react"],
    "vue": ["vue", "nuxt", "@vue/cli-service"],
    "angular": ["@angular/core", "@angular/cli"],
    "svelte": ["svelte", "@sveltejs/kit"],
    "solid": ["solid-js"],
}

BACKEND_INDICATORS = {
    "nestjs": ["@nestjs/core", "@nestjs/common"],
    "express": ["express"],
    "fastify": ["fastify"],
    "koa": ["koa"],
    "django": None,  # Python - checked via requirements.txt
    "flask": None,
    "fastapi": None,
}

PYTHON_INDICATORS = {
    "django": ["django", "Django"],
    "flask": ["flask", "Flask"],
    "fastapi": ["fastapi", "FastAPI"],
    "pytorch": ["torch", "pytorch"],
    "tensorflow": ["tensorflow"],
}


def _read_package_json(path: Path) -> Optional[Dict]:
    """Read and parse package.json if exists."""
    pj = path / "package.json"
    if pj.exists():
        try:
            with pj.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None


def _read_requirements(path: Path) -> List[str]:
    """Read requirements.txt or pyproject.toml for Python deps."""
    deps = []
    
    req = path / "requirements.txt"
    if req.exists():
        try:
            with req.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        # Extract package name (before ==, >=, etc.)
                        pkg = line.split("==")[0].split(">=")[0].split("<=")[0].split("[")[0]
                        deps.append(pkg.strip().lower())
        except Exception:
            pass
    
    pyproject = path / "pyproject.toml"
    if pyproject.exists():
        try:
            content = pyproject.read_text(encoding="utf-8")
            # Simple extraction - for more robust, use toml lib
            if "django" in content.lower():
                deps.append("django")
            if "flask" in content.lower():
                deps.append("flask")
            if "fastapi" in content.lower():
                deps.append("fastapi")
        except Exception:
            pass
    
    return deps


def _get_all_deps(pkg_json: Optional[Dict]) -> Set[str]:
    """Get all dependencies from package.json."""
    if not pkg_json:
        return set()
    
    deps = set()
    for key in ["dependencies", "devDependencies", "peerDependencies"]:
        if key in pkg_json:
            deps.update(pkg_json[key].keys())
    return deps


def _detect_package_manager(path: Path) -> Optional[str]:
    """Detect which package manager is being used."""
    if (path / "pnpm-lock.yaml").exists():
        return "pnpm"
    if (path / "yarn.lock").exists():
        return "yarn"
    if (path / "package-lock.json").exists():
        return "npm"
    if (path / "bun.lockb").exists():
        return "bun"
    if (path / "requirements.txt").exists() or (path / "pyproject.toml").exists():
        return "pip"
    if (path / "Pipfile").exists():
        return "pipenv"
    if (path / "poetry.lock").exists():
        return "poetry"
    return None


def _detect_monorepo(path: Path, pkg_json: Optional[Dict]) -> bool:
    """Check if project is a monorepo."""
    # Check for common monorepo patterns
    if pkg_json:
        if "workspaces" in pkg_json:
            return True
    
    # Check for monorepo tools
    monorepo_files = ["pnpm-workspace.yaml", "lerna.json", "nx.json", "turbo.json"]
    for f in monorepo_files:
        if (path / f).exists():
            return True
    
    # Check for apps/packages structure
    if (path / "apps").is_dir() or (path / "packages").is_dir():
        return True
    
    return False


def analyze_project(project_root: Path) -> ProjectAnalysis:
    """
    Analyze a project directory and detect its type, frameworks, and languages.
    
    Args:
        project_root: Path to the project root directory.
        
    Returns:
        ProjectAnalysis with detected information.
    """
    result = ProjectAnalysis()
    
    pkg_json = _read_package_json(project_root)
    py_deps = _read_requirements(project_root)
    all_deps = _get_all_deps(pkg_json)
    
    result.package_manager = _detect_package_manager(project_root)
    result.is_monorepo = _detect_monorepo(project_root, pkg_json)
    
    # Detect frontend frameworks
    for framework, indicators in FRONTEND_INDICATORS.items():
        if any(ind in all_deps for ind in indicators):
            result.has_frontend = True
            result.frameworks.append(framework)
            if "javascript" not in result.languages:
                result.languages.append("javascript")
            if "typescript" not in result.languages and (
                "typescript" in all_deps or list(project_root.glob("**/*.ts"))
            ):
                result.languages.append("typescript")
    
    # Detect backend frameworks (Node.js)
    for framework, indicators in BACKEND_INDICATORS.items():
        if indicators and any(ind in all_deps for ind in indicators):
            result.has_backend = True
            if framework not in result.frameworks:
                result.frameworks.append(framework)
    
    # Detect Python projects
    if py_deps:
        result.languages.append("python")
        for framework, indicators in PYTHON_INDICATORS.items():
            if any(ind in py_deps for ind in [i.lower() for i in indicators]):
                result.frameworks.append(framework)
                result.has_backend = True
    
    # Check for Python files if no requirements.txt
    if not py_deps and list(project_root.glob("*.py")):
        if "python" not in result.languages:
            result.languages.append("python")
    
    # Determine project type
    if result.has_frontend and result.has_backend:
        result.project_type = ProjectType.FULLSTACK
    elif result.has_frontend:
        result.project_type = ProjectType.FRONTEND
    elif result.has_backend:
        result.project_type = ProjectType.BACKEND
    elif "python" in result.languages:
        result.project_type = ProjectType.PYTHON
    else:
        result.project_type = ProjectType.UNKNOWN
    
    # Suggest file extensions based on detected languages
    if "typescript" in result.languages:
        result.suggested_extensions.extend([".ts", ".tsx"])
    if "javascript" in result.languages:
        result.suggested_extensions.extend([".js", ".jsx"])
    if "python" in result.languages:
        result.suggested_extensions.extend([".py", ".pyi"])
    
    # Add config files if web project
    if "typescript" in result.languages or "javascript" in result.languages:
        result.suggested_extensions.extend([".json", ".yaml", ".yml", ".env"])
    
    # Suggest excludes based on project type
    base_excludes = {"node_modules", ".git", "__pycache__", ".cache", "dist", "build"}
    result.suggested_excludes.update(base_excludes)
    
    if "react" in result.frameworks or "next" in str(result.frameworks):
        result.suggested_excludes.update({".next", ".vercel"})
    if "nestjs" in result.frameworks:
        result.suggested_excludes.add("dist")
    if result.is_monorepo:
        result.suggested_excludes.update({".nx", ".turbo"})
    if "python" in result.languages:
        result.suggested_excludes.update({"venv", ".venv", ".mypy_cache", ".pytest_cache", "htmlcov"})
    
    return result


def get_suggested_extensions_for_type(project_type: ProjectType) -> List[str]:
    """Get suggested file extensions for a project type."""
    mapping = {
        ProjectType.FRONTEND: [".ts", ".tsx", ".js", ".jsx", ".vue", ".svelte", ".css", ".scss"],
        ProjectType.BACKEND: [".ts", ".js", ".py", ".go", ".rs", ".java", ".json", ".yaml"],
        ProjectType.FULLSTACK: [".ts", ".tsx", ".js", ".jsx", ".py", ".json", ".yaml", ".env"],
        ProjectType.PYTHON: [".py", ".pyi", ".json", ".yaml", ".toml", ".ini"],
        ProjectType.UNKNOWN: [".ts", ".tsx", ".js", ".jsx", ".py", ".json", ".md"],
    }
    return mapping.get(project_type, mapping[ProjectType.UNKNOWN])
