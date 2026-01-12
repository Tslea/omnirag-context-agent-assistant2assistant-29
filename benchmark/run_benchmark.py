"""
Benchmark Runner: Copilot con vs senza OMNI

Questo script simula il workflow di Copilot per completare una serie
di task sequenziali e misura:
- Token consumati (input/output)
- Tempo di elaborazione
- Qualità del contesto

NON chiama realmente Copilot API - simula il costo in token
basandosi su cosa Copilot dovrebbe leggere per avere contesto.
"""

import json
import os
import sys
import time
import yaml
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class TokenEstimate:
    """Stima dei token per un testo."""
    text: str
    tokens: int
    
    @classmethod
    def from_text(cls, text: str) -> "TokenEstimate":
        """Stima token (approssimazione: 1 token ≈ 4 caratteri)."""
        # Più accurato sarebbe usare tiktoken, ma questa è una buona approssimazione
        tokens = len(text) // 4
        return cls(text=text, tokens=tokens)


@dataclass
class TaskResult:
    """Risultato di un singolo task."""
    task_id: str
    task_name: str
    scenario: str  # "with_omni" o "without_omni"
    
    # Token metrics
    context_tokens: int = 0
    task_tokens: int = 0
    total_input_tokens: int = 0
    estimated_output_tokens: int = 0
    
    # Files read
    files_read: list[str] = field(default_factory=list)
    files_read_count: int = 0
    
    # Time (simulato)
    estimated_time_seconds: float = 0.0
    
    # Quality indicators
    has_full_context: bool = False
    context_summary: str = ""
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BenchmarkReport:
    """Report completo del benchmark."""
    timestamp: str
    project_name: str
    total_tasks: int
    
    results_without_omni: list[TaskResult] = field(default_factory=list)
    results_with_omni: list[TaskResult] = field(default_factory=list)
    
    # Aggregated metrics
    total_tokens_without_omni: int = 0
    total_tokens_with_omni: int = 0
    token_savings_percent: float = 0.0
    
    total_files_read_without_omni: int = 0
    total_files_read_with_omni: int = 0
    
    estimated_time_without_omni: float = 0.0
    estimated_time_with_omni: float = 0.0
    time_savings_percent: float = 0.0


