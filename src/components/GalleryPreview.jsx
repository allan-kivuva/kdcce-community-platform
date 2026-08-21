import React from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import { gallery } from '../data/siteData'

export default function GalleryPreview() {
  return <section className="container-k py-20">
    <div className="mb-8 flex items-end justify-between gap-6"><div><div className="eyebrow">Moments of connection</div><h2 className="mt-2 font-display text-3xl font-bold text-kGreen md:text-4xl">Gallery</h2></div><Link to="/gallery" className="hidden items-center gap-2 text-sm font-bold text-kOrange sm:flex">View all <ArrowRight size={16}/></Link></div>
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4 md:gap-4">{gallery.slice(0, 8).map((src, i) => <Link key={src} to="/gallery" className={`group overflow-hidden rounded-2xl ${i === 0 || i === 5 ? 'md:col-span-2 md:row-span-2' : ''}`}><img src={src} alt="Community moment" className="h-full min-h-[170px] w-full object-cover transition duration-500 group-hover:scale-105" /></Link>)}</div>
  </section>
}
