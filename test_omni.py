"""
Test OMNI - Assistant to the Assistant

Questo script mostra come OMNI valida il codice PRIMA che venga applicato.
Simula il flusso: Copilot genera → OMNI valida → OK o Warning
"""

import asyncio
import pytest
import sys
sys.path.insert(0, '.')

# Import diretti per evitare import circolari
from backend.agents.context_agent import ContextAgent, ContextAgentConfig
from backend.agents.rag_agent import RAGAgent, RAGAgentConfig
from backend.agents.security_agent import SecurityAgent, SecurityAgentConfig
from backend.agents.compliance_agent import ComplianceAgent, ComplianceAgentConfig


@pytest.mark.asyncio
async def test_validation():
    """Test completo del sistema di validazione."""
    
    print("=" * 60)
    print("🛡️  OMNI - Assistant to the Assistant")
    print("=" * 60)
    
    # 1. Inizializza gli agent
    print("\n📦 Inizializzazione agent...")
    
    context_agent = ContextAgent(ContextAgentConfig(
        track_project_structure=True,
        auto_detect_stack=True,
    ))
    
    rag_agent = RAGAgent(RAGAgentConfig(
        enabled=True,
        return_summaries_only=True,
    ))
    
    security_agent = SecurityAgent(
        SecurityAgentConfig(
            semgrep_enabled=False,  # Disabilitato per test veloce
            use_context_agent=True,
            use_rag_agent=True,
        ),
        context_agent=context_agent,
        rag_agent=rag_agent,
    )
    
    compliance_agent = ComplianceAgent(
        ComplianceAgentConfig(
            use_context_agent=True,
            use_rag_agent=True,
        ),
        context_agent=context_agent,
        rag_agent=rag_agent,
    )
    
    print("✅ Agent inizializzati")
    
    # 2. Simula un progetto esistente
    print("\n📁 Simulazione progetto esistente...")
    context_agent.register_generated_file(
        "backend/main.py",
        """
from fastapi import FastAPI
app = FastAPI()

@app.get("/users")
def get_users():
    return []
"""
    )
    context_agent.register_generated_file(
        "frontend/App.tsx",
        """
import React from 'react';
export default function App() {
    return <div>Hello</div>;
}
"""
    )
    
    print(f"📊 Project Context: {context_agent.get_project_summary_for_prompt()}")
    print(f"🔍 Is Fullstack: {context_agent.requires_backend_and_frontend()}")
    
    # 3. TEST 1: Codice SICURO
    print("\n" + "=" * 60)
    print("TEST 1: Codice SICURO (dovrebbe passare)")
    print("=" * 60)
    
    safe_code = '''
from fastapi import FastAPI, Depends
from passlib.hash import bcrypt
import secrets

def hash_password(password: str) -> str:
    """Hash password with bcrypt."""
    return bcrypt.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash."""
    return bcrypt.verify(password, hashed)

def generate_token() -> str:
    """Generate secure random token."""
    return secrets.token_urlsafe(32)
'''
    
    print("\n🔒 Security Check...")
    security_result = await security_agent.validate_code(safe_code, "auth.py")
    print(f"   Valid: {security_result['valid']}")
    print(f"   Issues: {security_result['issue_count']}")
    
    print("\n📋 Compliance Check...")
    compliance_result = await compliance_agent.validate_code(safe_code, "auth.py")
    print(f"   Valid: {compliance_result['valid']}")
    print(f"   Issues: {compliance_result['issue_count']}")
    
    if security_result['valid'] and compliance_result['valid']:
        print("\n✅ RISULTATO: Codice approvato!")
    
    # 4. TEST 2: Codice con VULNERABILITÀ
    print("\n" + "=" * 60)
    print("TEST 2: Codice con VULNERABILITÀ (dovrebbe fallire)")
    print("=" * 60)
    
    unsafe_code = '''
import sqlite3

# VULNERABILITÀ: Password hardcoded
password = "admin123"
api_key = "sk-1234567890abcdef"

def login(username, password):
    # VULNERABILITÀ: SQL Injection
    conn = sqlite3.connect("db.sqlite")
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE username = '%s' AND password = '%s'" % (username, password)
    cursor.execute(query)
    return cursor.fetchone()

def process_input(data):
    # VULNERABILITÀ: eval() su input utente
    result = eval(data)
    return result
'''
    
    print("\n🔒 Security Check...")
    security_result = await security_agent.validate_code(unsafe_code, "auth.py")
    print(f"   Valid: {security_result['valid']}")
    print(f"   Issues: {security_result['issue_count']}")
    print(f"   Critical: {security_result['critical_count']}")
    print(f"   High: {security_result['high_count']}")
    
    if security_result['issues']:
        print("\n   ⚠️ Problemi trovati:")
        for issue in security_result['issues'][:5]:
            print(f"      - {issue['severity'].upper()}: {issue['title']}")
            print(f"        Line {issue['line_start']}: {issue['code_snippet'][:50]}...")
    
    # 5. TEST 3: Codice con problemi di COMPLIANCE
    print("\n" + "=" * 60)
    print("TEST 3: Codice con problemi di COMPLIANCE")
    print("=" * 60)
    
    non_compliant_code = '''
def register_user(email, name, password):
    """Register a new user."""
    # Salva i dati senza consent
    user = {
        "email": email,
        "name": name,
        "password": password,  # Password in chiaro!
    }
    
    # GDPR: Log con dati personali
    print(f"New user registered: {email}, {name}")
    
    # Salva nel database
    save_to_db(user)
    return user

def process_patient(patient_id, diagnosis):
    """Process patient medical data."""
    # HIPAA: Dati medici non criptati
    medical_record = {
        "patient_id": patient_id,
        "diagnosis": diagnosis,
    }
    return medical_record
'''
    
    print("\n📋 Compliance Check...")
    compliance_result = await compliance_agent.validate_code(non_compliant_code, "user_service.py")
    print(f"   Valid: {compliance_result['valid']}")
    print(f"   Issues: {compliance_result['issue_count']}")
    print(f"   Data types detected: {compliance_result['data_types_detected']}")
    print(f"   Regulations checked: {compliance_result['regulations_checked']}")
    
    if compliance_result['issues']:
        print("\n   ⚠️ Problemi di compliance:")
        for issue in compliance_result['issues'][:5]:
            print(f"      - [{issue['regulation']}] {issue['rule_name']}")
            print(f"        {issue['message']}")
            print(f"        💡 {issue['remediation']}")
    
    # 6. Riepilogo
    print("\n" + "=" * 60)
    print("📊 RIEPILOGO")
    print("=" * 60)
    print("""
OMNI funziona così:

1. Copilot genera codice
2. L'extension chiama: orchestrator.validate_code(code, file_path)
3. Security Agent scansiona vulnerabilità
4. Compliance Agent verifica GDPR/HIPAA/PCI
5. Se OK → codice applicato
6. Se problemi → mostra warning con fix suggeriti

Il Context Agent ricorda il progetto (fullstack, FastAPI+React, etc.)
Il RAG Agent fornisce knowledge base di sicurezza/compliance
""")


if __name__ == "__main__":
    asyncio.run(test_validation())
