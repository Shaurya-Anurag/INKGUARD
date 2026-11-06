"""
INKGUARD single-file backend MVP.
Install: pip install fastapi uvicorn sqlalchemy python-multipart pypdf python-docx
Run:     uvicorn main:app --reload
Docs:    http://127.0.0.1:8000/docs

Optional PostgreSQL:
  set DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DB
  pip install "psycopg[binary]"
Default is local SQLite so the first run works without provisioning a database.

Scope: real CRUD/upload/audit/revision/approval endpoints and deterministic checks.
No LLM is secretly called. Findings are advisory. No authentication is implemented yet.
"""
from __future__ import annotations
import os, re, uuid, hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, String, Text, Integer, Float, Boolean, DateTime, ForeignKey, JSON, select, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./inkguard.db")
STORAGE = Path(os.getenv("INKGUARD_STORAGE", "./storage")).resolve()
STORAGE.mkdir(parents=True, exist_ok=True)
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "15"))
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def now(): return datetime.now(timezone.utc)
def uid(prefix): return f"{prefix}_{uuid.uuid4().hex[:12]}"
class Base(DeclarativeBase): pass
def db_session():
    db = SessionLocal()
    try: yield db
    finally: db.close()

# ----------------------------- Database ------------------------------------
class Workspace(Base):
    __tablename__="workspaces"
    id: Mapped[str]=mapped_column(String(40),primary_key=True,default=lambda:uid("ws"))
    name: Mapped[str]=mapped_column(String(160))
    description: Mapped[Optional[str]]=mapped_column(Text,nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)

class Document(Base):
    __tablename__="documents"
    id: Mapped[str]=mapped_column(String(40),primary_key=True,default=lambda:uid("doc"))
    workspace_id: Mapped[str]=mapped_column(ForeignKey("workspaces.id"),index=True)
    filename: Mapped[str]=mapped_column(String(255))
    content_type: Mapped[Optional[str]]=mapped_column(String(120),nullable=True)
    storage_path: Mapped[str]=mapped_column(Text)
    extracted_text: Mapped[str]=mapped_column(Text,default="")
    sha256: Mapped[str]=mapped_column(String(64))
    kind: Mapped[str]=mapped_column(String(30),default="reference")
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)

class BrandRule(Base):
    __tablename__="brand_rules"
    id: Mapped[str]=mapped_column(String(40),primary_key=True,default=lambda:uid("rule"))
    workspace_id: Mapped[str]=mapped_column(ForeignKey("workspaces.id"),index=True)
    title: Mapped[str]=mapped_column(String(200))
    description: Mapped[str]=mapped_column(Text)
    category: Mapped[str]=mapped_column(String(60),default="brand")
    severity: Mapped[str]=mapped_column(String(20),default="medium")
    source_document_id: Mapped[Optional[str]]=mapped_column(ForeignKey("documents.id"),nullable=True)
    verified: Mapped[bool]=mapped_column(Boolean,default=False)

class ApprovedFact(Base):
    __tablename__="approved_facts"
    id: Mapped[str]=mapped_column(String(40),primary_key=True,default=lambda:uid("fact"))
    workspace_id: Mapped[str]=mapped_column(ForeignKey("workspaces.id"),index=True)
    subject: Mapped[str]=mapped_column(String(160))
    attribute: Mapped[str]=mapped_column(String(120))
    approved_value: Mapped[str]=mapped_column(Text)
    unit: Mapped[Optional[str]]=mapped_column(String(60),nullable=True)
    source_document_id: Mapped[Optional[str]]=mapped_column(ForeignKey("documents.id"),nullable=True)
    verified: Mapped[bool]=mapped_column(Boolean,default=False)

class Terminology(Base):
    __tablename__="terminology"
    id: Mapped[str]=mapped_column(String(40),primary_key=True,default=lambda:uid("term"))
    workspace_id: Mapped[str]=mapped_column(ForeignKey("workspaces.id"),index=True)
    term: Mapped[str]=mapped_column(String(200))
    replacement: Mapped[Optional[str]]=mapped_column(String(200),nullable=True)
    term_type: Mapped[str]=mapped_column(String(20),default="prohibited")
    case_sensitive: Mapped[bool]=mapped_column(Boolean,default=False)

class Audit(Base):
    __tablename__="audits"
    id: Mapped[str]=mapped_column(String(40),primary_key=True,default=lambda:uid("audit"))
    workspace_id: Mapped[str]=mapped_column(ForeignKey("workspaces.id"),index=True)
    document_id: Mapped[str]=mapped_column(ForeignKey("documents.id"))
    status: Mapped[str]=mapped_column(String(30),default="completed")
    score: Mapped[int]=mapped_column(Integer,default=100)
    summary: Mapped[str]=mapped_column(Text,default="")
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)

