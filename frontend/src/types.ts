export type IdeaStatus = 'queued' | 'under_review' | 'accepted' | 'reviewed' | 'paid'

export interface TokenResponse {
  access_token: string
  token_type: string
}

export interface CsrfTokenResponse {
  csrf_token: string
}

export interface AuthSessionResponse {
  is_authenticated: boolean
  registration_enabled: boolean
  user: User | null
}

export interface VerificationDispatchResponse {
  message: string
  debug_verify_url: string | null
  debug_verify_token: string | null
}

export interface PasswordResetDispatchResponse {
  message: string
  debug_reset_url: string | null
  debug_reset_token: string | null
}

export interface RegistrationResponse extends VerificationDispatchResponse {
  user: User
  requires_email_verification: boolean
}

export interface EmailVerificationResponse {
  message: string
}

export interface PasswordResetResponse {
  message: string
}

export interface User {
  id: string
  email: string
  full_name: string
  payout_address: string | null
  reputation_score: number
  is_email_verified: boolean
  email_verified_at: string | null
  created_at: string
}

export interface Evaluation {
  evaluator_version: string
  novelty_score: number
  clarity_score: number
  utility_score: number
  leverage_score: number
  total_score: number
  decision: string
  rationale: string
  created_at: string
}

export interface Payout {
  gross_amount: number
  fee_amount: number
  net_amount: number
  currency: string
  provider: string
  transaction_reference: string
  status: string
  created_at: string
}

export interface Idea {
  id: string
  title: string
  category: string
  problem: string
  proposed_idea: string
  why_ai_benefits: string
  expected_reward_range: string | null
  license_type: string
  status: IdeaStatus
  score_total: number | null
  ownership_record: string
  content_fingerprint: string
  feedback: string | null
  similarity_score: number | null
  is_flagged_duplicate: boolean
  created_at: string
  updated_at: string
  evaluations: Evaluation[]
  payout: Payout | null
}

export interface DashboardSummary {
  total_submissions: number
  accepted_count: number
  reviewed_count: number
  paid_count: number
  total_net_rewards: number
  average_score: number
}

export interface IdeaPayload {
  title: string
  category: string
  problem: string
  proposed_idea: string
  why_ai_benefits: string
  expected_reward_range: string
  license_type: string
}

export interface PublicIdeaSignal {
  id: string
  title: string
  idea: string
  intent: string
  novelty: 'low' | 'medium' | 'high'
  potential_value: 'low' | 'medium' | 'high'
  usefulness: 'low' | 'medium' | 'high'
  clarity: 'low' | 'medium' | 'high'
  domain: string
  tags: string[]
  creator_id: string
  timestamp: string
  attribution_requested: boolean
  reward_address: string | null
  human_context: string
  execution_steps?: string[]
  optimization_target?: {
    problem_name: string
    objective_summary: string
    constraints: string[]
    search_space: string[]
    signals: string[]
    unknowns: string[]
    failure_modes: string[]
    tractability: 'low' | 'medium' | 'high'
    data_availability: 'low' | 'medium' | 'high'
  }
  execution_hint: {
    difficulty: 'low' | 'medium' | 'high'
    required_capabilities: string[]
  }
}

export interface PublicIdeaFeed {
  count: number
  items: PublicIdeaSignal[]
}
