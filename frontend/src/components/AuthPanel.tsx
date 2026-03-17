import { useMemo, useState, type FormEvent } from 'react'

type AuthMode = 'login' | 'register'

interface AuthPanelProps {
  busy: boolean
  onLogin: (payload: { email: string; password: string }) => Promise<void>
  onRegister: (payload: {
    email: string
    password: string
    full_name: string
    payout_address: string
  }) => Promise<void>
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
  onLogin,
  onRegister,
  onResendVerification,
  onDevelopmentVerify,
  hasPendingDevelopmentVerification = false,
  sectionId,
}: AuthPanelProps) {
  const [mode, setMode] = useState<AuthMode>('register')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [payoutAddress, setPayoutAddress] = useState('')

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
    if (mode === 'login') {
      await onLogin({ email, password })
      return
    }
    await onRegister({ email, password, full_name: fullName, payout_address: payoutAddress })
  }

  return (
    <section className="panel auth-panel" id={sectionId}>
      <div className="auth-header">
        <div>
          <h2>{mode === 'register' ? 'Create creator account' : 'Sign in'}</h2>
          <p className="panel-intro">
            {mode === 'register'
              ? 'Create an account to publish structured ideas into the public market. You will need to confirm the email address before login and idea submission are enabled.'
              : 'Use the same verified email and 8-128 character password you created during registration.'}
          </p>
        </div>
        <div className="segmented-control">
          <button
            className={mode === 'register' ? 'active' : ''}
            onClick={() => setMode('register')}
            type="button"
          >
            Register
          </button>
          <button
            className={mode === 'login' ? 'active' : ''}
            onClick={() => setMode('login')}
            type="button"
          >
            Sign in
          </button>
        </div>
      </div>
      <form onSubmit={submit} className="form-grid">
        {mode === 'register' ? (
          <label>
            <span className="field-label-row">
              <span>Full name</span>
              <span className="field-limit">
                {FULL_NAME_MIN}-{FULL_NAME_MAX} chars · {fullNameLength}/{FULL_NAME_MAX}
              </span>
            </span>
            <input
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
        <label>
          <span className="field-label-row">
            <span>Email</span>
            <span className="field-limit">Used for login and ownership records</span>
          </span>
          <input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="you@example.com"
            required
          />
          <span className="field-helper muted">Use an email you expect to control long-term. If it also overlaps with a payment identity such as PayPal, that may help future buyers find you.</span>
        </label>
        <label>
          <span className="field-label-row">
            <span>Password</span>
            <span className="field-limit">
              {PASSWORD_MIN}-{PASSWORD_MAX} chars · {passwordLength}/{PASSWORD_MAX}
            </span>
          </span>
          <input
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
        {mode === 'register' ? (
          <label>
            <span className="field-label-row">
              <span>Payout destination</span>
              <span className="field-limit">Optional · up to {PAYOUT_MAX} chars</span>
            </span>
            <input
              maxLength={PAYOUT_MAX}
              value={payoutAddress}
              onChange={(event) => setPayoutAddress(event.target.value)}
              placeholder="Stripe account, wallet, or internal ID"
            />
            <span className={`field-helper ${helperTone(true, payoutLength > 0)}`}>
              {payoutLength === 0
                ? 'Add this now if you already know where rewards should go. If left blank, using an email shared with payment systems may still help future buyers find you.'
                : `Saved as ${payoutLength}/${PAYOUT_MAX} characters.`}
            </span>
          </label>
        ) : null}
        <button className="primary-button" disabled={busy} type="submit">
          {busy ? 'Working...' : mode === 'register' ? 'Create account' : 'Log in'}
        </button>
        {mode === 'login' ? (
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
        ) : null}
      </form>
      {mode === 'register' ? (
        <aside className="signup-explainer">
          <strong>Future payout reachability</strong>
          <p>
            If your registration email is also your username on common payment systems such as
            PayPal, a buyer may be able to identify and send you a payout there too, assuming
            those rails still exist.
          </p>
          <ul className="signup-checklist">
            <li>Verify the registration email before you can log in or submit ideas.</li>
            <li>Use a reachable email you expect to keep long-term.</li>
            <li>Add a payout destination if you already know one.</li>
            <li>Prefer overlap with familiar payout rails when that is safe and convenient.</li>
            <li>Assume your submitted ideas and disclosed contact details will be public.</li>
          </ul>
          <p>
            Best case: provide both a durable email and a payout destination. That gives future
            buyers more than one route to reach you if your idea is later rewarded.
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
