export type ExportFormat =
  | "csv"
  | "json"
  | "xlsx"
  | "xml"
  | "sql"
  | "parquet"
  | "pdf"
  | "html"
  | "markdown"
  | "docx";

export type AgentStatusType = "pending" | "running" | "completed" | "failed";

export interface AgentStatusInfo {
  name: string;
  status: AgentStatusType;
  message?: string;
  started_at?: string;
  completed_at?: string;
}

export interface ExportFileInfo {
  filename: string;
  format: string;
  path: string;
  size_bytes: number;
  record_count: number;
  entity_name?: string | null;
  created_at?: string | null;
}

export interface ValidationErrorItem {
  entity: string;
  field?: string;
  record_index?: number;
  error_type: string;
  message: string;
  severity: "error" | "warning";
}

export interface ValidationReportData {
  is_valid: boolean;
  errors: ValidationErrorItem[];
  warnings: ValidationErrorItem[];
  records_checked: number;
  records_passed: number;
  records_failed: number;
}

export interface FieldSpec {
  name: string;
  data_type: string;
  constraints?: Record<string, any>;
  nullable: boolean;
  unique: boolean;
  description?: string;
  example?: any;
}

export interface RelationshipSpec {
  from_entity: string;
  from_field: string;
  to_entity: string;
  to_field: string;
  relationship_type: string;
}

export interface EntitySpec {
  name: string;
  fields: FieldSpec[];
  record_count: number;
  relationships: RelationshipSpec[];
  business_rules: string[];
  description?: string;
}

export interface RequirementSpec {
  entities: EntitySpec[];
  global_rules: string[];
  include_edge_cases: boolean;
  include_nulls: boolean;
  include_duplicates: boolean;
  output_formats: string[];
}

export interface JobData {
  job_id: string;
  status: "pending" | "running" | "completed" | "failed";
  prompt: string;
  formats: string[];
  agent_statuses: AgentStatusInfo[];
  record_count: number;
  requirement_spec?: RequirementSpec;
  generation_plan?: Record<string, any>;
  generated_data?: Record<string, Record<string, any>[]>;
  validation_result?: ValidationReportData;
  export_files: ExportFileInfo[];
  error?: string;
  created_at?: string;
  updated_at?: string;
}

export interface DataPreviewResponse {
  entities: Record<string, Record<string, any>[]>;
  total_records: Record<string, number>;
  preview_limit: number;
}
