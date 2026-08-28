import { useRef, useState } from 'react'
import { Play } from 'lucide-react'

export default function VideoShowcase() {
  const videoRef = useRef(null)
  const [started, setStarted] = useState(false)

  function handlePlay() {
    setStarted(true)
    videoRef.current?.play()
  }

  return <section className="container-k py-20">
    <div className="mx-auto max-w-2xl text-center">
      <div className="eyebrow">See it for yourself</div>
      <h2 className="mt-3 font-display text-4xl font-bold text-kGreen">KDCCE in Action</h2>
      <p className="mt-5 text-base leading-7 text-kMuted">Beyond the mission statement — this is what community, care and dignity look like day to day at the center. A short look at the people and programs behind KDCCE.</p>
    </div>

    <div className="relative mx-auto mt-10 aspect-video w-full max-w-5xl overflow-hidden rounded-2xl bg-black shadow-soft">
      <video
        ref={videoRef}
        className="h-full w-full object-cover"
        src="/videos/kdcce-intro.mp4"
        poster="/images/community-gratitude.jpg"
        controls={started}
        preload="metadata"
        playsInline
        onEnded={() => { if (videoRef.current) videoRef.current.currentTime = 0 }}
      />
      {!started && <button
        type="button"
        onClick={handlePlay}
        aria-label="Play KDCCE introduction video"
        className="group absolute inset-0 flex items-center justify-center bg-black/25 transition hover:bg-black/35"
      >
        <span className="grid h-16 w-16 place-items-center rounded-full bg-white/95 text-kOrange shadow-soft transition group-hover:scale-105 sm:h-20 sm:w-20">
          <Play size={28} className="ml-1" fill="currentColor" />
        </span>
      </button>}
    </div>
  </section>
}
