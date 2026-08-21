import { useState } from 'react'
import { X } from 'lucide-react'
import PageHero from '../components/PageHero'
import { gallery } from '../data/siteData'

export default function Gallery(){ const [selected,setSelected]=useState(null); return <><PageHero title="Moments from the community" eyebrow="Gallery" text="A visual preview of meals, conversations, learning and shared moments."/><section className="container-k py-20"><div className="grid grid-cols-2 gap-4 md:grid-cols-4">{gallery.concat(gallery.slice(0,4)).map((src,i)=><button key={`${src}-${i}`} onClick={()=>setSelected(src)} className="group overflow-hidden rounded-2xl text-left"><img src={src} alt="Community moment" className="h-56 w-full object-cover transition duration-500 group-hover:scale-105"/></button>)}</div></section>{selected&&<div className="fixed inset-0 z-[60] grid place-items-center bg-black/90 p-5" onClick={()=>setSelected(null)}><button className="absolute right-5 top-5 grid h-12 w-12 place-items-center rounded-full bg-white/10 text-white" onClick={()=>setSelected(null)}><X/></button><img src={selected} alt="Gallery item" className="max-h-[85vh] max-w-5xl rounded-2xl object-contain"/></div>}</> }
