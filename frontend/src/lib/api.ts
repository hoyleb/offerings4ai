import type {
  AuthSessionResponse,
  CsrfTokenResponse,
  DashboardSummary,
  EmailVerificationResponse,
  Idea,
  IdeaPayload,
  PasswordResetDispatchResponse,
  PasswordResetResponse,
  PublicIdeaFeed,
  RegistrationResponse,
  TokenResponse,
  User,
  VerificationDispatchResponse,
} from '../types'

const STATE_CHANGING_METHODS = new Set(['POST', 'PUT', 'PATCH', 'DELETE'])
let csrfTokenCache = ''


export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

function normalizeBaseUrl(value: string | null | undefined): string {
  if (!value) {
    return ''
  }
  return value.endsWith('/') ? value.slice(0, -1) : value
}

function readRuntimeApiBaseUrl(): string {
  if (typeof window === 'undefined') {
    return ''
  }

  return normalizeBaseUrl(window.__APP_CONFIG__?.API_BASE_URL)
}

function readBuildTimeApiBaseUrl(): string {
  return normalizeBaseUrl(import.meta.env.VITE_API_BASE_URL)
}

function inferDefaultApiBaseUrl(): string {
  return ''
}

export const API_BASE_URL =
  readRuntimeApiBaseUrl() || readBuildTimeApiBaseUrl() || inferDefaultApiBaseUrl()

function formatValidationLocation(location: unknown): string {
  if (!Array.isArray(location)) {
    return 'Field'
  }

  const path = location
    .filter((segment): segment is string | number => ['string', 'number'].includes(typeof segment))
    .filter((segment) => segment !== 'body')
    .map((segment) => String(segment).split('_').join(' '))
    .join(' → ')

  if (!path) {
    return 'Field'
  }

  return path.charAt(0).toUpperCase() + path.slice(1)
}

function formatApiDetail(detail: unknown): string {
  if (typeof detail === 'string') {
    return detail
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (typeof item === 'string') {
          return item
        }

        if (item && typeof item === 'object') {
          const message = 'msg' in item && typeof item.msg === 'string' ? item.msg : null
          const location = 'loc' in item ? formatValidationLocation(item.loc) : null
          if (message && location) {
            return `${location}: ${message}`
          }
          if (message) {
            return message
          }
        }

        return null
      })
      .filter((message): message is string => Boolean(message))

    if (messages.length > 0) {
      return messages.join(' • ')
    }
  }

  if (detail && typeof detail === 'object') {
    if ('message' in detail && typeof detail.message === 'string') {
      return detail.message
    }
    return JSON.stringify(detail)
  }

  return 'Unexpected API error'
}

async function ensureCsrfToken(): Promise<string> {
  if (csrfTokenCache) {
    return csrfTokenCache
  }

  const response = await fetch(`${API_BASE_URL}/api/auth/csrf`, {
    credentials: 'include',
  })
  if (!response.ok) {
    throw new ApiError(response.status, 'Unable to initialize browser security token')
  }
  const payload = (await response.json()) as CsrfTokenResponse
  csrfTokenCache = payload.csrf_token
  return csrfTokenCache
}

async function request<T>(path: string, init: RequestInit = {}, token?: string): Promise<T> {
  const headers = new Headers(init.headers)
  headers.set('Content-Type', 'application/json')
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }
  const method = (init.method ?? 'GET').toUpperCase()
  if (STATE_CHANGING_METHODS.has(method) && !token) {
    headers.set('X-CSRF-Token', await ensureCsrfToken())
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    credentials: 'include',
    headers,
  })

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`
    try {
      const payload = (await response.json()) as { detail?: unknown }
      if ('detail' in payload) {
        message = formatApiDetail(payload.detail)
      }
    } catch {
      message = response.statusText || message
    }
    throw new ApiError(response.status, message)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return (await response.json()) as T
}

/**
 * Register a creator account so the platform can attribute ideas and payouts.
 */
export function registerUser(payload: {
  email: string
  password: string
  full_name: string
  payout_address: string
}): Promise<RegistrationResponse> {
  return request<RegistrationResponse>('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

/**
 * Authenticate a creator and return the bearer token used for idea operations.
 */
export function loginUser(payload: { email: string; password: string }): Promise<TokenResponse> {
  return request<TokenResponse>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function logoutUser(): Promise<void> {
  await request('/api/auth/logout', {
    method: 'POST',
  })
  csrfTokenCache = ''
}

/**
 * Confirm an email verification token issued during registration.
 */
export function verifyEmail(token: string): Promise<EmailVerificationResponse> {
  return request<EmailVerificationResponse>('/api/auth/verify-email', {
    method: 'POST',
    body: JSON.stringify({ token }),
  })
}

/**
 * Inspect the current browser session without forcing anonymous visitors through 401s.
 */
export function fetchSession(): Promise<AuthSessionResponse> {
  return request<AuthSessionResponse>('/api/auth/session')
}

/**
 * Send a fresh verification email when an account is still pending confirmation.
 */
export function resendVerificationEmail(email: string): Promise<VerificationDispatchResponse> {
  return request<VerificationDispatchResponse>('/api/auth/resend-verification', {
    method: 'POST',
    body: JSON.stringify({ email }),
  })
}

/**
 * Request a password reset link for an existing verified account.
 */
export function requestPasswordReset(email: string): Promise<PasswordResetDispatchResponse> {
  return request<PasswordResetDispatchResponse>('/api/auth/request-password-reset', {
    method: 'POST',
    body: JSON.stringify({ email }),
  })
}

/**
 * Complete a password reset and establish a fresh browser session.
 */
export function resetPassword(payload: {
  token: string
  new_password: string
}): Promise<PasswordResetResponse> {
  return request<PasswordResetResponse>('/api/auth/reset-password', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

/**
 * Fetch the currently authenticated creator profile.
 */
export function fetchMe(token?: string): Promise<User> {
  return request<User>('/api/auth/me', {}, token)
}

/**
 * Submit a structured idea into the Offering4AI evaluation pipeline.
 */
export function submitIdea(payload: IdeaPayload, token?: string): Promise<Idea> {
  return request<Idea>(
    '/api/ideas',
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
    token,
  )
}

/**
 * List all ideas submitted by the current creator.
 */
export function fetchIdeas(token?: string): Promise<Idea[]> {
  return request<Idea[]>('/api/ideas/my/ideas', {}, token)
}

/**
 * Fetch aggregate creator metrics for the dashboard cards.
 */
export function fetchDashboard(token?: string): Promise<DashboardSummary> {
  return request<DashboardSummary>('/api/ideas/my/ideas/dashboard', {}, token)
}

/**
 * Fetch the public AI-readable idea repository used by the landing page and agent clients.
 */
export function fetchPublicIdeaFeed(limit = 100): Promise<PublicIdeaFeed> {
  return request<PublicIdeaFeed>(`/api/ideas?limit=${limit}`)
}
