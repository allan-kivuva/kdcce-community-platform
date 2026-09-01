import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Heart } from 'lucide-react'
import PageHero from '../components/PageHero'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000'

function fmtMoney(n) { return `KES ${Number(n || 0).toLocaleString()}` }

function CampaignCard({ campaign }) {
  const progress = campaign.progress || {}
  const pct = Math.min(progress.percent_achieved ?? 0, 100)
  return <div className="card-k p-6">
    <div className="flex items-center justify-between gap-2">
      <h3 className="font-display text-xl font-bold text-kGreen">{campaign.name}</h3>
      {campaign.program_name && <span className="shrink-0 rounded-full bg-kTint px-3 py-1 text-xs font-bold text-kOrange">{campaign.program_name}</span>}
    </div>
    {campaign.description && <p className="mt-3 text-sm leading-6 text-kMuted">{campaign.description}</p>}
    <div className="mt-5">
      <div className="flex items-baseline justify-between text-sm"><span className="font-bold text-kGreen">{fmtMoney(progress.raised_amount)}</span><span className="text-xs text-kMuted">of {fmtMoney(campaign.goal_amount)} goal</span></div>
      <div className="mt-2 h-2.5 w-full overflow-hidden rounded-full bg-kBorderSoft"><div className="h-full rounded-full bg-kGreen" style={{ width: `${pct}%` }} /></div>
      <div className="mt-1.5 text-xs text-kMuted">{pct}% complete{progress.donation_count != null ? ` · ${progress.donation_count} donation${progress.donation_count === 1 ? '' : 's'}` : ''}</div>
    </div>
    <Link to={`/donate?campaign=${encodeURIComponent(campaign.name)}`} className="btn-orange mt-5 w-fit"><Heart size={16} /> Support this campaign</Link>
  </div>
}

export default function Campaigns() {
  const [campaigns, setCampaigns] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${API_URL}/api/campaigns`)
      .then(res => res.json())
      .then(data => setCampaigns(data.campaigns || []))
      .catch(() => setCampaigns([]))
      .finally(() => setLoading(false))
  }, [])

  return <>
    <PageHero title="Active campaigns" eyebrow="Give with purpose" text="Every campaign below funds a specific, real need — see exactly how close we are to reaching each goal." image="/images/programs.jpg" />
    <section className="container-k py-20">
      {loading && <p className="text-center text-kMuted">Loading campaigns…</p>}
      {!loading && campaigns.length === 0 && <p className="text-center text-kMuted">No active campaigns right now — check back soon, or make a general donation below.</p>}
      {!loading && campaigns.length > 0 && <div className="grid gap-6 md:grid-cols-2">{campaigns.map(c => <CampaignCard key={c.id} campaign={c} />)}</div>}
      <div className="mt-12 text-center"><Link to="/donate" className="btn-green">Make a general donation</Link></div>
    </section>
  </>
}
