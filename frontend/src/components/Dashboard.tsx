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

function Dashboard({ ideas, summary }: DashboardProps) {
  return (
    <section className="panel">
      <div className="section-heading">
        <h2>Creator dashboard</h2>
        <p>Track submission outcomes, rewards, and evaluation rationale.</p>
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
          <span>Paid</span>
          <strong>{summary?.paid_count ?? 0}</strong>
        </article>
        <article>
          <span>Net rewards</span>
          <strong>{formatMoney(summary?.total_net_rewards ?? 0)}</strong>
        </article>
      </div>
      <div className="idea-list">
        {ideas.length === 0 ? <p className="empty-state">No ideas yet. Submit the first spark.</p> : null}
        {ideas.map((idea) => (
          <article className="idea-card" key={idea.id}>
            <div className="idea-card-header">
              <div>
                <h3>{idea.title}</h3>
                <p>{idea.category.replace('_', ' ')}</p>
              </div>
              <span className={`status-badge status-${idea.status}`}>{idea.status}</span>
            </div>
            <p>{idea.feedback ?? 'Awaiting evaluator feedback.'}</p>
            <div className="idea-meta-grid">
              <span>Score: {idea.score_total ?? '—'}</span>
              <span>License: {idea.license_type}</span>
              <span>Duplicate risk: {idea.similarity_score ?? 0}</span>
              <span>
                Reward: {idea.payout ? formatMoney(idea.payout.net_amount) : 'Not paid'}
              </span>
            </div>
          </article>
        ))}
      </div>
    </section>
  )
}

export default Dashboard