class BenchmarkRunner:
    """Esegue il benchmark e raccoglie metriche."""
    
    def __init__(self, tasks_file: str, workspace_path: Optional[str] = None):
        self.tasks_file = Path(tasks_file)
        self.workspace_path = Path(workspace_path) if workspace_path else self.tasks_file.parent
        
        with open(self.tasks_file) as f:
            self.config = yaml.safe_load(f)
        
        self.tasks = self.config["tasks"]
        self.project = self.config["project"]
        
        # Simulated project files (what would exist after each task)
        self.simulated_files: dict[str, str] = {}
        
    def run(self) -> BenchmarkReport:
        """Esegue il benchmark completo."""
        print(f"\n{'='*60}")
        print(f"🚀 BENCHMARK: {self.project['name']}")
        print(f"{'='*60}")
        print(f"Stack: {self.project['stack']}")
        print(f"Tasks: {len(self.tasks)}")
        print()
        
        report = BenchmarkReport(
            timestamp=datetime.now().isoformat(),
            project_name=self.project["name"],
            total_tasks=len(self.tasks),
        )
        
        # Reset simulated files
        self.simulated_files = {}
        
        # Run each task in both scenarios
        for i, task in enumerate(self.tasks, 1):
            print(f"\n📋 Task {i}/{len(self.tasks)}: {task['name']}")
            print(f"   ID: {task['id']}")
            print(f"   Complexity: {task['complexity']}")
            
            # Simulate task completion (add expected files)
            self._simulate_task_completion(task)
            
            # Scenario 1: Without OMNI
            result_without = self._run_task_without_omni(task)
            report.results_without_omni.append(result_without)
            print(f"   📊 Without OMNI: {result_without.total_input_tokens:,} tokens, {result_without.files_read_count} files")
            
            # Scenario 2: With OMNI
            result_with = self._run_task_with_omni(task)
            report.results_with_omni.append(result_with)
            print(f"   📊 With OMNI:    {result_with.total_input_tokens:,} tokens, {result_with.files_read_count} files")
            
            # Calculate savings for this task
            if result_without.total_input_tokens > 0:
                savings = (1 - result_with.total_input_tokens / result_without.total_input_tokens) * 100
                print(f"   💰 Savings:      {savings:.1f}%")
        
        # Calculate totals
        report.total_tokens_without_omni = sum(r.total_input_tokens for r in report.results_without_omni)
        report.total_tokens_with_omni = sum(r.total_input_tokens for r in report.results_with_omni)
        
        if report.total_tokens_without_omni > 0:
            report.token_savings_percent = (
                (1 - report.total_tokens_with_omni / report.total_tokens_without_omni) * 100
            )
        
        report.total_files_read_without_omni = sum(r.files_read_count for r in report.results_without_omni)
        report.total_files_read_with_omni = sum(r.files_read_count for r in report.results_with_omni)
        
        # Estimate time (rough: 1 token ≈ 0.001s processing)
        report.estimated_time_without_omni = report.total_tokens_without_omni * 0.001
        report.estimated_time_with_omni = report.total_tokens_with_omni * 0.001
        
        if report.estimated_time_without_omni > 0:
            report.time_savings_percent = (
                (1 - report.estimated_time_with_omni / report.estimated_time_without_omni) * 100
            )
        
        return report
    
    def _simulate_task_completion(self, task: dict) -> None:
        """Simula il completamento di un task aggiungendo i file attesi."""
        for file_path in task.get("expected_files", []):
            # Genera contenuto simulato basato sul tipo di file
            content = self._generate_simulated_content(file_path, task)
            self.simulated_files[file_path] = content
    
    def _generate_simulated_content(self, file_path: str, task: dict) -> str:
        """Genera contenuto simulato per un file."""
        # Contenuti realistici basati sul tipo di file
        contents = {
            "main.py": '''"""FastAPI Application"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from config import settings
from routes import auth, users

app = FastAPI(title="Auth Benchmark App")

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/health")
async def health():
    return {"status": "ok"}
''',
            "config.py": '''"""Application Configuration"""
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    SECRET_KEY: str = "your-secret-key-change-in-production"
    DATABASE_URL: str = "sqlite:///./app.db"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    class Config:
        env_file = ".env"

settings = Settings()
''',
            "requirements.txt": '''fastapi==0.109.0
uvicorn==0.27.0
sqlalchemy==2.0.25
pydantic-settings==2.1.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
''',
            "models/user.py": '''"""User Model"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<User {self.email}>"
''',
            "database.py": '''"""Database Configuration"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import settings

engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
''',
            "auth/utils.py": '''"""Authentication Utilities"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")

def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
''',
            "routes/auth.py": '''"""Authentication Routes"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models.user import User
from schemas.auth import RegisterRequest, LoginRequest, UserResponse, TokenResponse
from auth.utils import hash_password, verify_password, create_access_token

router = APIRouter()

@router.post("/register", response_model=UserResponse)
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == request.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user = User(
        email=request.email,
        hashed_password=hash_password(request.password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token(data={"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}
''',
            "schemas/auth.py": '''"""Authentication Schemas"""
from datetime import datetime
from pydantic import BaseModel, EmailStr

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
''',
            "auth/dependencies.py": '''"""Authentication Dependencies"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError
from database import get_db
from models.user import User
from auth.utils import decode_token

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    token = credentials.credentials
    try:
        payload = decode_token(token)
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user
''',
            "routes/users.py": '''"""User Routes"""
from fastapi import APIRouter, Depends
from models.user import User
from schemas.auth import UserResponse
from auth.dependencies import get_current_user

router = APIRouter()

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
''',
            "static/login.html": '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login</title>
    <style>
        body { font-family: Arial; max-width: 400px; margin: 50px auto; padding: 20px; }
        input { width: 100%; padding: 10px; margin: 10px 0; box-sizing: border-box; }
        button { width: 100%; padding: 10px; background: #007bff; color: white; border: none; cursor: pointer; }
        .error { color: red; }
    </style>
</head>
<body>
    <h1>Login</h1>
    <form id="loginForm">
        <input type="email" id="email" placeholder="Email" required>
        <input type="password" id="password" placeholder="Password" required>
        <button type="submit">Login</button>
    </form>
    <p id="error" class="error"></p>
    <script src="/static/js/auth.js"></script>
</body>
</html>
''',
            "static/js/auth.js": '''// Authentication JavaScript

async function login(email, password) {
    const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
    });
    
    if (!response.ok) {
        throw new Error('Login failed');
    }
    
    const data = await response.json();
    localStorage.setItem('token', data.access_token);
    return data;
}

