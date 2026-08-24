import React from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, Heart } from 'lucide-react'
import PageHero from '../components/PageHero'
import { programs } from '../data/siteData'

export default function ProgramDetail() {
  const { id } = useParams()
  const program = programs.find(p => p.id === id) || programs[0]
  return <>
    <PageHero title={program.title} eyebrow={program.tag} text={program.description} image={program.image} />
    <article className="container-k max-w-3xl py-20">
      <img src={program.image} alt={program.title} className="h-[420px] w-full rounded-2xl object-cover" />
      <div className="prose prose-slate mt-10 max-w-none">
        <p>{program.description}</p>
        <p>This program is one of the ways KDCCE supports older persons in the community — through consistent, dignified care that responds to everyday needs rather than one-off interventions. Staff and volunteers work directly with elders to make sure support is practical and personal.</p>
        <h2>How you can help</h2>
        <p>Donations to this program go toward staff time, materials and the day-to-day running of activities. Every contribution, big or small, helps the centre keep showing up for the people who rely on it.</p>
      </div>
      <div className="mt-10 flex flex-wrap items-center gap-4">
        <Link to="/programs" className="inline-flex items-center gap-2 font-semibold text-kOrange"><ArrowLeft size={16} /> Back to programs</Link>
        <Link to={`/donate?campaign=${encodeURIComponent(program.title)}`} className="btn-orange"><Heart size={16} /> Support this program</Link>
      </div>
    </article>
  </>
}