class Finding(Base):
    __tablename__="findings"
    id: Mapped[str]=mapped_column(String(40),primary_key=True,default=lambda:uid("finding"))
    audit_id: Mapped[str]=mapped_column(ForeignKey("audits.id"),index=True)
    category: Mapped[str]=mapped_column(String(60))
    finding_type: Mapped[str]=mapped_column(String(50))
    severity: Mapped[str]=mapped_column(String(20))
    status: Mapped[str]=mapped_column(String(20),default="open")
    detected_text: Mapped[str]=mapped_column(Text)
    explanation: Mapped[str]=mapped_column(Text)
    suggestion: Mapped[str]=mapped_column(Text)
    confidence: Mapped[float]=mapped_column(Float,default=.7)
    evidence: Mapped[list]=mapped_column(JSON,default=list)
    start_offset: Mapped[Optional[int]]=mapped_column(Integer,nullable=True)
    end_offset: Mapped[Optional[int]]=mapped_column(Integer,nullable=True)

class Revision(Base):
    __tablename__="revisions"
    id: Mapped[str]=mapped_column(String(40),primary_key=True,default=lambda:uid("rev"))
    audit_id: Mapped[str]=mapped_column(ForeignKey("audits.id"),index=True)
    revision_number: Mapped[int]=mapped_column(Integer)
    content: Mapped[str]=mapped_column(Text)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)

class Approval(Base):
    __tablename__="approvals"
    id: Mapped[str]=mapped_column(String(40),primary_key=True,default=lambda:uid("approval"))
    audit_id: Mapped[str]=mapped_column(ForeignKey("audits.id"),unique=True,index=True)
    decision: Mapped[str]=mapped_column(String(30),default="pending")
    reviewer: Mapped[str]=mapped_column(String(160),default="Reviewer")
    comment: Mapped[Optional[str]]=mapped_column(Text,nullable=True)
    decided_at: Mapped[Optional[datetime]]=mapped_column(DateTime(timezone=True),nullable=True)

class AuditEvent(Base):
    __tablename__="audit_events"
    id: Mapped[str]=mapped_column(String(40),primary_key=True,default=lambda:uid("event"))
    workspace_id: Mapped[str]=mapped_column(ForeignKey("workspaces.id"),index=True)
    audit_id: Mapped[Optional[str]]=mapped_column(ForeignKey("audits.id"),nullable=True,index=True)
    actor: Mapped[str]=mapped_column(String(160),default="system")
    action: Mapped[str]=mapped_column(String(100))
    details: Mapped[dict]=mapped_column(JSON,default=dict)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)

Base.metadata.create_all(engine)

# ----------------------------- Schemas -------------------------------------
class WorkspaceIn(BaseModel):
    name: str=Field(min_length=2,max_length=160)
    description: Optional[str]=None
class RuleIn(BaseModel):
    workspace_id:str; title:str; description:str
    category:str="brand"; severity:str="medium"
    source_document_id:Optional[str]=None; verified:bool=False
class FactIn(BaseModel):
    workspace_id:str; subject:str; attribute:str; approved_value:str
    unit:Optional[str]=None; source_document_id:Optional[str]=None; verified:bool=False
class TermIn(BaseModel):
    workspace_id:str; term:str; replacement:Optional[str]=None
    term_type:str="prohibited"; case_sensitive:bool=False
class AuditIn(BaseModel):
    workspace_id:str; document_id:str
class RevisionIn(BaseModel):
    content:str=Field(min_length=1); actor:str="Creator"
class ApprovalIn(BaseModel):
    decision:str=Field(pattern="^(approved|changes_requested)$")
    reviewer:str="Reviewer"; comment:Optional[str]=None

# ----------------------------- Helpers -------------------------------------
def workspace_or_404(db,wid):
    w=db.get(Workspace,wid)
    if not w: raise HTTPException(404,"Workspace not found")
    return w
def log_event(db,wid,action,audit_id=None,actor="system",details=None):
    db.add(AuditEvent(workspace_id=wid,audit_id=audit_id,action=action,actor=actor,details=details or {}))
def extract(path:Path,filename:str)->str:
    ext=Path(filename).suffix.lower()
    if ext in {".txt",".md",".csv",".json"}: return path.read_text(encoding="utf-8",errors="replace")
    if ext==".pdf":
        from pypdf import PdfReader
        return "\n".join(p.extract_text() or "" for p in PdfReader(str(path)).pages)
    if ext==".docx":
        from docx import Document as Docx
        return "\n".join(p.text for p in Docx(str(path)).paragraphs)
    raise ValueError("Allowed formats: PDF, DOCX, TXT, MD, CSV, JSON")
def finding_json(f):
    return {k:getattr(f,k) for k in ("id","category","finding_type","severity","status","detected_text","explanation","suggestion","confidence","evidence","start_offset","end_offset")}
