// User Types
export interface User {
  id: string;
  email: string;
  full_name?: string;
  phone?: string;
  company?: string;
  role: string;
  tier: string;
  credits_remaining: number;
  email_verified: boolean;
  created_at: string;
  updated_at?: string;
}

export interface Token {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  email: string;
  password: string;
  full_name?: string;
  phone?: string;
  company?: string;
}

export interface PasswordChange {
  current_password: string;
  new_password: string;
}

export interface PasswordResetRequest {
  email: string;
}

export interface PasswordReset {
  token: string;
  new_password: string;
}

// Property Types
export interface Property {
  id: string;
  user_id: string;
  property_address?: string;
  property_city?: string;
  property_zone?: string;
  property_description?: string;
  status: string;
  created_at: string;
  updated_at?: string;
}

export interface PropertyDetail extends Property {
  documents: Document[];
}

export interface PropertyCreate {
  property_address?: string;
  property_city?: string;
  property_zone?: string;
  property_description?: string;
}

export interface PropertyUpdate extends Partial<PropertyCreate> {
  status?: string;
}

// Document Types
export type DocumentStatus = 'pending' | 'processing' | 'completed' | 'failed';
export type DocumentType = 'title_deed' | 'sale_agreement' | 'tax_record' | 'lease' | 'other';

export interface Document {
  id: string;
  property_id: string;
  user_id: string;
  document_type?: DocumentType;
  filename: string;
  file_size: number;
  mime_type: string;
  status: DocumentStatus;
  processing_progress: number;
  page_count?: number;
  created_at: string;
  processed_at?: string;
  metadata: Record<string, unknown>;
}

export interface DocumentDetail extends Document {
  extracted_text?: string;
  ocr_used: boolean;
  ocr_confidence?: number;
}

export interface DocumentUploadResponse {
  id: string;
  filename: string;
  document_type?: string;
  status: string;
  message: string;
}

export interface DocumentListResponse {
  items: Document[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

// Analysis Types
export interface AnalysisJob {
  id: string;
  user_id: string;
  property_id: string;
  status: string;
  analysis_types?: string[];
  created_at: string;
  updated_at?: string;
  completed_at?: string;
}

export interface AnalysisRequest {
  property_id: string;
  analysis_types?: string[];
}

export interface AnalysisResponse {
  job_id: string;
  status: string;
  message: string;
  estimated_time: number;
}

export interface AnalysisStatusResponse {
  job_id: string;
  status: string;
  progress: number;
  results?: Record<string, unknown>;
  error?: string;
  created_at: string;
  updated_at?: string;
  completed_at?: string;
}

export interface Report {
  id: string;
  analysis_job_id: string;
  property_id: string;
  user_id: string;
  content: string;
  pdf_path?: string;
  created_at: string;
  viewed_at?: string;
}

// RAG Types
export interface SearchQuery {
  query: string;
  document_type?: DocumentType;
  limit?: number;
}

export interface SearchResult {
  document_id: string;
  chunk_text: string;
  page_number?: number;
  section_title?: string;
  relevance_score: number;
}

export interface AnalysisRequestRAG {
  query: string;
  document_type?: DocumentType;
  analysis_type?: string;
  limit?: number;
}

export interface AnalysisResponseRAG {
  query: string;
  analysis_type?: string;
  response: string;
  documents_used: {
    document_id: string;
    chunk_index?: number;
    page_number?: number;
    relevance_score: number;
  }[];
}

export interface IndexStats {
  total_documents: number;
  total_chunks: number;
  last_updated: string;
}

// API Response Types
export interface ApiError {
  detail: string;
}

export interface ApiResponse<T> {
  data?: T;
  error?: ApiError;
}

// Pagination
export interface PaginationParams {
  skip?: number;
  limit?: number;
}
