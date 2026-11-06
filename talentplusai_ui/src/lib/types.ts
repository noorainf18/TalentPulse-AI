/**
 * types.ts
 * All TypeScript types derived directly from the Django backend serializers.
 * Keep this file as the single source of truth for API shapes.
 */

// ── Skill structure ───────────────────────────────────────────────
// Skills are now [{category, skills[]}] — preserving resume section headings.
export interface SkillGroup {
  category: string;   // e.g. "Programming & Frameworks", "AI, ML & Generative AI"
  skills: string[];   // individual skill/tool names
}

// ── Candidates List (GET /api/dashboard/candidates/) ─────────────
export interface CandidateListItem {
  id: string;
  name: string;
  email: string;
  github_url: string | null;
  skills: SkillGroup[];       // categorized
  created_at: string;
  score: number | null;
  evaluation_status: EvaluationStatus;
  candidate_label: CandidateLabel;
}

export interface CandidatesListResponse {
  count: number;
  results: CandidateListItem[];
}

// ── Evaluation Status ─────────────────────────────────────────────
export type EvaluationStatus =
  | "pending"
  | "screening_sent"
  | "rejected"
  | "borderline"
  | "hired";

export type CandidateLabel =
  | "Strong Match"
  | "Hidden Gem"
  | "Promising"
  | "Needs Development"
  | "Not a Fit"
  | "Pending";

// ── Score Breakdown ───────────────────────────────────────────────
export interface ScoreBreakdown {
  overall: number;
  technical: number;
  culture: number;
  experience: number;
}

// ── Trace Step ────────────────────────────────────────────────────
export interface TraceStep {
  step: string;
  message: string;
  status: "done" | "running" | "error";
}

// ── GitHub Evidence ───────────────────────────────────────────────
export interface RepoAnalysed {
  name: string;
  is_fork: boolean;
  stars: number;
  description: string;
  languages: Record<string, number>;
  readme_snippet: string;
  commits: {
    total_commits_fetched: number;
    recent_commits_90_days: number;
    sample_messages: string[];
  };
}

export interface GitHubEvidence {
  username?: string;
  profile_url?: string;
  has_original_work?: boolean;
  total_recent_commits?: number;
  primary_languages?: Record<string, number>;
  repos_analysed?: RepoAnalysed[];
  skipped?: boolean;
  reason?: string;
  error?: string;
}

// ── Gap Analysis ──────────────────────────────────────────────────
export interface RoleMatch {
  job_id: number;
  role_title: string;
  department: string;
  seniority: string;
  hiring_priority: string;
  overall_fit_score: number;
  required_skill_coverage: number;
  preferred_skill_coverage: number;
  required_skills_matched: string[];
  required_skills_missing: string[];
  preferred_skills_matched: string[];
  preferred_skills_missing: string[];
  fills_critical_team_gap: boolean;
  culture_values: string[];
  min_experience_years: number;
  tech_stack_focus: string;
}

export interface GapAnalysis {
  best_match_role: string;
  best_match_department: string;
  best_match_fit_score: number;
  critical_gaps: string[];
  nice_to_have_gaps: string[];
  fills_team_gap: boolean;
  top_role_matches: RoleMatch[];
  candidate_skills?: SkillGroup[];
}

// ── Evidence Panel ────────────────────────────────────────────────
// ── Voice interview (embedded in GET /api/dashboard/candidate/<id>/ and voice APIs) ──
export interface VoiceAnswer {
  id: string;
  answer_text: string;
  duration_seconds: number | null;
  answer_score: number | null;
  score_reasoning: string;
}

export interface VoiceQuestion {
  id: string;
  question_text: string;
  question_type: string;
  target_skill: string;
  sequence_order: number;
  expected_answer_signals: unknown[];
  answer: VoiceAnswer | null;
}

export interface VoiceInterviewDetail {
  id: string;
  status: string;
  livekit_room_name: string;
  session_token: string;
  join_url: string;
  invite_sent_at: string | null;
  scheduled_at: string | null;
  started_at: string | null;
  ended_at: string | null;
  duration_seconds: number | null;
  transcript_text: string;
  voice_composite_score: number | null;
  final_merged_score: number | null;
  questions: VoiceQuestion[];
  error_message: string;
  created_at: string;
}

