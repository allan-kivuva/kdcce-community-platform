import React from 'react'
import { ArrowRight, Heart, Users, HandHeart } from 'lucide-react'
import { Link } from 'react-router-dom'
import { programs } from '../data/siteData'
import ProgramCard from '../components/ProgramCard'
import Stats from '../components/Stats'
import GalleryPreview from '../components/GalleryPreview'
import VideoShowcase from '../components/VideoShowcase'
import CtaBanner from '../components/CtaBanner'
import { useApiList } from '../lib/useApiList'

export default function Home() {
  const { items: team, loading: teamLoading, error: teamError } = useApiList('/api/team', 'team')
  return <div>
    <section className="relative min-h-[690px] overflow-hidden bg-black">
      <img src="/images/hero.jpg" alt="Older adults smiling together" className="absolute inset-0 h-full w-full object-cover object-center" />
      <div className="hero-overlay absolute inset-0" />
      <div className="container-k relative flex min-h-[690px] items-center py-20 text-white">
        <div className="max-w-[620px] pt-10"><div className="mb-5 font-display text-sm font-semibold italic text-kLime">Community. Care. Dignity.</div><h1 className="font-display text-5xl font-bold leading-[1.02] md:text-7xl">Restoring dignity to older persons in Kibera.</h1><p className="mt-6 max-w-xl text-base leading-7 text-white/75 md:text-lg">We build practical support, companionship and pathways to opportunity so elders can live healthier, more connected lives.</p><div className="mt-8 flex flex-col gap-3 sm:flex-row"><Link className="btn-orange" to="/donate"><Heart size={17}/> Donate Now</Link><Link className="btn-outline" to="/become-a-volunteer"><Users size={17}/> Become a Volunteer</Link></div><div className="mt-10 grid max-w-md grid-cols-3 gap-6 border-t border-white/15 pt-5 text-xs text-white/60"><div><b className="block text-xl text-white">35+</b>Associations connected</div><div><b className="block text-xl text-white">8K+</b>Elders supported</div><div><b className="block text-xl text-white">6</b>Core programs</div></div></div>
      </div>
    </section>

    <VideoShowcase />

    <section className="container-k grid gap-4 md:grid-cols-3">
      {programs.slice(0,3).map(p => <ProgramCard key={p.title} program={p} />)}
    </section>
    <Stats />

    <section className="container-k grid gap-10 py-24 md:grid-cols-2 md:items-center">
      <div className="relative min-h-[520px]">
        <div className="absolute left-0 top-8 h-[330px] w-[68%] overflow-hidden rounded-2xl"><img className="h-full w-full object-cover" src="/images/community.jpg" alt="Older people gathered in the community" /></div>
        <div className="absolute bottom-4 right-0 h-[280px] w-[54%] overflow-hidden rounded-2xl border-8 border-white shadow-soft"><img className="h-full w-full object-cover" src="/images/mary.jpg" alt="Older community member" /></div>
        <div className="absolute left-0 bottom-0 grid h-28 w-28 grid-cols-5 gap-2 opacity-75">{Array.from({length: 25}).map((_, i)=><span key={i} className="h-1 w-1 rounded-full bg-kOrange" />)}</div>
      </div>
      <div><div className="eyebrow">About KDCCE</div><h2 className="mt-3 font-display text-4xl font-bold leading-tight text-kGreen">Helping older persons live with dignity.</h2><p className="mt-5 text-base leading-7 text-kMuted">This course-project design reimagines a community-centered website for an organization serving older persons in Kibera. It combines warm storytelling with clear pathways for donations, volunteering and practical support.</p><div className="mt-8 grid gap-5 sm:grid-cols-2"><div><div className="mb-2 flex items-center gap-2 font-semibold text-kGreen"><HandHeart size={19} className="text-kOrange"/> Our Mission</div><p className="text-sm leading-6 text-kMuted">Provide care, connection and advocacy through food, wellness, learning and community activities.</p></div><div><div className="mb-2 flex items-center gap-2 font-semibold text-kGreen"><Heart size={19} className="text-kOrange"/> Our Vision</div><p className="text-sm leading-6 text-kMuted">A society where older persons are respected, included and able to access essential services.</p></div></div><Link to="/about" className="btn-orange mt-8">Learn More About Us <ArrowRight size={16}/></Link></div>
    </section>

    <section className="bg-kCream py-20"><div className="container-k"><div className="mb-10 flex items-end justify-between"><div><div className="eyebrow">What we do</div><h2 className="mt-2 font-display text-4xl font-bold text-kGreen">Our programs</h2></div><Link to="/programs" className="hidden items-center gap-2 font-semibold text-kOrange sm:flex">See all programs <ArrowRight size={16}/></Link></div><div className="grid gap-5 md:grid-cols-3">{programs.slice(3,6).map(p=><ProgramCard key={p.title} program={p} />)}</div></div></section>

    <section className="container-k py-20"><div className="grid gap-8 rounded-2xl bg-kTint p-6 md:grid-cols-[.9fr_1.1fr] md:p-10"><img className="h-[320px] w-full rounded-2xl object-cover" src="/images/social.jpg" alt="Older people sharing community time"/><div className="flex flex-col justify-center"><div className="section-kicker">Mary's Story</div><div className="mt-3 text-5xl leading-none text-kOrange">“</div><p className="mt-1 max-w-xl font-display text-2xl font-semibold leading-9 text-kGreen">Before joining the center, many days felt quiet. Now I have people to talk to, new things to learn and reasons to keep showing up.</p><div className="mt-5 text-sm font-bold text-kInk">Mary Akinyi, 72</div><div className="mt-4 flex gap-1">{Array.from({length:5}).map((_,i)=><span key={i} className="h-2 w-2 rounded-full bg-kOrange" />)}</div></div></div></section>

    <GalleryPreview />
    {!teamLoading && !teamError && team.length > 0 && <section className="container-k pb-16"><div className="mb-8 text-center"><div className="eyebrow">The people behind the work</div><h2 className="mt-2 font-display text-3xl font-bold text-kGreen">Meet our team</h2></div><div className="grid gap-5 sm:grid-cols-3 lg:grid-cols-5">{team.map(member=><div key={member.id} className="overflow-hidden card-k text-center"><img src={member.image} alt={member.name} className="h-60 w-full object-cover"/><div className="p-5"><h3 className="font-display text-lg font-semibold text-kGreen">{member.name}</h3><p className="mt-1 text-sm text-kMuted">{member.role}</p></div></div>)}</div></section>}
    <CtaBanner />
  </div>
}
