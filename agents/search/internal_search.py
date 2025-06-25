# search/internal_search.py

import os
import re
import ast
from pathlib import Path
from typing import List, Dict, Any, Optional
from langchain_core.tools import tool
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import json


class InternalSearchEngine:
    def __init__(self, workspace_path: str):
        self.workspace_path = Path(workspace_path)
        self.embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        self.supported_extensions = {'.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.hpp', 
                                   '.go', '.rs', '.rb', '.php', '.cs', '.swift', '.kt', 
                                   '.md', '.txt', '.json', '.yaml', '.yml', '.toml', '.ini'}
    
    def _is_binary_file(self, file_path: Path) -> bool:
        """Check if file is binary"""
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(1024)
                return b'\0' in chunk
        except:
            return True
    
    def _read_file_content(self, file_path: Path) -> Optional[str]:
        """Safely read file content"""
        try:
            if self._is_binary_file(file_path):
                return None
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return None
    
    def _extract_code_structure(self, content: str, file_path: Path) -> Dict[str, Any]:
        """Extract code structure (functions, classes, imports) for Python files"""
        structure = {"functions": [], "classes": [], "imports": [], "variables": []}
        
        if file_path.suffix != '.py':
            return structure
        
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    structure["functions"].append({
                        "name": node.name,
                        "line": node.lineno,
                        "args": [arg.arg for arg in node.args.args],
                        "docstring": ast.get_docstring(node)
                    })
                elif isinstance(node, ast.ClassDef):
                    structure["classes"].append({
                        "name": node.name,
                        "line": node.lineno,
                        "methods": [n.name for n in node.body if isinstance(n, ast.FunctionDef)],
                        "docstring": ast.get_docstring(node)
                    })
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            structure["imports"].append(alias.name)
                    else:
                        module = node.module or ""
                        for alias in node.names:
                            structure["imports"].append(f"{module}.{alias.name}")
                elif isinstance(node, ast.Assign):
                    target = node.targets[0]
                    if isinstance(target, ast.Name):
                        structure["variables"].append(target.id)
        except Exception as e:
            print(f"Error parsing AST for {file_path}: {e}")
        
        return structure
    
    def index_workspace(self) -> Dict[str, Any]:
        """Index all files in workspace"""
        file_index = {}
        
        for file_path in self.workspace_path.rglob('*'):
            if (file_path.is_file() and 
                file_path.suffix in self.supported_extensions and
                not any(ignore in str(file_path) for ignore in ['.git', '__pycache__', 'node_modules', '.venv'])):
                
                content = self._read_file_content(file_path)
                if content:
                    relative_path = str(file_path.relative_to(self.workspace_path))
                    
                    file_index[relative_path] = {
                        "path": str(file_path),
                        "size": len(content),
                        "lines": len(content.split('\n')),
                        "extension": file_path.suffix,
                        "content": content,
                        "structure": self._extract_code_structure(content, file_path)
                    }
        
        return file_index
    
    def search_by_content(self, query: str, file_index: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search files by content similarity"""
        results = []
        query_lower = query.lower()
        
        for file_path, file_info in file_index.items():
            content = file_info['content'].lower()
            
            # Simple relevance scoring
            score = 0
            
            # Exact match bonus
            if query_lower in content:
                score += 10
            
            # Word matching
            query_words = query_lower.split()
            for word in query_words:
                if word in content:
                    score += content.count(word)
            
            # Function/class name matching
            structure = file_info['structure']
            for func in structure.get('functions', []):
                if query_lower in func['name'].lower():
                    score += 20
            
            for cls in structure.get('classes', []):
                if query_lower in cls['name'].lower():
                    score += 20
            
            if score > 0:
                results.append({
                    "file_path": file_path,
                    "relevance_score": score,
                    "content_preview": file_info['content'][:500],
                    "structure": structure,
                    "file_info": {
                        "size": file_info['size'],
                        "lines": file_info['lines'],
                        "extension": file_info['extension']
                    }
                })
        
        return sorted(results, key=lambda x: x['relevance_score'], reverse=True)
    
    def search_by_filename(self, query: str, file_index: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search files by filename"""
        results = []
        query_lower = query.lower()
        
        for file_path, file_info in file_index.items():
            filename = Path(file_path).name.lower()
            
            score = 0
            if query_lower in filename:
                score = 100 - len(filename)  # Shorter matches get higher scores
                
                results.append({
                    "file_path": file_path,
                    "relevance_score": score,
                    "content_preview": file_info['content'][:500],
                    "structure": file_info['structure'],
                    "file_info": {
                        "size": file_info['size'],
                        "lines": file_info['lines'],
                        "extension": file_info['extension']
                    }
                })
        
        return sorted(results, key=lambda x: x['relevance_score'], reverse=True)
    
    def search_by_structure(self, query: str, file_index: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search for functions, classes, or imports"""
        results = []
        query_lower = query.lower()
        
        for file_path, file_info in file_index.items():
            structure = file_info['structure']
            score = 0
            matches = []
            
            # Search functions
            for func in structure.get('functions', []):
                if query_lower in func['name'].lower():
                    score += 30
                    matches.append(f"Function: {func['name']} (line {func['line']})")
            
            # Search classes
            for cls in structure.get('classes', []):
                if query_lower in cls['name'].lower():
                    score += 30
                    matches.append(f"Class: {cls['name']} (line {cls['line']})")
            
            # Search imports
            for imp in structure.get('imports', []):
                if query_lower in imp.lower():
                    score += 15
                    matches.append(f"Import: {imp}")
            
            if score > 0:
                results.append({
                    "file_path": file_path,
                    "relevance_score": score,
                    "matches": matches,
                    "content_preview": file_info['content'][:500],
                    "structure": structure,
                    "file_info": {
                        "size": file_info['size'],
                        "lines": file_info['lines'],
                        "extension": file_info['extension']
                    }
                })
        
        return sorted(results, key=lambda x: x['relevance_score'], reverse=True)


@tool
def internal_search(query: str, workspace_path: str, search_type: str = "content") -> str:
    """
    Search within the workspace codebase for relevant files and code structures.
    
    Args:
        query: The search query
        workspace_path: Path to the workspace directory
        search_type: Type of search - "content", "filename", "structure", or "all"
    
    Returns:
        JSON string with search results
    """
    try:
        engine = InternalSearchEngine(workspace_path)
        file_index = engine.index_workspace()
        
        all_results = []
        
        if search_type in ["content", "all"]:
            content_results = engine.search_by_content(query, file_index)
            all_results.extend(content_results)
        
        if search_type in ["filename", "all"]:
            filename_results = engine.search_by_filename(query, file_index)
            all_results.extend(filename_results)
        
        if search_type in ["structure", "all"]:
            structure_results = engine.search_by_structure(query, file_index)
            all_results.extend(structure_results)
        
        # Remove duplicates and sort by relevance
        seen_files = set()
        unique_results = []
        for result in sorted(all_results, key=lambda x: x['relevance_score'], reverse=True):
            if result['file_path'] not in seen_files:
                seen_files.add(result['file_path'])
                unique_results.append(result)
        
        return json.dumps({
            "query": query,
            "search_type": search_type,
            "total_files_indexed": len(file_index),
            "results_count": len(unique_results),
            "results": unique_results[:10]  # Top 10 results
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "query": query,
            "results": []
        })