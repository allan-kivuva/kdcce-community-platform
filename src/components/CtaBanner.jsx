import React from 'react'
import { Heart, Users } from 'lucide-react'
import { Link } from 'react-router-dom'

export default function CtaBanner() {
  return <section className="container-k mt-4 overflow-hidden rounded-2xl bg-kGreen px-6 py-8 text-white md:px-10 md:py-10">
    <div className="flex flex-col gap-7 md:flex-row md:items-center md:justify-between"><div className="flex gap-4"><div className="grid h-14 w-14 shrink-0 place-items-center rounded-2xl bg-kOrange"><Heart /></div><div><h3 className="font-display text-2xl font-bold">Your support can change an elder's life.</h3><p className="mt-2 max-w-xl text-sm leading-6 text-white/70">Every contribution helps create access to food, care, education and community for older persons.</p></div></div><div className="flex flex-col gap-3 sm:flex-row"><Link to="/donate" className="btn-orange"><Heart size={16}/> Donate Now</Link><Link to="/contact" className="btn-outline"><Users size={16}/> Become a Partner</Link></div></div>
  </section>
}
