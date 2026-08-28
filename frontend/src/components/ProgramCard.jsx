import React from 'react'
import { Link } from 'react-router-dom'
import { ArrowUpRight } from 'lucide-react'

export default function ProgramCard({ program, compact = false }) {
  return <Link to={`/programs/${program.id}`} className={`group relative block overflow-hidden rounded-2xl focus:outline-none focus-visible:ring-2 focus-visible:ring-kOrange focus-visible:ring-offset-2 ${compact ? 'h-[180px]' : 'h-[280px]'}`}>
    <img src={program.image} alt={program.title} className="absolute inset-0 h-full w-full object-cover transition duration-500 group-hover:scale-105" />
    <div className="absolute inset-0 bg-gradient-to-t from-black/85 via-black/35 to-black/5" />
    <div className="relative flex h-full flex-col justify-between p-5 text-white">
      <div className="grid h-10 w-10 place-items-center rounded-full bg-kOrange text-sm font-bold">{program.icon}</div>
      <div><div className="mb-1 text-xs font-semibold uppercase tracking-[.13em] text-kLime">{program.tag}</div><h3 className="font-display text-xl font-semibold">{program.title}</h3><p className="mt-1 text-sm leading-6 text-white/75">{program.description}</p><div className="mt-3 inline-flex items-center gap-2 text-sm font-semibold text-kLime">Read more <ArrowUpRight size={15} className="transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5"/></div></div>
    </div>
  </Link>
}
