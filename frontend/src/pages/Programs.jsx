import React from 'react'
import PageHero from '../components/PageHero'
import ProgramCard from '../components/ProgramCard'
import { programs } from '../data/siteData'

export default function Programs(){ return <><PageHero title="Programs that put people first" eyebrow="Our work" text="From shared meals to literacy and livelihood skills, each program is designed around everyday needs and dignity." image="/images/programs.jpg"/><section className="container-k py-20"><div className="grid gap-5 md:grid-cols-3">{programs.map(p=><ProgramCard key={p.title} program={p}/>)}</div></section></> }
