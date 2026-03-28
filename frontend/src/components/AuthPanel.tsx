import { useMemo, useState, type FormEvent } from 'react'

type AuthMode = 'login' | 'register' | 'request_reset' | 'reset_password'

interface AuthPanelProps {
  busy: boolean
  passwordResetToken?: string
  registrationEnabled: boolean
  onCancelPasswordReset: () => void
  onLogin: (payload: { email: string; password: string }) => Promise<void>
  onRequestPasswordReset: (email: string) => Promise<void>
  onRegister: (payload: {
    email: string
    password: string
    full_name: string
    payout_address: string
  }) => Promise<void>
  onResetPassword: (payload: { token: string; new_password: string }) => Promise<void>
  onResendVerification: (email: string) => Promise<void>
  onDevelopmentVerify?: () => Promise<void>
  hasPendingDevelopmentVerification?: boolean
  sectionId?: string
}

const PASSWORD_MIN = 8
const PASSWORD_MAX = 128
const FULL_NAME_MIN = 2
const FULL_NAME_MAX = 255
const PAYOUT_MAX = 255

function helperTone(isValid: boolean, hasValue: boolean): 'valid' | 'warning' | 'muted' {
  if (!hasValue) {
    return 'muted'
  }
  return isValid ? 'valid' : 'warning'
}

