import React from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import PageHero from '../components/PageHero'
import { useApiList } from '../lib/useApiList'

function formatDate(iso) {
  return new Date(iso).toLocaleDateString('en-KE', { dateStyle: 'medium' })
}

export default function Blog(){
  const { items: posts, loading, error } = useApiList('/api/blog', 'posts')
  return <><PageHero title="News & stories" eyebrow="Blog" text="Stories that show the people, ideas and small wins behind the work."/><section className="container-k py-20">
    {loading && <p className="text-kMuted">Loading stories…</p>}
    {error && <p className="text-kOrange">{error}</p>}
    {!loading && !error && posts.length === 0 && <p className="text-kMuted">No stories published yet — check back soon.</p>}
    <div className="grid gap-6 md:grid-cols-2">{posts.map(post=><article key={post.id} className="overflow-hidden card-k">{post.image && <img src={post.image} alt="" className="h-64 w-full object-cover"/>}<div className="p-6"><div className="text-xs font-semibold uppercase tracking-widest text-kOrange">{formatDate(post.created_at)}</div><h2 className="mt-2 font-display text-2xl font-bold text-kGreen">{post.title}</h2><p className="mt-3 leading-7 text-kMuted">{post.excerpt}</p><Link to={`/blog/${post.id}`} className="mt-5 inline-flex items-center gap-2 font-semibold text-kOrange">Read story <ArrowRight size={16}/></Link></div></article>)}</div>
  </section></> }