def audit_json(db,a):
    fs=db.scalars(select(Finding).where(Finding.audit_id==a.id)).all()
    ap=db.scalar(select(Approval).where(Approval.audit_id==a.id))
    return {"id":a.id,"workspace_id":a.workspace_id,"document_id":a.document_id,"status":a.status,
      "compliance_score":a.score,"summary":a.summary,"created_at":a.created_at.isoformat(),
      "findings":[finding_json(f) for f in fs],
      "approval":({"decision":ap.decision,"reviewer":ap.reviewer,"comment":ap.comment,
                   "decided_at":ap.decided_at.isoformat() if ap.decided_at else None} if ap else None)}

# ----------------------------- Compliance ----------------------------------
WEIGHTS={"critical":18,"high":12,"medium":7,"low":3}
CLAIM_PATTERNS=[
 (r"\b100\s*%\s*(?:safe|effective|guaranteed)\b","absolute_claim","Absolute claims require explicit substantiation."),
 (r"\b(?:cures?|eliminates?|permanently removes?)\b","strong_outcome_claim","Strong outcome claims require approved substantiation."),
 (r"\b(?:in|within)\s+\d+\s+days?\b","time_bound_claim","Time-bound performance claims require approved substantiation.")
]

def _sentence_bounds(content, start, end):
    """Return the sentence-like span containing [start, end), bounded by punctuation/newlines."""
    left=max(content.rfind(".",0,start),content.rfind("!",0,start),content.rfind("?",0,start),content.rfind("\n",0,start),content.rfind(";",0,start))+1
    stops=[p for p in (content.find(".",end),content.find("!",end),content.find("?",end),content.find("\n",end),content.find(";",end)) if p!=-1]
    right=min(stops) if stops else len(content)
    return left,right

def _number_value(raw):
    try:
        from decimal import Decimal
        m=re.search(r"\d+(?:\.\d+)?",raw)
        return Decimal(m.group()) if m else None
    except Exception:
        return None

def _attribute_anchors(attribute):
    # Avoid generic measurement words as sole anchors; they create cross-attribute matches.
    generic={"concentration","percentage","percent","amount","level","content","quantity","value","rate"}
    tokens=[t.lower() for t in re.findall(r"[a-zA-Z0-9]+",attribute) if t.lower() not in generic]
    return tokens

def _subject_anchors(subject):
    generic={"product","formula","item","variant","the","and","for","of","with"}
    return [t.lower() for t in re.findall(r"[a-zA-Z0-9]+",subject)
            if len(t)>1 and t.lower() not in generic]

def _paragraph_bounds(content,start,end):
    left=content.rfind("\n\n",0,start)
    left=0 if left < 0 else left+2
    right=content.find("\n\n",end)
    right=len(content) if right < 0 else right
    return left,right