function AuthPanel({
  busy,
  passwordResetToken = '',
  registrationEnabled,
  onCancelPasswordReset,
  onLogin,
  onRequestPasswordReset,
  onRegister,
  onResetPassword,
  onResendVerification,
  onDevelopmentVerify,
  hasPendingDevelopmentVerification = false,
  sectionId,
}: AuthPanelProps) {
  const [mode, setMode] = useState<AuthMode>(registrationEnabled ? 'register' : 'login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [payoutAddress, setPayoutAddress] = useState('')
  const hasPasswordResetToken = passwordResetToken.trim().length > 0
  const effectiveMode = hasPasswordResetToken
    ? 'reset_password'
    : !registrationEnabled && mode === 'register'
      ? 'login'
      : mode

  const passwordLength = password.length
  const fullNameLength = fullName.length
  const payoutLength = payoutAddress.length

  const passwordState = useMemo(() => {
    if (passwordLength === 0) {
      return {
        tone: 'muted' as const,
        text: `Requirement: ${PASSWORD_MIN}-${PASSWORD_MAX} characters.`,
      }
    }

    if (passwordLength < PASSWORD_MIN) {
      return {
        tone: 'warning' as const,
        text: `Add ${PASSWORD_MIN - passwordLength} more characters to reach the minimum of ${PASSWORD_MIN}.`,
      }
    }

    return {
      tone: 'valid' as const,
      text: `Password length looks good: ${passwordLength}/${PASSWORD_MAX} characters.`,
    }
  }, [passwordLength])

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (effectiveMode === 'reset_password') {
      await onResetPassword({ token: passwordResetToken, new_password: password })
      return
    }
    if (effectiveMode === 'request_reset') {
      await onRequestPasswordReset(email)
      return
    }
    if (effectiveMode === 'login') {
      await onLogin({ email, password })
      return
    }
    await onRegister({ email, password, full_name: fullName, payout_address: payoutAddress })
  }

  return (
    <section className="panel auth-panel" id={sectionId}>
      <div className="auth-header">
        <div>
          <h2>
            {effectiveMode === 'register'
              ? 'Create creator account'
              : effectiveMode === 'request_reset'
                ? 'Reset password'
                : effectiveMode === 'reset_password'
                  ? 'Choose a new password'
                  : 'Sign in'}
          </h2>
          <p className="panel-intro">
            {effectiveMode === 'register'
              ? 'Create an account to publish structured ideas into the public repository. You must confirm the email address before login and publishing are enabled.'
              : effectiveMode === 'request_reset'
                ? 'Enter the verified email on your account and the app will send a password reset link.'
                : effectiveMode === 'reset_password'
                  ? 'Choose a new 8-128 character password. Completing this step will sign you straight back in.'
                  : 'Use the same verified email and 8-128 character password you created during registration.'}
          </p>
          {!registrationEnabled ? (
            <p className="field-helper warning">
              Registration is temporarily disabled on this deployment until outbound verification
              email is configured.
            </p>
          ) : null}
        </div>
        {!hasPasswordResetToken && effectiveMode !== 'request_reset' ? (
          <div className="segmented-control">
            <button
              className={effectiveMode === 'register' ? 'active' : ''}
              disabled={!registrationEnabled}
              onClick={() => setMode('register')}
              type="button"
            >
              Register
            </button>
            <button
              className={effectiveMode === 'login' ? 'active' : ''}
              onClick={() => setMode('login')}
              type="button"
            >
              Sign in
            </button>
          </div>
        ) : null}
      </div>
      <form onSubmit={submit} className="form-grid">
        {effectiveMode === 'register' ? (
          <label>
            <span className="field-label-row">
              <span>Full name</span>
              <span className="field-limit">
                {FULL_NAME_MIN}-{FULL_NAME_MAX} chars · {fullNameLength}/{FULL_NAME_MAX}
              </span>
            </span>
            <input
              autoComplete="name"
              maxLength={FULL_NAME_MAX}
              minLength={FULL_NAME_MIN}
              value={fullName}
              onChange={(event) => setFullName(event.target.value)}
              placeholder="Ada Lovelace"
              required
            />
            <span
              className={`field-helper ${helperTone(
                fullNameLength >= FULL_NAME_MIN,
                fullNameLength > 0,
              )}`}
            >
              {fullNameLength === 0
                ? 'Use your real or professional display name.'
                : fullNameLength >= FULL_NAME_MIN
                  ? 'Name length looks good.'
                  : `Add ${FULL_NAME_MIN - fullNameLength} more character to continue.`}
            </span>
          </label>
        ) : null}
        {!hasPasswordResetToken ? (
          <label>
            <span className="field-label-row">
              <span>Email</span>
              <span className="field-limit">Used for login and ownership records</span>
            </span>
            <input
              autoCapitalize="none"
              autoComplete={effectiveMode === 'register' ? 'email' : 'username'}
              autoCorrect="off"
              spellCheck={false}
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@example.com"
              required
            />
            <span className="field-helper muted">
              Use an email you expect to control long-term. It is used for login, ownership
              records, and verification.
            </span>
          </label>
        ) : null}
        {effectiveMode !== 'request_reset' ? (
          <label>
            <span className="field-label-row">
              <span>{hasPasswordResetToken ? 'New password' : 'Password'}</span>
              <span className="field-limit">
                {PASSWORD_MIN}-{PASSWORD_MAX} chars · {passwordLength}/{PASSWORD_MAX}
              </span>
            </span>
            <input
              autoComplete={effectiveMode === 'login' ? 'current-password' : 'new-password'}
              type="password"
              maxLength={PASSWORD_MAX}
              minLength={PASSWORD_MIN}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="At least 8 characters"
              required
            />
            <span className={`field-helper ${passwordState.tone}`}>{passwordState.text}</span>
          </label>
        ) : null}
        {effectiveMode === 'register' ? (
          <label>
            <span className="field-label-row">
              <span>Reward address</span>
              <span className="field-limit">Optional · up to {PAYOUT_MAX} chars</span>
            </span>
            <input
              autoCorrect="off"
              spellCheck={false}
              maxLength={PAYOUT_MAX}
              value={payoutAddress}
              onChange={(event) => setPayoutAddress(event.target.value)}
              placeholder="Wallet, handle, or other future reward route"
            />
            <span className={`field-helper ${helperTone(true, payoutLength > 0)}`}>
              {payoutLength === 0
                ? 'Optional. Add this only if you want a public reward route attached to your published signals.'
                : `Saved as ${payoutLength}/${PAYOUT_MAX} characters.`}
            </span>
          </label>
        ) : null}
        {effectiveMode === 'reset_password' ? (
          <div className="full-width auth-mode-note">
            This reset link is single-use. If it has expired, go back and request a fresh one.
          </div>
        ) : null}
        <button className="primary-button" disabled={busy} type="submit">
          {busy
            ? 'Working...'
            : effectiveMode === 'register'
              ? 'Create account'
              : effectiveMode === 'request_reset'
                ? 'Email reset link'
                : effectiveMode === 'reset_password'
                  ? 'Save new password'
                  : 'Log in'}
        </button>
        {effectiveMode === 'login' ? (
          <>
            <button
              className="secondary-button"
              disabled={busy || email.trim().length === 0}
              onClick={() => {
                void onResendVerification(email)
              }}
              type="button"
            >
              Resend verification email
            </button>
            <button
              className="secondary-button"
              disabled={busy}
              onClick={() => setMode('request_reset')}
              type="button"
            >
              Forgot password
            </button>
          </>
        ) : null}
        {effectiveMode === 'request_reset' ? (
          <button
            className="secondary-button"
            disabled={busy}
            onClick={() => setMode('login')}
            type="button"
          >
            Back to sign in
          </button>
        ) : null}
        {effectiveMode === 'reset_password' ? (
          <button
            className="secondary-button"
            disabled={busy}
            onClick={onCancelPasswordReset}
            type="button"
          >
            Back to sign in
          </button>
        ) : null}
      </form>
      {effectiveMode === 'register' ? (
        <aside className="signup-explainer">
          <strong>Publishing rules</strong>
          <p>
            This is a public repository for AI-readable ideas. Verification protects account
            ownership, but it does not make the repository private.
          </p>
          <ul className="signup-checklist">
            <li>Verify the registration email before you can log in or publish ideas.</li>
            <li>Use a reachable email you expect to keep long-term.</li>
            <li>Add a reward address only if you want a public follow-up route.</li>
            <li>Assume your submitted ideas and disclosed contact details will be public.</li>
          </ul>
          <p>
            No execution, reward, or recognition is guaranteed. The point is durable publication of
            a structured signal.
          </p>
        </aside>
      ) : null}
      {hasPendingDevelopmentVerification && onDevelopmentVerify ? (
        <div className="dev-verification-panel">
          <strong>Development shortcut</strong>
          <p>
            Local log mode exposes a direct verification step so you can finish the signup flow
            without a real SMTP server.
          </p>
          <button
            className="secondary-button"
            disabled={busy}
            onClick={() => {
              void onDevelopmentVerify()
            }}
            type="button"
          >
            Verify email now (development)
          </button>
        </div>
      ) : null}
    </section>
  )
}

export default AuthPanel
