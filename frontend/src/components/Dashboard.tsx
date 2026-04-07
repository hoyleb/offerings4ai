import type { DashboardSummary, Idea } from '../types'

interface DashboardProps {
  ideas: Idea[]
  summary: DashboardSummary | null
}

function formatMoney(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 2,
  }).format(value)
}

function formatStatusLabel(status: Idea['status']): string {
  switch (status) {
    case 'queued':
      return 'queued for review'
    case 'under_review':
      return 'in review'
    default:
      return status.replace('_', ' ')
  }
}

function Dashboard({ ideas, summary }: DashboardProps) {
  return (
    <section className="panel">
      <div className="section-heading">
        <h2>Creator dashboard</h2>
        <p>
          Track publication, review progress, and any downstream payouts. Ideas stay public as
          signals; this platform does not decide they are worthless.
        </p>
      </div>
      <div className="metrics-grid">
        <article>
          <span>Submissions</span>
          <strong>{summary?.total_submissions ?? 0}</strong>
        </article>
        <article>
          <span>Accepted</span>
          <strong>{summary?.accepted_count ?? 0}</strong>
        </article>
        <article>
          <span>Reviewed</span>
          <strong>{summary?.reviewed_count ?? 0}</strong>
        </article>
        <article>
          <span>Paid</span>
          <strong>{summary?.paid_count ?? 0}</strong>
        </article>
        <article>
          <span>Total rewards</span>
          <strong>{formatMoney(summary?.total_net_rewards ?? 0)}</strong>
        </article>
        <article>
          <span>Average score</span>
          <strong>{summary?.average_score?.toFixed(1) ?? '0.0'}</strong>
        </article>
      </div>
      <div className="idea-list">
        {ideas.length === 0 ? <p className="empty-state">No ideas yet. Publish the first signal.</p> : null}
        {ideas.map((idea) => (
          <article className="idea-card" key={idea.id}>
            <div className="idea-card-header">
              <div>
                <h3>{idea.title}</h3>
                <p>{idea.category.replace('_', ' ')}</p>
              </div>
              <span className={`status-badge status-${idea.status}`}>
                {formatStatusLabel(idea.status)}
              </span>
            </div>
            <p>{idea.feedback ?? 'Awaiting evaluator feedback.'}</p>
            <div className="idea-meta-grid">
              <span>Score: {idea.score_total ?? '—'}</span>
              <span>Reuse: {idea.license_type}</span>
              <span>Duplicate risk: {idea.similarity_score ?? 0}</span>
              <span>
                Payout: {idea.payout ? formatMoney(idea.payout.net_amount) : 'None observed'}
              </span>
            </div>
          </article>
        ))}
      </div>
    </section>
  )
}

export default Dashboard