def evaluate(db,wid,content):
    out=[]
    terms=db.scalars(select(Terminology).where(Terminology.workspace_id==wid)).all()
    rules=db.scalars(select(BrandRule).where(BrandRule.workspace_id==wid,BrandRule.verified.is_(True))).all()
    facts=db.scalars(select(ApprovedFact).where(ApprovedFact.workspace_id==wid,ApprovedFact.verified.is_(True))).all()

    for t in terms:
        hay=content if t.case_sensitive else content.lower()
        needle=t.term if t.case_sensitive else t.term.lower()
        # Find every occurrence, not only the first one.
        for m in re.finditer(re.escape(needle),hay):
            if t.term_type=="prohibited":
                out.append(dict(category="terminology",finding_type="terminology_violation",severity="high",
                  detected_text=content[m.start():m.end()],explanation=f"'{t.term}' is prohibited terminology.",
                  suggestion=f"Replace with '{t.replacement}'." if t.replacement else "Use approved terminology.",
                  confidence=.99,evidence=[{"source_type":"terminology","source_id":t.id,"source_text":t.term}],
                  start_offset=m.start(),end_offset=m.end()))
            elif t.term_type=="preferred":
                out.append(dict(category="terminology",finding_type="preferred_term_recommendation",severity="low",
                  detected_text=content[m.start():m.end()],
                  explanation=f"'{t.term}' is not the preferred brand term. This is a consistency recommendation, not a compliance violation.",
                  suggestion=f"Use '{t.replacement}' instead." if t.replacement else "Use the brand's approved preferred terminology.",
                  confidence=.97,evidence=[{"source_type":"terminology","source_id":t.id,"source_text":t.term}],
                  start_offset=m.start(),end_offset=m.end()))

    for r in rules:
        m=re.search(r"(?:avoid|prohibited)\s*:\s*['\"]?([^.;\n'\"]+)",r.description,re.I)
        if m:
            phrase=m.group(1).strip()
            for hit in re.finditer(re.escape(phrase),content,re.I):
                out.append(dict(category=r.category,finding_type="brand_rule_violation",severity=r.severity,
                  detected_text=content[hit.start():hit.end()],explanation=f"{r.title}: {r.description}",
                  suggestion="Revise this text to comply with the verified brand rule.",confidence=.96,
                  evidence=[{"source_type":"brand_rule","source_id":r.id,"source_text":r.title+": "+r.description}],
                  start_offset=hit.start(),end_offset=hit.end()))

    for pattern,kind,why in CLAIM_PATTERNS:
        for m in re.finditer(pattern,content,re.I):
            out.append(dict(category="claims",finding_type=kind,severity="high",detected_text=m.group(),
              explanation=why+" This is a wording flag, not a determination that the claim is false.",
              suggestion="Verify against approved substantiation or rewrite as a qualified claim.",
              confidence=.78,evidence=[],start_offset=m.start(),end_offset=m.end()))

    # Attribute-aware numeric comparison. A number is only compared with a fact when
    # the same sentence contains a distinctive term from that fact's attribute.
    # This prevents unrelated numbers elsewhere in a nearby 100-character window
    # (e.g. "3 days" or "100% safe") from being treated as product concentrations.
    number_pattern=re.compile(r"\b\d+(?:\.\d+)?\s*(?:%|percent\b)?",re.I)
    for fact in facts:
        approved=_number_value(fact.approved_value)
        if approved is None:
            continue
        anchors=_attribute_anchors(fact.attribute)
        subject_anchors=_subject_anchors(fact.subject)
        if not anchors or not subject_anchors:
            continue

        for m in number_pattern.finditer(content):
            left,right=_sentence_bounds(content,m.start(),m.end())
            sentence=content[left:right].lower()
            if not any(re.search(r"\b"+re.escape(anchor)+r"\b",sentence) for anchor in anchors):
                continue

            pleft,pright=_paragraph_bounds(content,m.start(),m.end())
            paragraph=content[pleft:pright].lower()
            subject_found=all(
                re.search(r"\b"+re.escape(anchor)+r"\b",paragraph)
                for anchor in subject_anchors
            )

            # A product heading immediately above the paragraph can establish context.
            # Do not search arbitrarily far back: that risks borrowing another product's identity.
            if not subject_found and pleft > 0:
                previous_separator=content.rfind("\n\n",0,max(0,pleft-2))
                previous_start=0 if previous_separator < 0 else previous_separator+2
                previous=content[previous_start:pleft].strip()
                is_heading=(
                    bool(previous)
                    and len(previous)<=120
                    and not re.search(r"[.!?]",previous)
                )
                if is_heading:
                    previous_lower=previous.lower()
                    subject_found=all(
                        re.search(r"\b"+re.escape(anchor)+r"\b",previous_lower)
                        for anchor in subject_anchors
                    )

            if not subject_found:
                continue

            raw=m.group()
            candidate=_number_value(raw)
            if candidate is None or candidate==approved:
                continue

            unit=(fact.unit or "").strip().lower()
            raw_lower=raw.lower()
            if unit in {"%","percent","percentage"} and not ("%" in raw or "percent" in raw_lower):
                continue
            if unit and unit not in {"%","percent","percentage"} and unit not in sentence:
                continue

            out.append(dict(
                category="product_fact",
                finding_type="fact_contradiction",
                severity="critical",
                detected_text=content[m.start():m.end()].strip(),
                explanation=f"Potential mismatch for {fact.subject}/{fact.attribute}. Approved value: {fact.approved_value} {fact.unit or ''}".strip(),
                suggestion=f"Verify against approved value: {fact.approved_value} {fact.unit or ''}".strip(),
                confidence=.90,
                evidence=[{
                    "source_type":"approved_fact",
                    "source_id":fact.id,
                    "source_text":f"{fact.subject} — {fact.attribute}: {fact.approved_value} {fact.unit or ''}".strip()
                }],
                start_offset=m.start(),
                end_offset=m.end()
            ))

    # Merge detectors that flag the exact same text span. Keep one user-facing finding,
    # retain all evidence, and preserve the additional detector explanation.
    merged=[]
    by_span={}
    severity_rank={"low":1,"medium":2,"high":3,"critical":4}
    for item in out:
        key=(item["start_offset"],item["end_offset"],item["detected_text"].strip().lower())
        if key not in by_span:
            item=dict(item)
            item["evidence"]=list(item.get("evidence") or [])
            by_span[key]=item
            merged.append(item)
            continue
        existing=by_span[key]
        if item["explanation"] not in existing["explanation"]:
            existing["explanation"] += " Additional check: "+item["explanation"]
        for evidence in item.get("evidence") or []:
            if evidence not in existing["evidence"]:
                existing["evidence"].append(evidence)
        if severity_rank.get(item["severity"],0)>severity_rank.get(existing["severity"],0):
            existing["severity"]=item["severity"]
        existing["confidence"]=max(existing["confidence"],item["confidence"])
        # Prefer a concrete terminology replacement over a generic claim rewrite.
        if item["suggestion"] and existing["suggestion"] in {
            "Verify against approved substantiation or rewrite as a qualified claim.",
            "Revise this text to comply with the verified brand rule."
        }:
            existing["suggestion"]=item["suggestion"]
    return merged

