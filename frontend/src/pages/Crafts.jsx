import { useState } from 'react'
import { ArrowRight, MessageCircle } from 'lucide-react'
import PageHero from '../components/PageHero'
import { useApiList } from '../lib/useApiList'

export default function Crafts(){
  const [filter,setFilter]=useState('All')
  const { items: crafts, loading, error } = useApiList('/api/crafts', 'crafts')
  const shown=filter==='All'?crafts:crafts.filter(x=>x.category===filter)
  return <><PageHero title="Made with skill and purpose" eyebrow="Craft Showcase" text="A public catalog concept for beadwork and knitting created through skills training." image="/images/crafts.jpg"/><section className="container-k py-20"><div className="flex flex-wrap items-center justify-between gap-4"><div><div className="eyebrow">Elder-made crafts</div><h2 className="mt-2 font-display text-4xl font-bold text-kGreen">Support the maker behind the craft.</h2></div><div className="flex rounded-xl border border-kBorder p-1">{['All','Beadwork','Knitting'].map(x=><button key={x} onClick={()=>setFilter(x)} className={`rounded-lg px-4 py-2 text-sm font-semibold ${filter===x?'bg-kGreen text-white':'text-kMuted'}`}>{x}</button>)}</div></div>
    {loading && <p className="mt-8 text-kMuted">Loading crafts…</p>}
    {error && <p className="mt-8 text-kOrange">{error}</p>}
    {!loading && !error && shown.length === 0 && <p className="mt-8 text-kMuted">No crafts to show yet — check back soon.</p>}
    <div className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">{shown.map(item=><article key={item.id} className="overflow-hidden card-k"><div className="relative">{item.image && <img src={item.image} alt={item.title} className="h-64 w-full object-cover"/>}<span className={`absolute left-4 top-4 rounded-full px-3 py-1 text-xs font-bold ${item.status==='Available'?'bg-green-100 text-green-700':item.status==='Reserved'?'bg-amber-100 text-amber-700':'bg-slate-200 text-slate-600'}`}>{item.status}</span></div><div className="p-5"><div className="text-xs font-semibold uppercase tracking-wider text-kOrange">{item.category}</div><h3 className="mt-1 font-display text-lg font-bold text-kGreen">{item.title}</h3><p className="mt-2 text-sm leading-6 text-kMuted">{item.description}</p><div className="mt-3 flex items-center justify-between text-sm"><span className="text-kMuted">Maker: <b className="text-kInk">{item.maker}</b></span><b className="text-kGreen">KES {item.price.toLocaleString()}</b></div><button className="btn-orange mt-4 w-full" disabled={item.status==='Sold'}><MessageCircle size={16}/> Inquire <ArrowRight size={14}/></button></div></article>)}</div></section></> }
