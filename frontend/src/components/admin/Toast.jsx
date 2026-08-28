import { Check } from 'lucide-react'

export default function Toast({ message }) {
  if (!message) return null
  return <div className="fixed bottom-6 right-6 z-50 flex items-center gap-2 rounded-xl bg-kGreen px-5 py-3 text-sm font-semibold text-white shadow-soft">
    <Check size={16} className="text-kLime" /> {message}
  </div>
}
