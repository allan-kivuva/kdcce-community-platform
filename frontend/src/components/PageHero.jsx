import React from 'react'
export default function PageHero({ title, eyebrow = 'KDCCE', text, image = '/images/hero.jpg' }) {
  return <section className="relative overflow-hidden bg-kGreen">
    <img src={image} alt="" className="absolute inset-0 h-full w-full object-cover object-center opacity-55" />
    <div className="absolute inset-0 bg-kGreen/55" />
    <div className="container-k relative py-20 text-white md:py-28">
      <div className="max-w-2xl"><div className="mb-3 text-sm font-semibold italic text-kLime">{eyebrow}</div><h1 className="font-display text-4xl font-bold leading-tight md:text-6xl">{title}</h1>{text && <p className="mt-5 max-w-xl text-base leading-7 text-white/80 md:text-lg">{text}</p>}</div>
    </div>
  </section>
}
