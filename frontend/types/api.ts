export type FindingStatus = "open" | "accepted" | "dismissed" | "resolved";
export type FindingSeverity = "critical" | "high" | "medium" | "low";
export type ApprovalDecision = "approved" | "changes_requested";

export interface Workspace {
  id: string;
  name: string;
  description: string | null;
}

export interface WorkspaceIn {
  name: string;
  description?: string | null;
}

export interface Document {
  id: string;
  filename: string;
  kind: string;
  character_count: number;
  created_at: string;
}

export interface BrandRuleIn {
  workspace_id: string;
  title: string;
  description: string;
  category?: string;
  severity?: string;
  source_document_id?: string | null;
  verified?: boolean;
}

export interface ApprovedFact {
  id: string;
  subject: string;
  attribute: string;
  approved_value: string;
  unit: string | null;
  verified: boolean;
  source_document_id: string | null;
}

export interface FactIn {
  workspace_id: string;
  subject: string;
  attribute: string;
  approved_value: string;
  unit?: string | null;
  source_document_id?: string | null;
  verified?: boolean;
}

export interface Terminology {
  id: string;
  term: string;
  replacement: string | null;
  term_type: string;
  case_sensitive: boolean;
}

export interface TermIn {
  workspace_id: string;
  term: string;
  replacement?: string | null;
  term_type?: string;
  case_sensitive?: boolean;
}

export interface AuditIn {
  workspace_id: string;
  document_id: string;
}

export interface Evidence {
  source_type: string;
  source_id: string;
  source_text: string;
}

export interface Finding {
  id: string;
  category: string;
  finding_type: string;
  severity: FindingSeverity;
  status: FindingStatus;
  detected_text: string;
  explanation: string;
  suggestion: string;
  confidence: number;
  evidence: Evidence[];
  start_offset: number;
  end_offset: number;
}

export interface Approval {
  decision: ApprovalDecision;
  reviewer: string;
  comment: string | null;
  decided_at: string;
}

export interface Audit {
  id: string;
  workspace_id: string;
  document_id: string;
  status: string;
  compliance_score: number;
  summary: string;
  created_at: string;
  findings: Finding[];
  approval: Approval | null;
}

export interface RevisionIn {
  content: string;
  actor?: string;
}

export interface ApprovalIn {
  decision: ApprovalDecision;
  reviewer?: string;
  comment?: string | null;
}

export interface AnalyticsOverview {
  total_audits: number;
  average_compliance_score: number;
  total_findings: number;
  open_findings: number;
  severity_breakdown: Record<FindingSeverity, number>;
  approved_audits: number;
  changes_requested: number;
}

export interface AuditEvent {
  id: string;
  audit_id: string | null;
  actor: string;
  action: string;
  details: Record<string, unknown>;
  created_at: string;
}

export interface HealthResponse {
  status: string;
  database: string;
}

export type BrandRule = BrandRuleIn & { id: string };