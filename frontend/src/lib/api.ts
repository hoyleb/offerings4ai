import type {
  DashboardSummary,
  EmailVerificationResponse,
  Idea,
  IdeaPayload,
  RegistrationResponse,
  TokenResponse,
  User,
  VerificationDispatchResponse,
} from '../types'

const LOCAL_HOSTNAMES = new Set(['localhost', '127.0.0.1'])

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
  if (typeof window === 'undefined') {
    return 'http://localhost:8899'
  }

  if (LOCAL_HOSTNAMES.has(window.location.hostname)) {
    return 'http://localhost:8899'
  }

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

async function request<T>(path: string, init: RequestInit = {}, token?: string): Promise<T> {
  const headers = new Headers(init.headers)
  headers.set('Content-Type', 'application/json')
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
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
    throw new Error(message)
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
 * Send a fresh verification email when an account is still pending confirmation.
 */
export function resendVerificationEmail(email: string): Promise<VerificationDispatchResponse> {
  return request<VerificationDispatchResponse>('/api/auth/resend-verification', {
    method: 'POST',
    body: JSON.stringify({ email }),
  })
}

/**
 * Fetch the currently authenticated creator profile.
 */
export function fetchMe(token: string): Promise<User> {
  return request<User>('/api/auth/me', {}, token)
}

/**
 * Submit a structured idea into the Offering4AI evaluation pipeline.
 */
export function submitIdea(token: string, payload: IdeaPayload): Promise<Idea> {
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
export function fetchIdeas(token: string): Promise<Idea[]> {
  return request<Idea[]>('/api/ideas', {}, token)
}

/**
 * Fetch aggregate creator metrics for the dashboard cards.
 */
export function fetchDashboard(token: string): Promise<DashboardSummary> {
  return request<DashboardSummary>('/api/ideas/dashboard', {}, token)
}
