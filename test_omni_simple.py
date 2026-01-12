"""
Test OMNI - Assistant to the Assistant

Questo script mostra come OMNI valida il codice PRIMA che venga applicato.
Simula il flusso: Copilot genera → OMNI valida → OK o Warning

USO: python test_omni_simple.py
"""

import asyncio
import sys
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from enum import Enum

# ==========================================
# Mini implementazione standalone per test
# ==========================================

class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class SecurityFinding:
    title: str
    severity: Severity
    line: int
    code: str
    fix: str


@dataclass
class ComplianceFinding:
    rule: str
    regulation: str
    message: str
    fix: str


class SimpleSecurityChecker:
    """Security checker semplificato per demo."""
    
    PATTERNS = [
        (r'password\s*=\s*["\'][^"\']+["\']', "Hardcoded password", Severity.CRITICAL, "Use environment variables"),
        (r'api_key\s*=\s*["\'][^"\']+["\']', "Hardcoded API key", Severity.CRITICAL, "Use secrets manager"),
        (r'secret\s*=\s*["\'][^"\']+["\']', "Hardcoded secret", Severity.CRITICAL, "Use environment variables"),
        (r'eval\s*\(', "Use of eval()", Severity.HIGH, "Avoid eval, use safe alternatives"),
        (r'exec\s*\(', "Use of exec()", Severity.HIGH, "Avoid exec, use safe alternatives"),
        (r'shell\s*=\s*True', "Shell injection risk", Severity.HIGH, "Use shell=False"),
        (r'%s.*%.*\(', "SQL injection risk", Severity.HIGH, "Use parameterized queries"),
        (r'\.format\(.*\)', "Potential injection", Severity.MEDIUM, "Use parameterized queries"),
        (r'innerHTML\s*=', "XSS risk", Severity.MEDIUM, "Use textContent instead"),
        (r'dangerouslySetInnerHTML', "XSS risk (React)", Severity.MEDIUM, "Sanitize HTML"),
    ]
    
    def check(self, code: str) -> list[SecurityFinding]:
        findings = []
        lines = code.split('\n')
        
        for i, line in enumerate(lines, 1):
            for pattern, title, severity, fix in self.PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    findings.append(SecurityFinding(
                        title=title,
                        severity=severity,
                        line=i,
                        code=line.strip()[:60],
                        fix=fix,
                    ))
        
        return findings


class SimpleComplianceChecker:
    """Compliance checker semplificato per demo."""
    
    def check(self, code: str) -> list[ComplianceFinding]:
        findings = []
        code_lower = code.lower()
        
        # GDPR checks
        if any(w in code_lower for w in ['email', 'name', 'address', 'phone']):
            if 'consent' not in code_lower:
                findings.append(ComplianceFinding(
                    rule="GDPR-CONSENT",
                    regulation="GDPR Article 6",
                    message="Personal data handling without consent check",
                    fix="Add consent verification before processing",
                ))
            
            if re.search(r'(log|print|console)\s*\(', code_lower):
                if any(w in code_lower for w in ['email', 'password', 'name']):
                    findings.append(ComplianceFinding(
                        rule="GDPR-LOGGING",
                        regulation="GDPR Article 32",
                        message="Personal data may be exposed in logs",
                        fix="Sanitize logs to remove personal data",
                    ))
        
        # HIPAA checks
        if any(w in code_lower for w in ['patient', 'medical', 'health', 'diagnosis']):
            if not any(w in code_lower for w in ['encrypt', 'hash', 'bcrypt']):
                findings.append(ComplianceFinding(
                    rule="HIPAA-ENCRYPT",
                    regulation="HIPAA 164.312",
                    message="Health data should be encrypted",
                    fix="Encrypt health data at rest and in transit",
                ))
        
        # Auth checks
        if 'password' in code_lower:
            if not any(w in code_lower for w in ['bcrypt', 'argon', 'pbkdf', 'hash']):
                findings.append(ComplianceFinding(
                    rule="AUTH-HASH",
                    regulation="Security Best Practice",
                    message="Password handling without hashing",
                    fix="Use bcrypt or argon2 to hash passwords",
                ))
        
        return findings


# ==========================================
# Test principale
# ==========================================

