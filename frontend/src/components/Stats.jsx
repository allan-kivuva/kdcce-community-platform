import React from 'react'
import { HandHeart, Heart, Users, Utensils } from 'lucide-react'

export default function Stats() {
  const stats = [
    [<Users size={24}/>, '35+', 'Older Persons Associations'],
    [<Utensils size={24}/>, '68+', 'Meals Served Daily'],
    [<Users size={24}/>, '8K+', 'Elders Supported Weekly'],
    [<Heart size={24}/>, '93+', 'Beneficiaries Reached']
  ]
  return <section id="impact" className="container-k -mt-2 card-k">
    <div className="grid grid-cols-2 md:grid-cols-4">{stats.map(([icon, number, label], i) => <div key={label} className={`flex items-center gap-3 px-5 py-7 md:px-8 ${i < stats.length - 1 ? 'border-r border-kBorderSoft' : ''}`}><div className="text-kOrange">{icon}</div><div><div className="font-display text-2xl font-bold text-kGreen">{number}</div><div className="mt-1 max-w-[125px] text-xs font-semibold leading-5 text-kMuted">{label}</div></div></div>)}</div>
  </section>
}
