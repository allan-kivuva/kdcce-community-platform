import { useState } from 'react'
import { X } from 'lucide-react'
import PageHero from '../components/PageHero'
import { useApiList } from '../lib/useApiList'

export default function Gallery(){
  const [selected,setSelected]=useState(null)
  const { items: images, loading, error } = useApiList('/api/gallery', 'images')
  return <><PageHero title="Moments from the community" eyebrow="Gallery" text="A visual preview of meals, conversations, learning and shared moments." image="/images/community-market.jpg"/><section className="container-k py-20">
    {loading && <p className="text-kMuted">Loading gallery…</p>}
    {error && <p className="text-kOrange">{error}</p>}
    {!loading && !error && images.length === 0 && <p className="text-kMuted">No photos yet — check back soon.</p>}
    <div className="grid grid-cols-2 gap-4 md:grid-cols-4">{images.map(img=><button key={img.id} onClick={()=>setSelected(img)} className="group overflow-hidden rounded-2xl text-left"><img src={img.url} alt={img.caption || 'Community moment'} className="h-56 w-full object-cover transition duration-500 group-hover:scale-105"/></button>)}</div>
  </section>{selected&&<div className="fixed inset-0 z-[60] grid place-items-center bg-black/90 p-5" onClick={()=>setSelected(null)}><button className="absolute right-5 top-5 grid h-12 w-12 place-items-center rounded-full bg-white/10 text-white" onClick={()=>setSelected(null)}><X/></button><img src={selected.url} alt={selected.caption || 'Gallery item'} className="max-h-[85vh] max-w-5xl rounded-2xl object-contain"/></div>}</> }
