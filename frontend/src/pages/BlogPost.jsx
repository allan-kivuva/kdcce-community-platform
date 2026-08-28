import React from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import PageHero from '../components/PageHero'
import { useApiList } from '../lib/useApiList'

export default function BlogPost(){
  const {id}=useParams()
  const { items: posts, loading, error } = useApiList('/api/blog', 'posts')
  if (loading) return <div className="container-k py-20"><p className="text-kMuted">Loading story…</p></div>
  if (error) return <div className="container-k py-20"><p className="text-kOrange">{error}</p></div>
  const post = posts.find(p=>String(p.id)===id)
  if (!post) return <div className="container-k py-20"><p className="text-kMuted">This story isn't available.</p><Link to="/blog" className="mt-4 inline-flex items-center gap-2 font-semibold text-kOrange"><ArrowLeft size={16}/> Back to stories</Link></div>
  return <><PageHero title={post.title} eyebrow={new Date(post.created_at).toLocaleDateString('en-KE', { dateStyle: 'medium' })} text={post.excerpt} image={post.image}/><article className="container-k max-w-3xl py-20">{post.image && <img src={post.image} alt="" className="h-[420px] w-full rounded-2xl object-cover"/>}<div className="prose prose-slate mt-10 max-w-none"><p>Today at the center, the focus is not on a single big moment but on the small experiences that build confidence over time. A shared meal becomes a conversation; a learning session becomes a new skill; a home visit becomes a reason to look forward to the next day.</p><p>These stories remind us that support works best when it is practical, consistent and rooted in community. The site UI is designed to make those stories easy to discover and to connect each story with a clear way to help.</p><h2>What we are learning</h2><p>Good community programs are built around people rather than processes. That means listening first, communicating clearly and giving supporters simple ways to participate.</p></div><Link to="/blog" className="mt-10 inline-flex items-center gap-2 font-semibold text-kOrange"><ArrowLeft size={16}/> Back to stories</Link></article></> }