def run_audit(db,wid,doc,content):
    items=evaluate(db,wid,content)
    # Score unique, merged findings only. This is a transparent heuristic, not a
    # legal/compliance certification; the UI should show the findings alongside it.
    score=max(0,100-sum(WEIGHTS.get(x["severity"],5) for x in items))
    a=Audit(workspace_id=wid,document_id=doc.id,status="completed",score=score,
      summary=f"{len(items)} finding(s). Automated results are advisory; human review is required.")
    db.add(a); db.flush()
    for item in items: db.add(Finding(audit_id=a.id,**item))
    db.add(Approval(audit_id=a.id))
    log_event(db,wid,"audit.completed",a.id,details={"score":score,"finding_count":len(items)})
    db.commit(); db.refresh(a)
    return a

# ----------------------------- App / CORS ----------------------------------
app=FastAPI(title="INKGUARD API",version="0.1.0",
 description="Brand governance MVP. Automated findings are advisory; human approval is required.")
origins=[x.strip() for x in os.getenv("CORS_ORIGINS","http://localhost:3000,http://127.0.0.1:3000").split(",")]
app.add_middleware(CORSMiddleware,allow_origins=origins,allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

@app.get("/")
def root(): return {"service":"INKGUARD API","version":"0.1.0","docs":"/docs"}
@app.get("/api/health")
def health(): return {"status":"ok","database":"configured"}

@app.post("/api/workspaces",status_code=201)
def create_workspace(p:WorkspaceIn,db:Session=Depends(db_session)):
    w=Workspace(**p.model_dump()); db.add(w); db.commit(); db.refresh(w)
    log_event(db,w.id,"workspace.created",details={"name":w.name}); db.commit()
    return {"id":w.id,"name":w.name,"description":w.description}
@app.get("/api/workspaces")
def list_workspaces(db:Session=Depends(db_session)):
    return [{"id":w.id,"name":w.name,"description":w.description} for w in db.scalars(select(Workspace)).all()]
@app.get("/api/workspaces/{wid}")
def get_workspace(wid:str,db:Session=Depends(db_session)):
    w=workspace_or_404(db,wid); return {"id":w.id,"name":w.name,"description":w.description}

@app.post("/api/documents/upload",status_code=201)
async def upload_document(workspace_id:str=Query(...),kind:str=Query("reference",pattern="^(reference|submission)$"),
                          file:UploadFile=File(...),db:Session=Depends(db_session)):
    workspace_or_404(db,workspace_id)
    filename=Path(file.filename or "upload").name
    if Path(filename).suffix.lower() not in {".pdf",".docx",".txt",".md",".csv",".json"}:
        raise HTTPException(415,"Unsupported file type.")
    suffix=Path(filename).suffix.lower()
    target=STORAGE/(uuid.uuid4().hex+suffix)
    digest=hashlib.sha256()
    total_bytes=0
    max_bytes=MAX_UPLOAD_MB*1024*1024
    try:
        # Stream to disk and enforce the limit as bytes arrive. Reading the whole
        # upload first would let oversized requests consume unbounded memory.
        with target.open("wb") as destination:
            while chunk := await file.read(1024*1024):
                total_bytes += len(chunk)
                if total_bytes > max_bytes:
                    raise HTTPException(413,f"Maximum upload size is {MAX_UPLOAD_MB} MB.")
                digest.update(chunk)
                destination.write(chunk)
        text=extract(target,filename)
    except HTTPException:
        target.unlink(missing_ok=True)
        raise
    except Exception as e:
        target.unlink(missing_ok=True)
        raise HTTPException(422,f"Text extraction failed: {e}")
    finally:
        await file.close()
    if not text.strip():
        target.unlink(missing_ok=True)
        raise HTTPException(422,"No text extracted. Scanned PDFs need OCR; OCR is not included.")
    d=Document(workspace_id=workspace_id,filename=filename,content_type=file.content_type,
      storage_path=str(target),extracted_text=text,sha256=digest.hexdigest(),kind=kind)
    db.add(d); db.flush()
    log_event(db,workspace_id,"document.uploaded",details={"document_id":d.id,"filename":filename,"kind":kind})
    db.commit(); db.refresh(d)
    return {"id":d.id,"workspace_id":workspace_id,"filename":filename,"kind":kind,
      "character_count":len(text),"preview":text[:500],"status":"processed"}
@app.get("/api/documents")
def list_documents(workspace_id:str,db:Session=Depends(db_session)):
    workspace_or_404(db,workspace_id)
    return [{"id":d.id,"filename":d.filename,"kind":d.kind,"character_count":len(d.extracted_text),
      "created_at":d.created_at.isoformat()} for d in db.scalars(select(Document).where(Document.workspace_id==workspace_id)).all()]
@app.get("/api/documents/{did}")
def get_document(did:str,db:Session=Depends(db_session)):
    d=db.get(Document,did)
    if not d: raise HTTPException(404,"Document not found")
    return {"id":d.id,"workspace_id":d.workspace_id,"filename":d.filename,"kind":d.kind,"extracted_text":d.extracted_text}

@app.post("/api/brand/rules",status_code=201)
def create_rule(p:RuleIn,db:Session=Depends(db_session)):
    workspace_or_404(db,p.workspace_id)
    if p.source_document_id:
        d=db.get(Document,p.source_document_id)
        if not d or d.workspace_id!=p.workspace_id: raise HTTPException(400,"Source document is not in this workspace.")
    r=BrandRule(**p.model_dump()); db.add(r); db.flush()
    log_event(db,p.workspace_id,"brand_rule.created",details={"rule_id":r.id}); db.commit()
    return {"id":r.id,**p.model_dump()}
@app.get("/api/brand/rules")
def get_rules(workspace_id:str,db:Session=Depends(db_session)):
    workspace_or_404(db,workspace_id)
    return [{"id":r.id,"title":r.title,"description":r.description,"category":r.category,
      "severity":r.severity,"verified":r.verified,"source_document_id":r.source_document_id}
      for r in db.scalars(select(BrandRule).where(BrandRule.workspace_id==workspace_id)).all()]
@app.post("/api/brand/facts",status_code=201)
def create_fact(p:FactIn,db:Session=Depends(db_session)):
    workspace_or_404(db,p.workspace_id)
    if p.source_document_id:
        d=db.get(Document,p.source_document_id)
        if not d or d.workspace_id!=p.workspace_id: raise HTTPException(400,"Source document is not in this workspace.")
    f=ApprovedFact(**p.model_dump()); db.add(f); db.flush()
    log_event(db,p.workspace_id,"approved_fact.created",details={"fact_id":f.id}); db.commit()
    return {"id":f.id,**p.model_dump()}
@app.get("/api/brand/facts")
def get_facts(workspace_id:str,db:Session=Depends(db_session)):
    workspace_or_404(db,workspace_id)
    return [{"id":f.id,"subject":f.subject,"attribute":f.attribute,"approved_value":f.approved_value,
      "unit":f.unit,"verified":f.verified,"source_document_id":f.source_document_id}
      for f in db.scalars(select(ApprovedFact).where(ApprovedFact.workspace_id==workspace_id)).all()]
@app.post("/api/brand/terminology",status_code=201)
def create_term(p:TermIn,db:Session=Depends(db_session)):
    workspace_or_404(db,p.workspace_id)
    if p.term_type not in {"prohibited","preferred"}: raise HTTPException(422,"term_type must be prohibited or preferred.")
    t=Terminology(**p.model_dump()); db.add(t); db.flush()
    log_event(db,p.workspace_id,"terminology.created",details={"term_id":t.id}); db.commit()
    return {"id":t.id,**p.model_dump()}
@app.get("/api/brand/terminology")
def get_terms(workspace_id:str,db:Session=Depends(db_session)):
    workspace_or_404(db,workspace_id)
    return [{"id":t.id,"term":t.term,"replacement":t.replacement,"term_type":t.term_type,
      "case_sensitive":t.case_sensitive} for t in db.scalars(select(Terminology).where(Terminology.workspace_id==workspace_id)).all()]


@app.put("/api/brand/rules/{rid}")
def update_rule(rid:str,p:RuleIn,db:Session=Depends(db_session)):
    r=db.get(BrandRule,rid)
    if not r: raise HTTPException(404,"Brand rule not found")
    if r.workspace_id!=p.workspace_id: raise HTTPException(404,"Brand rule not found in workspace")
    if p.source_document_id:
        d=db.get(Document,p.source_document_id)
        if not d or d.workspace_id!=p.workspace_id: raise HTTPException(400,"Source document is not in this workspace.")
    for key,value in p.model_dump(exclude={"workspace_id"}).items(): setattr(r,key,value)
    log_event(db,r.workspace_id,"brand_rule.updated",details={"rule_id":rid})
    db.commit(); db.refresh(r)
    return {"id":r.id,"title":r.title,"description":r.description,"category":r.category,
      "severity":r.severity,"verified":r.verified,"source_document_id":r.source_document_id}
@app.delete("/api/brand/rules/{rid}",status_code=204)
def delete_rule(rid:str,db:Session=Depends(db_session)):
    r=db.get(BrandRule,rid)
    if not r: raise HTTPException(404,"Brand rule not found")
    wid=r.workspace_id
    log_event(db,wid,"brand_rule.deleted",details={"rule_id":rid})
    db.delete(r); db.commit()
    return None

@app.put("/api/brand/facts/{fid}")
def update_fact(fid:str,p:FactIn,db:Session=Depends(db_session)):
    f=db.get(ApprovedFact,fid)
    if not f: raise HTTPException(404,"Approved fact not found")
    if f.workspace_id!=p.workspace_id: raise HTTPException(404,"Approved fact not found in workspace")
    if p.source_document_id:
        d=db.get(Document,p.source_document_id)
        if not d or d.workspace_id!=p.workspace_id: raise HTTPException(400,"Source document is not in this workspace.")
    for key,value in p.model_dump(exclude={"workspace_id"}).items(): setattr(f,key,value)
    log_event(db,f.workspace_id,"approved_fact.updated",details={"fact_id":fid})
    db.commit(); db.refresh(f)
    return {"id":f.id,"subject":f.subject,"attribute":f.attribute,"approved_value":f.approved_value,
      "unit":f.unit,"verified":f.verified,"source_document_id":f.source_document_id}
@app.delete("/api/brand/facts/{fid}",status_code=204)
def delete_fact(fid:str,db:Session=Depends(db_session)):
    f=db.get(ApprovedFact,fid)
    if not f: raise HTTPException(404,"Approved fact not found")
    wid=f.workspace_id
    log_event(db,wid,"approved_fact.deleted",details={"fact_id":fid})
    db.delete(f); db.commit()
    return None

@app.put("/api/brand/terminology/{tid}")
def update_term(tid:str,p:TermIn,db:Session=Depends(db_session)):
    t=db.get(Terminology,tid)
    if not t: raise HTTPException(404,"Terminology record not found")
    if t.workspace_id!=p.workspace_id: raise HTTPException(404,"Terminology record not found in workspace")
    if p.term_type not in {"prohibited","preferred"}: raise HTTPException(422,"term_type must be prohibited or preferred.")
    for key,value in p.model_dump(exclude={"workspace_id"}).items(): setattr(t,key,value)
    log_event(db,t.workspace_id,"terminology.updated",details={"term_id":tid})
    db.commit(); db.refresh(t)
    return {"id":t.id,"term":t.term,"replacement":t.replacement,"term_type":t.term_type,
      "case_sensitive":t.case_sensitive}
@app.delete("/api/brand/terminology/{tid}",status_code=204)
def delete_term(tid:str,db:Session=Depends(db_session)):
    t=db.get(Terminology,tid)
    if not t: raise HTTPException(404,"Terminology record not found")
    wid=t.workspace_id
    log_event(db,wid,"terminology.deleted",details={"term_id":tid})
    db.delete(t); db.commit()
    return None

@app.post("/api/audits",status_code=201)
def create_audit_endpoint(p:AuditIn,db:Session=Depends(db_session)):
    workspace_or_404(db,p.workspace_id); d=db.get(Document,p.document_id)
    if not d or d.workspace_id!=p.workspace_id: raise HTTPException(404,"Document not found in workspace.")
    if d.kind!="submission": raise HTTPException(400,"Upload the content as kind=submission before auditing.")
    return audit_json(db,run_audit(db,p.workspace_id,d,d.extracted_text))
@app.get("/api/audits")
def list_audits(workspace_id:str,db:Session=Depends(db_session)):
    workspace_or_404(db,workspace_id); rows=db.scalars(select(Audit).where(Audit.workspace_id==workspace_id).order_by(Audit.created_at.desc())).all()
    result=[]
    for a in rows:
        approval=db.scalar(select(Approval).where(Approval.audit_id==a.id))
        result.append({"id":a.id,"document_id":a.document_id,"status":a.status,
          "approval_decision":approval.decision if approval else "pending",
          "compliance_score":a.score,
          "finding_count":db.scalar(select(func.count(Finding.id)).where(Finding.audit_id==a.id)) or 0,
          "created_at":a.created_at.isoformat()})
    return result
@app.get("/api/audits/{aid}")
def get_audit(aid:str,db:Session=Depends(db_session)):
    a=db.get(Audit,aid)
    if not a: raise HTTPException(404,"Audit not found")
    return audit_json(db,a)
@app.post("/api/audits/{aid}/revisions",status_code=201)
def add_revision(aid:str,p:RevisionIn,db:Session=Depends(db_session)):
    a=db.get(Audit,aid)
    if not a: raise HTTPException(404,"Audit not found")
    ap=db.scalar(select(Approval).where(Approval.audit_id==aid))
    if ap and ap.decision=="approved":
        raise HTTPException(409,"Approved audits are immutable. Create a new submission and audit instead.")
    n=(db.scalar(select(func.max(Revision.revision_number)).where(Revision.audit_id==aid)) or 0)+1
    r=Revision(audit_id=aid,revision_number=n,content=p.content); db.add(r)
    log_event(db,a.workspace_id,"revision.created",aid,p.actor,{"revision_number":n}); db.commit(); db.refresh(r)
    return {"id":r.id,"audit_id":aid,"revision_number":n,"content":r.content}
@app.post("/api/audits/{aid}/reevaluate")
def reevaluate(aid:str,db:Session=Depends(db_session)):
    a=db.get(Audit,aid)
    if not a: raise HTTPException(404,"Audit not found")
    ap=db.scalar(select(Approval).where(Approval.audit_id==aid))
    if ap and ap.decision=="approved":
        raise HTTPException(409,"Approved audits are immutable. Create a new submission and audit instead.")
    r=db.scalar(select(Revision).where(Revision.audit_id==aid).order_by(Revision.revision_number.desc()).limit(1))
    if not r: raise HTTPException(400,"Create a revision first.")
    old=db.get(Document,a.document_id)
    d=Document(workspace_id=a.workspace_id,filename=f"revision-{r.revision_number}-{old.filename}",
      content_type=old.content_type,storage_path=old.storage_path,extracted_text=r.content,
      sha256=hashlib.sha256(r.content.encode()).hexdigest(),kind="submission")
    db.add(d); db.flush()
    new=run_audit(db,a.workspace_id,d,r.content)
    log_event(db,a.workspace_id,"audit.reevaluated",new.id,details={"previous_audit_id":aid,"revision_id":r.id}); db.commit()
    return audit_json(db,new)
@app.post("/api/audits/{aid}/approve")
def approve(aid:str,p:ApprovalIn,db:Session=Depends(db_session)):
    a=db.get(Audit,aid)
    if not a: raise HTTPException(404,"Audit not found")
    # Open findings are unresolved and must be dispositioned before approval.
    # accepted = reviewer explicitly accepts the flagged risk; dismissed/resolved are closed.
    if p.decision == "approved":
        open_count = db.scalar(select(func.count(Finding.id)).where(
            Finding.audit_id == aid, Finding.status == "open"
        )) or 0
        if open_count:
            raise HTTPException(
                409,
                detail=f"Cannot approve: {open_count} finding(s) are still open. "
                       "Resolve, dismiss, or explicitly accept each finding first."
            )
    ap=db.scalar(select(Approval).where(Approval.audit_id==aid))
    if not ap: ap=Approval(audit_id=aid); db.add(ap)
    ap.decision=p.decision; ap.reviewer=p.reviewer; ap.comment=p.comment; ap.decided_at=now()
    log_event(db,a.workspace_id,"approval."+p.decision,aid,p.reviewer,{"comment":p.comment})
    db.commit()
    return {"audit_id":aid,"decision":ap.decision,"reviewer":ap.reviewer,"comment":ap.comment,"decided_at":ap.decided_at.isoformat()}
@app.patch("/api/findings/{fid}")
def set_finding_status(fid:str,status:str=Query(...,pattern="^(open|accepted|dismissed|resolved)$"),db:Session=Depends(db_session)):
    f=db.get(Finding,fid)
    if not f: raise HTTPException(404,"Finding not found")
    a=db.get(Audit,f.audit_id)
    ap=db.scalar(select(Approval).where(Approval.audit_id==a.id))
    if ap and ap.decision=="approved":
        raise HTTPException(409,"Approved audits are immutable. Create a new revision and audit instead.")
    f.status=status
    log_event(db,a.workspace_id,"finding.status_updated",a.id,details={"finding_id":fid,"status":status})
    db.commit()
    return {"id":fid,"status":status}
@app.get("/api/audits/{aid}/events")
def audit_events(aid:str,db:Session=Depends(db_session)):
    a=db.get(Audit,aid)
    if not a: raise HTTPException(404,"Audit not found")
    rows=db.scalars(select(AuditEvent).where(AuditEvent.audit_id==aid).order_by(AuditEvent.created_at)).all()
    return [{"id":e.id,"actor":e.actor,"action":e.action,"details":e.details,"created_at":e.created_at.isoformat()} for e in rows]
@app.get("/api/events")
def workspace_events(workspace_id:str,limit:int=Query(50,ge=1,le=200),db:Session=Depends(db_session)):
    workspace_or_404(db,workspace_id)
    rows=db.scalars(select(AuditEvent).where(AuditEvent.workspace_id==workspace_id).order_by(AuditEvent.created_at.desc()).limit(limit)).all()
    return [{"id":e.id,"audit_id":e.audit_id,"actor":e.actor,"action":e.action,"details":e.details,"created_at":e.created_at.isoformat()} for e in rows]
@app.get("/api/analytics/overview")
def analytics(workspace_id:str,db:Session=Depends(db_session)):
    workspace_or_404(db,workspace_id); audits=db.scalars(select(Audit).where(Audit.workspace_id==workspace_id)).all()
    ids=[a.id for a in audits]
    findings=db.scalars(select(Finding).where(Finding.audit_id.in_(ids))).all() if ids else []
    approvals=db.scalars(select(Approval).where(Approval.audit_id.in_(ids))).all() if ids else []
    return {"total_audits":len(audits),
      "average_compliance_score":round(sum(a.score for a in audits)/len(audits),1) if audits else None,
      "total_findings":len(findings),"open_findings":sum(f.status=="open" for f in findings),
      "severity_breakdown":{s:sum(f.severity==s for f in findings) for s in ("critical","high","medium","low")},
      "approved_audits":sum(x.decision=="approved" for x in approvals),
      "changes_requested":sum(x.decision=="changes_requested" for x in approvals)}
