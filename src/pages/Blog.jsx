import React from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import PageHero from '../components/PageHero'
import { posts } from '../data/siteData'

export default function Blog(){ return <><PageHero title="News & stories" eyebrow="Blog" text="Stories that show the people, ideas and small wins behind the work."/><section className="container-k py-20"><div className="grid gap-6 md:grid-cols-2">{posts.map(post=><article key={post.id} className="overflow-hidden rounded-2xl border border-slate-100 bg-white shadow-soft"><img src={post.image} alt="" className="h-64 w-full object-cover"/><div className="p-6"><div className="text-xs font-semibold uppercase tracking-widest text-kOrange">{post.date}</div><h2 className="mt-2 font-display text-2xl font-bold text-kGreen">{post.title}</h2><p className="mt-3 leading-7 text-kMuted">{post.excerpt}</p><Link to={`/blog/${post.id}`} className="mt-5 inline-flex items-center gap-2 font-semibold text-kOrange">Read story <ArrowRight size={16}/></Link></div></article>)}</div></section></> }