document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    
    try {
        await login(email, password);
        window.location.href = '/profile';
    } catch (error) {
        document.getElementById('error').textContent = error.message;
    }
});
''',
        }
        
        return contents.get(file_path, f"# {file_path}\n# Content for {task['name']}\n")
    
    def _run_task_without_omni(self, task: dict) -> TaskResult:
        """Simula esecuzione task SENZA OMNI (legge tutti i file)."""
        result = TaskResult(
            task_id=task["id"],
            task_name=task["name"],
            scenario="without_omni",
        )
        
        # Senza OMNI, Copilot deve leggere TUTTI i file esistenti
        context_parts = []
        
        for file_path, content in self.simulated_files.items():
            context_parts.append(f"=== {file_path} ===\n{content}\n")
            result.files_read.append(file_path)
        
        full_context = "\n".join(context_parts)
        result.context_tokens = TokenEstimate.from_text(full_context).tokens
        result.files_read_count = len(result.files_read)
        
        # Task description tokens
        task_text = f"Task: {task['name']}\n\n{task['description']}"
        result.task_tokens = TokenEstimate.from_text(task_text).tokens
        
        result.total_input_tokens = result.context_tokens + result.task_tokens
        result.estimated_output_tokens = task.get("estimated_tokens_without_context", 500)
        result.estimated_time_seconds = result.total_input_tokens * 0.001
        
        result.has_full_context = True
        result.context_summary = f"Read {result.files_read_count} raw files"
        
        return result
    
    def _run_task_with_omni(self, task: dict) -> TaskResult:
        """Simula esecuzione task CON OMNI (legge solo summaries)."""
        result = TaskResult(
            task_id=task["id"],
            task_name=task["name"],
            scenario="with_omni",
        )
        
        # Con OMNI, Copilot legge SOLO i file summary
        omni_context = self._generate_omni_summary()
        result.context_tokens = TokenEstimate.from_text(omni_context).tokens
        
        # Conta solo i file .omni/ letti
        result.files_read = [".omni/context/project-overview.md", ".omni/context/file-summaries.md"]
        result.files_read_count = len(result.files_read)
        
        # Task description tokens
        task_text = f"Task: {task['name']}\n\n{task['description']}"
        result.task_tokens = TokenEstimate.from_text(task_text).tokens
        
        result.total_input_tokens = result.context_tokens + result.task_tokens
        result.estimated_output_tokens = task.get("estimated_tokens_with_context", 500)
        result.estimated_time_seconds = result.total_input_tokens * 0.001
        
        result.has_full_context = True
        result.context_summary = f"Read {result.files_read_count} OMNI summary files"
        
        return result
    
    def _generate_omni_summary(self) -> str:
        """Genera un summary OMNI simulato per i file esistenti."""
        lines = ["# Project Overview", f"Project: {self.project['name']}", ""]
        lines.append("## File Summaries")
        
        for file_path, content in self.simulated_files.items():
            # Genera summary compatto invece del contenuto completo
            line_count = len(content.split("\n"))
            
            # Estrai info chiave
            if file_path.endswith(".py"):
                classes = [l.split("class ")[1].split("(")[0] for l in content.split("\n") if l.strip().startswith("class ")]
                funcs = [l.split("def ")[1].split("(")[0] for l in content.split("\n") if l.strip().startswith("def ") or l.strip().startswith("async def ")]
                
                lines.append(f"### {file_path}")
                lines.append(f"- Lines: {line_count}")
                if classes:
                    lines.append(f"- Classes: {', '.join(classes[:5])}")
                if funcs:
                    lines.append(f"- Functions: {', '.join(funcs[:5])}")
                lines.append("")
            else:
                lines.append(f"### {file_path}")
                lines.append(f"- Lines: {line_count}")
                lines.append("")
        
        return "\n".join(lines)
    
    def generate_report_html(self, report: BenchmarkReport) -> str:
        """Genera report HTML."""
        html = f'''<!DOCTYPE html>