/** GET /api/voice/session/?token= — candidate UI brief */
export interface VoiceSessionQuestionBrief {
  id: string;
  sequence_order: number;
  question_text: string;
  answered: boolean;
  answer_preview: string;
}

export interface VoiceSessionBrief {
  interview_id: string;
  status: string;
  role_title: string;
  candidate_display_name: string;
  questions: VoiceSessionQuestionBrief[];
}

/** GET /api/voice/<id>/status/ */
export interface VoiceInterviewSummary {
  id: string;
  status: string;
  voice_composite_score: number | null;
  final_merged_score: number | null;
  duration_seconds: number | null;
  started_at: string | null;
  ended_at: string | null;
}

export interface EvidencePanelReady {
  kind: "ready";
  id: string;
  target_role: string;
  candidate_name: string;
  candidate_email: string;
  candidate_github_url: string | null;
  candidate_skills: SkillGroup[];        // categorized
  parsed_resume: Record<string, unknown> | null;
  score_breakdown: ScoreBreakdown;
  reasoning: string;
  github_evidence: GitHubEvidence | null;
  gap_analysis: GapAnalysis | null;
  trace_steps: TraceStep[];
  status: EvaluationStatus;
  email_sent: boolean;
  feedback_thumbs_up: boolean | null;
  feedback_notes: string;
  evaluated_at: string;
  /** Present when a voice screen exists for this evaluation (from voice_interview OneToOne). */
  voice_interview: VoiceInterviewDetail | null;
}

export interface EvidencePanelPending {
  kind: "pending";
  candidate_id: string;
  candidate_name: string;
  status: "pending";
  message: string;
}

export type EvidencePanel = EvidencePanelReady | EvidencePanelPending;

// ── Agent Status ──────────────────────────────────────────────────
export interface AgentStatus {
  candidate_id: string;
  status: EvaluationStatus;
  score: number | null;
  candidate_label: string | null;
  trace_log: TraceStep[];
  email_sent: boolean;
}

// ── WebSocket message ─────────────────────────────────────────────
export interface WsEvaluationUpdate {
  type: "evaluation_update";
  candidate_id: string;
  status: EvaluationStatus;
  score: number | null;
  technical_score: number;
  culture_score: number;
  experience_score: number;
  reasoning: string;
  trace_log: TraceStep[];
  email_sent: boolean;
  error?: string;
}

// ── Upload Response ───────────────────────────────────────────────
export interface UploadResponseNew {
  kind: "created";
  message: string;
  candidate_id: string;
  evaluation_id?: string;
}

export interface UploadResponseDuplicate {
  kind: "duplicate";
  message: string;
  candidate_id: string;
  evaluation_id?: string;
}

export type UploadResponse = UploadResponseNew | UploadResponseDuplicate;

// ── Feedback ──────────────────────────────────────────────────────
export interface FeedbackRequest {
  candidate_id: string;
  thumbs_up: boolean;
  notes?: string;
}

export interface FeedbackResponse {
  message: string;
  candidate_id: string;
  thumbs_up: boolean;
}

// ── Agent Run ─────────────────────────────────────────────────────
export interface AgentRunResponse {
  message: string;
  candidate_id: string;
}

// ── RAG Chat ──────────────────────────────────────────────────────
export interface RagAskRequest {
  question: string;
  session_id?: string;
  /**
   * FIX: Scope all retrieval to a single candidate UUID.
   * When set, the backend will filter the vector store, BM25 corpus, and
   * answer cache to this candidate only — preventing cross-candidate
   * hallucination. Pass the candidate's UUID whenever the chat is opened
   * from a specific candidate's evidence panel.
   */
  candidate_id?: string;
  top_k?: number;
}

export interface RagCitation {
  rank: number;
  candidate_id: string;
  chunk_index: number;
  score: number;
}

export interface RagAskResponse {
  session_id: string;
  answer: string;
  citations: RagCitation[];
  retrieved_count: number;
}

// ── Dashboard Summary ─────────────────────────────────────────────
export interface DashboardKpis {
  total_candidates: number;
  pending: number;
  review_queue: number;
  hired: number;
  rejected: number;
  avg_score: number | null;
}

export interface DashboardRecentActivityItem {
  candidate_id: string;
  name: string;
  email: string;
  status: EvaluationStatus;
  score: number | null;
  created_at: string;
}

export interface DashboardSummaryResponse {
  kpis: DashboardKpis;
  recent_activity: DashboardRecentActivityItem[];
}