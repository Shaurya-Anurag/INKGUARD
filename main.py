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
def evaluate(db,wid,content):
    out=[]
    terms=db.scalars(select(Terminology).where(Terminology.workspace_id==wid)).all()
    rules=db.scalars(select(BrandRule).where(BrandRule.workspace_id==wid,BrandRule.verified.is_(True))).all()
    facts=db.scalars(select(ApprovedFact).where(ApprovedFact.workspace_id==wid,ApprovedFact.verified.is_(True))).all()
    for t in terms:
        hay=content if t.case_sensitive else content.lower()
        needle=t.term if t.case_sensitive else t.term.lower()
        pos=hay.find(needle)
        if pos>=0 and t.term_type=="prohibited":
            out.append(dict(category="terminology",finding_type="terminology_violation",severity="high",
              detected_text=content[pos:pos+len(t.term)],explanation=f"'{t.term}' is prohibited terminology.",
              suggestion=f"Replace with '{t.replacement}'." if t.replacement else "Use approved terminology.",
              confidence=.99,evidence=[{"source_type":"terminology","source_id":t.id,"source_text":t.term}],
              start_offset=pos,end_offset=pos+len(t.term)))
    for r in rules:
        m=re.search(r"(?:avoid|prohibited)\s*:\s*['\"]?([^.;\n'\"]+)",r.description,re.I)
        if m:
            phrase=m.group(1).strip(); pos=content.lower().find(phrase.lower())
            if pos>=0:
                out.append(dict(category=r.category,finding_type="brand_rule_violation",severity=r.severity,
                  detected_text=content[pos:pos+len(phrase)],explanation=f"{r.title}: {r.description}",
                  suggestion="Revise this text to comply with the verified brand rule.",confidence=.96,
                  evidence=[{"source_type":"brand_rule","source_id":r.id,"source_text":r.title+": "+r.description}],
                  start_offset=pos,end_offset=pos+len(phrase)))
    for pattern,kind,why in CLAIM_PATTERNS:
        for m in re.finditer(pattern,content,re.I):
            out.append(dict(category="claims",finding_type=kind,severity="high",detected_text=m.group(),
              explanation=why+" This is a wording flag, not a determination that the claim is false.",
              suggestion="Verify against approved substantiation or rewrite as a qualified claim.",
              confidence=.78,evidence=[],start_offset=m.start(),end_offset=m.end()))
    # Numeric mismatch heuristic: only compare numbers in nearby subject/attribute context.
    for fact in facts:
        approved=re.findall(r"\d+(?:\.\d+)?",fact.approved_value)
        if not approved: continue
        keywords=[x.lower() for x in re.split(r"\W+",fact.subject+" "+fact.attribute) if len(x)>2]
        for m in re.finditer(r"\b\d+(?:\.\d+)?\s*%?",content):
            window=content[max(0,m.start()-100):min(len(content),m.end()+100)].lower()
            if keywords and not any(k in window for k in keywords): continue
            if m.group().strip().rstrip("%") not in approved:
                out.append(dict(category="product_fact",finding_type="fact_contradiction",severity="critical",
                  detected_text=m.group(),explanation=f"Potential mismatch near {fact.subject}/{fact.attribute}. Approved value: {fact.approved_value} {fact.unit or ''}".strip(),
                  suggestion=f"Verify against approved value: {fact.approved_value} {fact.unit or ''}".strip(),
                  confidence=.82,evidence=[{"source_type":"approved_fact","source_id":fact.id,
                  "source_text":f"{fact.subject} — {fact.attribute}: {fact.approved_value} {fact.unit or ''}".strip()}],
                  start_offset=m.start(),end_offset=m.end()))
    unique=[]; seen=set()
    for f in out:
        key=(f["finding_type"],f["start_offset"],f["end_offset"],f["detected_text"].lower())
        if key not in seen: seen.add(key); unique.append(f)
    return unique
def run_audit(db,wid,doc,content):
    items=evaluate(db,wid,content)
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
    raw=await file.read()
    if len(raw)>MAX_UPLOAD_MB*1024*1024: raise HTTPException(413,f"Maximum upload size is {MAX_UPLOAD_MB} MB.")
    suffix=Path(filename).suffix.lower(); target=STORAGE/(uuid.uuid4().hex+suffix); target.write_bytes(raw)
    try: text=extract(target,filename)
    except Exception as e:
        target.unlink(missing_ok=True); raise HTTPException(422,f"Text extraction failed: {e}")
    if not text.strip():
        target.unlink(missing_ok=True); raise HTTPException(422,"No text extracted. Scanned PDFs need OCR; OCR is not included.")
    d=Document(workspace_id=workspace_id,filename=filename,content_type=file.content_type,
      storage_path=str(target),extracted_text=text,sha256=hashlib.sha256(raw).hexdigest(),kind=kind)
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

@app.post("/api/audits",status_code=201)
def create_audit_endpoint(p:AuditIn,db:Session=Depends(db_session)):
    workspace_or_404(db,p.workspace_id); d=db.get(Document,p.document_id)
    if not d or d.workspace_id!=p.workspace_id: raise HTTPException(404,"Document not found in workspace.")
    if d.kind!="submission": raise HTTPException(400,"Upload the content as kind=submission before auditing.")
    return audit_json(db,run_audit(db,p.workspace_id,d,d.extracted_text))
@app.get("/api/audits")
def list_audits(workspace_id:str,db:Session=Depends(db_session)):
    workspace_or_404(db,workspace_id); rows=db.scalars(select(Audit).where(Audit.workspace_id==workspace_id).order_by(Audit.created_at.desc())).all()
    return [{"id":a.id,"document_id":a.document_id,"status":a.status,"compliance_score":a.score,
      "finding_count":db.scalar(select(func.count(Finding.id)).where(Finding.audit_id==a.id)) or 0,
      "created_at":a.created_at.isoformat()} for a in rows]
@app.get("/api/audits/{aid}")
def get_audit(aid:str,db:Session=Depends(db_session)):
    a=db.get(Audit,aid)
    if not a: raise HTTPException(404,"Audit not found")
    return audit_json(db,a)
@app.post("/api/audits/{aid}/revisions",status_code=201)
def add_revision(aid:str,p:RevisionIn,db:Session=Depends(db_session)):
    a=db.get(Audit,aid)
    if not a: raise HTTPException(404,"Audit not found")
    n=(db.scalar(select(func.max(Revision.revision_number)).where(Revision.audit_id==aid)) or 0)+1
    r=Revision(audit_id=aid,revision_number=n,content=p.content); db.add(r)
    log_event(db,a.workspace_id,"revision.created",aid,p.actor,{"revision_number":n}); db.commit(); db.refresh(r)
    return {"id":r.id,"audit_id":aid,"revision_number":n,"content":r.content}
@app.post("/api/audits/{aid}/reevaluate")
def reevaluate(aid:str,db:Session=Depends(db_session)):
    a=db.get(Audit,aid)
    if not a: raise HTTPException(404,"Audit not found")
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
    f.status=status; a=db.get(Audit,f.audit_id)
    log_event(db,a.workspace_id,"finding.status_updated",a.id,details={"finding_id":fid,"status":status}); db.commit()
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