<html>
<head>
    <title>Benchmark Report: {report.project_name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #333; }}
        .summary {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 20px 0; }}
        .card {{ background: #f5f5f5; padding: 20px; border-radius: 8px; text-align: center; }}
        .card h2 {{ margin: 0 0 10px 0; font-size: 2em; }}
        .card.savings {{ background: #d4edda; }}
        .card.savings h2 {{ color: #28a745; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #333; color: white; }}
        tr:hover {{ background: #f5f5f5; }}
        .bar {{ height: 20px; background: #007bff; border-radius: 4px; }}
        .bar-container {{ background: #e0e0e0; border-radius: 4px; overflow: hidden; }}
    </style>
</head>
<body>
    <h1>🚀 Benchmark Report: {report.project_name}</h1>
    <p>Generated: {report.timestamp}</p>
    
    <div class="summary">
        <div class="card">
            <h2>{report.total_tokens_without_omni:,}</h2>
            <p>Total Tokens (Without OMNI)</p>
        </div>
        <div class="card">
            <h2>{report.total_tokens_with_omni:,}</h2>
            <p>Total Tokens (With OMNI)</p>
        </div>
        <div class="card savings">
            <h2>{report.token_savings_percent:.1f}%</h2>
            <p>Token Savings</p>
        </div>
    </div>
    
    <div class="summary">
        <div class="card">
            <h2>{report.total_files_read_without_omni}</h2>
            <p>Files Read (Without OMNI)</p>
        </div>
        <div class="card">
            <h2>{report.total_files_read_with_omni}</h2>
            <p>Files Read (With OMNI)</p>
        </div>
        <div class="card savings">
            <h2>{report.time_savings_percent:.1f}%</h2>
            <p>Estimated Time Savings</p>
        </div>
    </div>
    
    <h2>Task-by-Task Comparison</h2>
    <table>
        <tr>
            <th>Task</th>
            <th>Without OMNI (tokens)</th>
            <th>With OMNI (tokens)</th>
            <th>Savings</th>
            <th>Comparison</th>
        </tr>
'''
        
        for i, (without, with_omni) in enumerate(zip(report.results_without_omni, report.results_with_omni)):
            savings = (1 - with_omni.total_input_tokens / without.total_input_tokens) * 100 if without.total_input_tokens > 0 else 0
            bar_width = (with_omni.total_input_tokens / without.total_input_tokens) * 100 if without.total_input_tokens > 0 else 100
            
            html += f'''
        <tr>
            <td><strong>{without.task_name}</strong><br><small>{without.task_id}</small></td>
            <td>{without.total_input_tokens:,}</td>
            <td>{with_omni.total_input_tokens:,}</td>
            <td style="color: #28a745;">{savings:.1f}%</td>
            <td>
                <div class="bar-container">
                    <div class="bar" style="width: {bar_width}%"></div>
                </div>
            </td>
        </tr>
'''
        
        html += '''
    </table>
    
    <h2>Conclusioni</h2>
    <ul>
'''
        
        if report.token_savings_percent > 50:
            html += f'<li>✅ <strong>Risparmio significativo</strong>: OMNI riduce i token del {report.token_savings_percent:.1f}%</li>'
        
        if report.total_files_read_with_omni < report.total_files_read_without_omni:
            files_saved = report.total_files_read_without_omni - report.total_files_read_with_omni
            html += f'<li>✅ <strong>Meno file da leggere</strong>: {files_saved} file in meno</li>'
        
        html += f'''
        <li>📊 Token totali risparmiati: <strong>{report.total_tokens_without_omni - report.total_tokens_with_omni:,}</strong></li>
        <li>⏱️ Tempo stimato risparmiato: <strong>{report.estimated_time_without_omni - report.estimated_time_with_omni:.1f}s</strong></li>
    </ul>
</body>
</html>
'''
        return html


def main():
    """Esegue il benchmark."""
    # Find tasks.yaml
    script_dir = Path(__file__).parent
    tasks_file = script_dir / "tasks.yaml"
    
    if not tasks_file.exists():
        print(f"❌ File not found: {tasks_file}")
        return 1
    
    # Run benchmark
    runner = BenchmarkRunner(str(tasks_file))
    report = runner.run()
    
    # Print summary
    print(f"\n{'='*60}")
    print("📊 BENCHMARK SUMMARY")
    print(f"{'='*60}")
    print(f"Tasks completed: {report.total_tasks}")
    print()
    print(f"WITHOUT OMNI:")
    print(f"  Total tokens:     {report.total_tokens_without_omni:,}")
    print(f"  Files read:       {report.total_files_read_without_omni}")
    print(f"  Estimated time:   {report.estimated_time_without_omni:.1f}s")
    print()
    print(f"WITH OMNI:")
    print(f"  Total tokens:     {report.total_tokens_with_omni:,}")
    print(f"  Files read:       {report.total_files_read_with_omni}")
    print(f"  Estimated time:   {report.estimated_time_with_omni:.1f}s")
    print()
    print(f"SAVINGS:")
    print(f"  Token savings:    {report.token_savings_percent:.1f}%")
    print(f"  Time savings:     {report.time_savings_percent:.1f}%")
    print(f"  Tokens saved:     {report.total_tokens_without_omni - report.total_tokens_with_omni:,}")
    
    # Generate HTML report
    html = runner.generate_report_html(report)
    report_file = script_dir / "report.html"
    report_file.write_text(html, encoding="utf-8")
    print(f"\n✅ HTML report saved to: {report_file}")
    
    # Save JSON report
    json_file = script_dir / "report.json"
    json_data = {
        "timestamp": report.timestamp,
        "project_name": report.project_name,
        "total_tasks": report.total_tasks,
        "totals": {
            "without_omni": {
                "tokens": report.total_tokens_without_omni,
                "files_read": report.total_files_read_without_omni,
                "time_seconds": report.estimated_time_without_omni,
            },
            "with_omni": {
                "tokens": report.total_tokens_with_omni,
                "files_read": report.total_files_read_with_omni,
                "time_seconds": report.estimated_time_with_omni,
            },
            "savings": {
                "token_percent": report.token_savings_percent,
                "time_percent": report.time_savings_percent,
            }
        },
        "tasks": [
            {
                "id": r.task_id,
                "name": r.task_name,
                "without_omni": report.results_without_omni[i].to_dict(),
                "with_omni": report.results_with_omni[i].to_dict(),
            }
            for i, r in enumerate(report.results_without_omni)
        ]
    }
    json_file.write_text(json.dumps(json_data, indent=2), encoding="utf-8")
    print(f"✅ JSON report saved to: {json_file}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
