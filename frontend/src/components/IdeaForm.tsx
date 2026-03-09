import { useState, type FormEvent } from 'react'

import type { IdeaPayload } from '../types'

interface IdeaFormProps {
  busy: boolean
  onSubmit: (payload: IdeaPayload) => Promise<boolean>
  sectionId?: string
}

const TITLE_MIN = 5
const TITLE_MAX = 120
const PROBLEM_MIN = 20
const PROBLEM_MAX = 5000
const IDEA_MIN = 20
const IDEA_MAX = 10000
const BENEFIT_MIN = 20
const BENEFIT_MAX = 5000
const REWARD_MAX = 64

const REWARD_OPTIONS = [
  {
    value: 'let_ai_decide',
    label: 'Let the AI decide',
    helper: 'Best default. The evaluator decides value from novelty, utility, and leverage.',
  },
  {
    value: 'equivalent_credits',
    label: 'Equivalent credits',
    helper: 'Future-facing non-fiat mode. Today this just signals that the AI should price the idea in platform credits rather than a cash range.',
  },
] as const

const initialState: IdeaPayload = {
  title: '',
  category: 'agent_workflow',
  problem: '',
  proposed_idea: '',
  why_ai_benefits: '',
  expected_reward_range: 'let_ai_decide',
  license_type: 'non_exclusive',
}

function getLengthHint(valueLength: number, min: number, max: number, optional = false): string {
  if (valueLength === 0 && optional) {
    return `Optional · up to ${max} chars`
  }
  return `${min}-${max} chars · ${valueLength}/${max}`
}

function getValidityTone(valueLength: number, min: number, optional = false): 'muted' | 'valid' | 'warning' {
  if (valueLength === 0) {
    return 'muted'
  }
  if (optional) {
    return 'valid'
  }
  return valueLength >= min ? 'valid' : 'warning'
}

function getMessage(
  valueLength: number,
  min: number,
  goodText: string,
  idleText: string,
  optional = false,
): string {
  if (valueLength === 0) {
    return idleText
  }
  if (!optional && valueLength < min) {
    return `Add ${min - valueLength} more characters to reach the minimum.`
  }
  return goodText
}