def main():
    print("=" * 70)
    print("🛡️  OMNI - Assistant to the Assistant")
    print("    Validazione codice PRIMA dell'applicazione")
    print("=" * 70)
    
    security = SimpleSecurityChecker()
    compliance = SimpleComplianceChecker()
    
    # =========================================
    # TEST 1: Codice SICURO
    # =========================================
    print("\n" + "=" * 70)
    print("✅ TEST 1: Codice SICURO (dovrebbe passare)")
    print("=" * 70)
    
    safe_code = '''
from fastapi import FastAPI, Depends
from passlib.hash import bcrypt
import secrets
import os

def hash_password(password: str) -> str:
    """Hash password with bcrypt."""
    return bcrypt.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash."""
    return bcrypt.verify(password, hashed)

def get_api_key() -> str:
    """Get API key from environment."""
    return os.environ.get("API_KEY")
'''
    
    print("\n📝 Codice da validare:")
    print("-" * 40)
    print(safe_code[:300] + "...")
    
    sec_findings = security.check(safe_code)
    comp_findings = compliance.check(safe_code)
    
    print("\n🔒 Security Check:")
    if sec_findings:
        for f in sec_findings:
            print(f"   ⚠️ {f.severity.value.upper()}: {f.title} (line {f.line})")
    else:
        print("   ✅ Nessun problema di sicurezza")
    
    print("\n📋 Compliance Check:")
    if comp_findings:
        for f in comp_findings:
            print(f"   ⚠️ [{f.regulation}] {f.message}")
    else:
        print("   ✅ Nessun problema di compliance")
    
    if not sec_findings and not comp_findings:
        print("\n" + "=" * 70)
        print("✅ RISULTATO: CODICE APPROVATO - Può essere applicato!")
        print("=" * 70)
    
    # =========================================
    # TEST 2: Codice con VULNERABILITÀ
    # =========================================
    print("\n\n" + "=" * 70)
    print("❌ TEST 2: Codice con VULNERABILITÀ (dovrebbe fallire)")
    print("=" * 70)
    
    unsafe_code = '''
import sqlite3

# Credenziali hardcoded (MALE!)
password = "admin123"
api_key = "sk-1234567890abcdef"
secret = "super_secret_token"

def login(username, pwd):
    # SQL Injection vulnerability
    conn = sqlite3.connect("db.sqlite")
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE username = '%s'" % username
    cursor.execute(query)
    return cursor.fetchone()

def process_input(data):
    # Code injection vulnerability
    result = eval(data)
    return result

def run_command(cmd):
    import subprocess
    # Shell injection
    subprocess.call(cmd, shell=True)
'''
    
    print("\n📝 Codice da validare:")
    print("-" * 40)
    print(unsafe_code[:400] + "...")
    
    sec_findings = security.check(unsafe_code)
    comp_findings = compliance.check(unsafe_code)
    
    print("\n🔒 Security Check:")
    if sec_findings:
        critical = [f for f in sec_findings if f.severity == Severity.CRITICAL]
        high = [f for f in sec_findings if f.severity == Severity.HIGH]
        medium = [f for f in sec_findings if f.severity == Severity.MEDIUM]
        
        if critical:
            print(f"\n   🚨 CRITICAL ({len(critical)}):")
            for f in critical:
                print(f"      Line {f.line}: {f.title}")
                print(f"      Code: {f.code}")
                print(f"      💡 Fix: {f.fix}")
        
        if high:
            print(f"\n   🔴 HIGH ({len(high)}):")
            for f in high:
                print(f"      Line {f.line}: {f.title}")
                print(f"      💡 Fix: {f.fix}")
        
        if medium:
            print(f"\n   🟠 MEDIUM ({len(medium)}):")
            for f in medium:
                print(f"      Line {f.line}: {f.title}")
    else:
        print("   ✅ Nessun problema")
    
    print("\n" + "=" * 70)
    print("❌ RISULTATO: CODICE BLOCCATO - Richiede fix!")
    print("=" * 70)
    
    # =========================================
    # TEST 3: Codice con problemi di COMPLIANCE
    # =========================================
    print("\n\n" + "=" * 70)
    print("⚠️ TEST 3: Codice con problemi di COMPLIANCE")
    print("=" * 70)
    
    non_compliant_code = '''
def register_user(email, name, password):
    """Register a new user."""
    # Salva dati personali senza consent
    user = {
        "email": email,
        "name": name,
        "password": password,
    }
    
    # Log con dati personali (GDPR violation)
    print(f"New user: {email}, {name}")
    
    save_to_db(user)
    return user

def process_patient(patient_id, diagnosis):
    """Process patient medical data."""
    # Dati medici non criptati (HIPAA violation)
    medical_record = {
        "patient_id": patient_id,
        "diagnosis": diagnosis,
    }
    return medical_record
'''
    
    print("\n📝 Codice da validare:")
    print("-" * 40)
    print(non_compliant_code[:400] + "...")
    
    sec_findings = security.check(non_compliant_code)
    comp_findings = compliance.check(non_compliant_code)
    
    print("\n📋 Compliance Check:")
    if comp_findings:
        for f in comp_findings:
            print(f"\n   ⚠️ [{f.regulation}] {f.rule}")
            print(f"      {f.message}")
            print(f"      💡 Fix: {f.fix}")
    else:
        print("   ✅ Nessun problema")
    
    print("\n" + "=" * 70)
    print("⚠️ RISULTATO: WARNING - Richiede review compliance!")
    print("=" * 70)
    
    # =========================================
    # Riepilogo
    # =========================================
    print("\n\n" + "=" * 70)
    print("📊 COME FUNZIONA OMNI")
    print("=" * 70)
    print("""
1. 👨‍💻 Developer chiede a Copilot: "aggiungi login"

2. 🤖 Copilot genera il codice

3. 🛡️ OMNI intercetta PRIMA dell'applicazione:
   
   Security Agent controlla:
   ├── Hardcoded secrets
   ├── SQL Injection
   ├── XSS vulnerabilities
   ├── Code injection (eval/exec)
   └── Shell injection
   
   Compliance Agent controlla:
   ├── GDPR (consent, data logging)
   ├── HIPAA (encryption, PHI handling)
   ├── PCI-DSS (card data)
   └── Auth best practices

4. 📊 Risultato:
   ├── ✅ OK → Codice applicato
   ├── ⚠️ Warning → Mostra issues, chiede conferma
   └── ❌ Critical → Blocca, richiede fix

5. 💾 Dopo applicazione:
   └── Context Agent memorizza il file
   └── RAG Agent indicizza per future query
""")


if __name__ == "__main__":
    main()
