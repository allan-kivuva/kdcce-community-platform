import React from 'react'
import { Link } from 'react-router-dom'
import { Facebook, Instagram, Mail, MapPin, Phone, Twitter } from 'lucide-react'

export default function Footer() {
  return <footer className="mt-20 bg-[#0b1721] text-white">
    <div className="container-k grid gap-12 py-14 md:grid-cols-[1.2fr_.8fr_.9fr_1fr]">
      <div>
        <div className="mb-5 inline-flex rounded-2xl bg-white px-3 py-2">
          <img src="/images/logo.png" alt="KDCCE" className="h-14 w-auto max-w-[190px] object-contain object-left" />
        </div>
        <p className="max-w-sm text-sm leading-7 text-white/65">A course project UI inspired by the mission of supporting older persons through care, connection, dignity and opportunity.</p>
        <div className="mt-5 flex gap-3"><a href="#" className="grid h-9 w-9 place-items-center rounded-full border border-white/15 hover:border-kOrange"><Facebook size={15}/></a><a href="#" className="grid h-9 w-9 place-items-center rounded-full border border-white/15 hover:border-kOrange"><Instagram size={15}/></a><a href="#" className="grid h-9 w-9 place-items-center rounded-full border border-white/15 hover:border-kOrange"><Twitter size={15}/></a></div>
      </div>
      <div><h4 className="mb-5 font-display text-lg">Quick Links</h4><div className="grid gap-3 text-sm text-white/65"><Link to="/about">About Us</Link><Link to="/programs">Programs</Link><Link to="/gallery">Gallery</Link><Link to="/blog">Blog & News</Link><Link to="/crafts">Craft Showcase</Link></div></div>
      <div><h4 className="mb-5 font-display text-lg">Get Involved</h4><div className="grid gap-3 text-sm text-white/65"><Link to="/donate">Donate</Link><Link to="/sponsor">Sponsor an Elder</Link><Link to="/contact">Volunteer</Link><Link to="/contact">Partner With Us</Link><Link to="/contact">Send a Message</Link></div></div>
      <div><h4 className="mb-5 font-display text-lg">Contact Us</h4><div className="grid gap-4 text-sm text-white/65"><div className="flex gap-3"><Phone size={16} className="mt-1 text-kOrange"/><span>+254 724 380 025</span></div><div className="flex gap-3"><Mail size={16} className="mt-1 text-kOrange"/><span>info@kdcce.org</span></div><div className="flex gap-3"><MapPin size={16} className="mt-1 text-kOrange"/><span>Kibera, Nairobi, Kenya</span></div></div></div>
    </div>
    <div className="border-t border-white/10 py-5 text-center text-xs text-white/40">© 2026 KDCCE Course Project. Not affiliated with or endorsed by the real organization.</div>
  </footer>
}