function IdeaForm({ busy, onSubmit, sectionId }: IdeaFormProps) {
  const [form, setForm] = useState<IdeaPayload>(initialState)

  const updateField = (field: keyof IdeaPayload, value: string) => {
    setForm((current) => ({ ...current, [field]: value }))
  }

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const succeeded = await onSubmit(form)
    if (succeeded) {
      setForm(initialState)
    }
  }

  return (
    <section className="panel" id={sectionId}>
      <div className="section-heading">
        <div>
          <h2>Submit structured idea</h2>
          <p>
            Every limit is visible up front, so you can finish the form once instead of guessing and
            resubmitting.
          </p>
        </div>
      </div>
      <div className="submission-disclosure">
        Public submission notice: safe submissions are published. Your contact email and optional
        payout destination may appear in public feeds so future buyers can reach you later. Do not
        submit secrets, confidential information, or anything you are not prepared to make public.
      </div>
      <form className="form-grid" onSubmit={submit}>
        <label>
          <span className="field-label-row">
            <span>Title</span>
            <span className="field-limit">{getLengthHint(form.title.length, TITLE_MIN, TITLE_MAX)}</span>
          </span>
          <input
            maxLength={TITLE_MAX}
            minLength={TITLE_MIN}
            value={form.title}
            onChange={(event) => updateField('title', event.target.value)}
            placeholder="Short, specific idea title"
            required
          />
          <span className={`field-helper ${getValidityTone(form.title.length, TITLE_MIN)}`}>
            {getMessage(
              form.title.length,
              TITLE_MIN,
              'Clear and concise titles help both humans and agents scan quickly.',
              'Aim for a compact title that says exactly what the idea is.',
            )}
          </span>
        </label>
        <label>
          <span className="field-label-row">
            <span>Category</span>
            <span className="field-limit">Used for routing and analytics</span>
          </span>
          <select value={form.category} onChange={(event) => updateField('category', event.target.value)}>
            <option value="agent_workflow">Agent workflow</option>
            <option value="product">Product</option>
            <option value="automation">Automation</option>
            <option value="research">Research</option>
            <option value="creative">Creative</option>
            <option value="other">Other</option>
          </select>
          <span className="field-helper muted">Pick the closest fit. It does not lock you into a niche forever.</span>
        </label>
        <label className="full-width">
          <span className="field-label-row">
            <span>Problem it addresses</span>
            <span className="field-limit">
              {getLengthHint(form.problem.length, PROBLEM_MIN, PROBLEM_MAX)}
            </span>
          </span>
          <textarea
            maxLength={PROBLEM_MAX}
            minLength={PROBLEM_MIN}
            rows={4}
            value={form.problem}
            onChange={(event) => updateField('problem', event.target.value)}
            placeholder="Describe the bottleneck, failure mode, or missed opportunity."
            required
          />
          <span className={`field-helper ${getValidityTone(form.problem.length, PROBLEM_MIN)}`}>
            {getMessage(
              form.problem.length,
              PROBLEM_MIN,
              'A concrete problem statement makes the idea easier to price and evaluate.',
              'Start with the current pain point or failure mode.',
            )}
          </span>
        </label>
        <label className="full-width">
          <span className="field-label-row">
            <span>Proposed idea</span>
            <span className="field-limit">{getLengthHint(form.proposed_idea.length, IDEA_MIN, IDEA_MAX)}</span>
          </span>
          <textarea
            maxLength={IDEA_MAX}
            minLength={IDEA_MIN}
            rows={5}
            value={form.proposed_idea}
            onChange={(event) => updateField('proposed_idea', event.target.value)}
            placeholder="Describe the solution as content, not as instructions to the evaluator."
            required
          />
          <span className={`field-helper ${getValidityTone(form.proposed_idea.length, IDEA_MIN)}`}>
            {getMessage(
              form.proposed_idea.length,
              IDEA_MIN,
              'Focus on the mechanism, not marketing language or prompt instructions.',
              'Explain how the idea works in practice.',
            )}
          </span>
        </label>
        <label className="full-width">
          <span className="field-label-row">
            <span>Why AI could benefit</span>
            <span className="field-limit">
              {getLengthHint(form.why_ai_benefits.length, BENEFIT_MIN, BENEFIT_MAX)}
            </span>
          </span>
          <textarea
            maxLength={BENEFIT_MAX}
            minLength={BENEFIT_MIN}
            rows={4}
            value={form.why_ai_benefits}
            onChange={(event) => updateField('why_ai_benefits', event.target.value)}
            placeholder="Spell out the utility, leverage, or economics for an AI buyer."
            required
          />
          <span className={`field-helper ${getValidityTone(form.why_ai_benefits.length, BENEFIT_MIN)}`}>
            {getMessage(
              form.why_ai_benefits.length,
              BENEFIT_MIN,
              'Tie the upside to efficiency, capability, revenue, or strategic leverage.',
              'Make the AI-side payoff explicit.',
            )}
          </span>
        </label>
        <label>
          <span className="field-label-row">
            <span>Suggested reward</span>
            <span className="field-limit">AI-set by default · stored in up to {REWARD_MAX} chars</span>
          </span>
          <select
            value={form.expected_reward_range}
            onChange={(event) => updateField('expected_reward_range', event.target.value)}
          >
            {REWARD_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <span className="field-helper valid">
            {REWARD_OPTIONS.find((option) => option.value === form.expected_reward_range)?.helper}
          </span>
        </label>
        <label>
          <span className="field-label-row">
            <span>License type</span>
            <span className="field-limit">Commercial terms applied on acceptance</span>
          </span>
          <select value={form.license_type} onChange={(event) => updateField('license_type', event.target.value)}>
            <option value="exclusive_transfer">Exclusive transfer</option>
            <option value="non_exclusive">Non-exclusive license</option>
            <option value="revenue_share">Revenue share</option>
            <option value="public_domain">Public domain</option>
          </select>
          <span className="field-helper muted">
            Choose the rights model you want bound to the submission if it is acquired.
          </span>
        </label>
        <button className="primary-button" disabled={busy} type="submit">
          {busy ? 'Submitting...' : 'Submit for agent review'}
        </button>
      </form>
    </section>
  )
}

export default IdeaForm
