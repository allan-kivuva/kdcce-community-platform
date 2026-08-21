export const programs = [
  { title: 'Feeding Program', icon: '🍲', image: '/images/hero.jpg', description: 'Warm, nourishing meals that help older persons stay healthy and connected.', tag: 'Nutrition' },
  { title: 'Healthcare Support', icon: '✚', image: '/images/program-health.jpg', description: 'Basic wellness checks, referrals and health education delivered with dignity.', tag: 'Healthcare' },
  { title: 'Social Support', icon: '◉', image: '/images/community.jpg', description: 'Companionship, home visits and group activities that reduce isolation.', tag: 'Community' },
  { title: 'Adult Literacy', icon: '▣', image: '/images/program-literacy.jpg', description: 'Practical reading, writing and numeracy sessions for everyday confidence.', tag: 'Education' },
  { title: 'Physical Activities', icon: '↗', image: '/images/social.jpg', description: 'Gentle movement sessions that encourage strength, balance and joy.', tag: 'Wellness' },
  { title: 'Home Visits', icon: '⌂', image: '/images/contact.jpg', description: 'Friendly visits for elders who cannot regularly reach the center.', tag: 'Care' },
  { title: 'Advocacy', icon: '⚑', image: '/images/program-elderly.jpg', description: 'Championing respect, access and inclusion for older persons in the community.', tag: 'Rights' },
  { title: 'Skills Training', icon: '✿', image: '/images/crafts.jpg', description: 'Creative skills such as beadwork and knitting that can generate extra income.', tag: 'Livelihoods' }
]

export const gallery = [
  '/images/hero.jpg',
  '/images/community.jpg',
  '/images/program-health.jpg',
  '/images/program-elderly.jpg',
  '/images/social.jpg',
  '/images/crafts.jpg',
  '/images/contact.jpg',
  '/images/program-literacy.jpg'
]

export const posts = [
  { id: 1, title: 'A morning at the center', date: 'Aug 14, 2026', image: gallery[0], excerpt: 'From breakfast to conversation circles, small routines can create a strong sense of belonging.' },
  { id: 2, title: 'Why companionship matters', date: 'Aug 03, 2026', image: gallery[1], excerpt: 'A little time, a listening ear and a familiar face can make a big difference.' },
  { id: 3, title: 'Growing skills through crafts', date: 'Jul 22, 2026', image: gallery[3], excerpt: 'Our creative workshops are helping elders explore new skills and celebrate what they can make.' },
  { id: 4, title: 'A week of movement and smiles', date: 'Jul 10, 2026', image: gallery[2], excerpt: 'Gentle exercise, music and shared laughter have become a favorite part of the week.' }
]

export const crafts = [
  { id: 1, title: 'Sunrise Beaded Bracelet', category: 'Beadwork', maker: 'Mary A.', price: 850, status: 'Available', image: '/images/crafts.jpg', description: 'Hand-assembled seed-bead bracelet in warm tones.' },
  { id: 2, title: 'Kibera Knit Scarf', category: 'Knitting', maker: 'Agnes N.', price: 1800, status: 'Available', image: '/images/crafts.jpg', description: 'Soft hand-knit scarf made for cool mornings.' },
  { id: 3, title: 'Colour Circle Necklace', category: 'Beadwork', maker: 'Rose W.', price: 1200, status: 'Reserved', image: '/images/crafts.jpg', description: 'Statement necklace featuring bright circular bead patterns.' },
  { id: 4, title: 'Cozy Winter Wrap', category: 'Knitting', maker: 'Jane K.', price: 2200, status: 'Sold', image: '/images/program-elderly.jpg', description: 'Textured wrap with a simple, timeless finish.' }
]

export const team = [
  { name: 'Grace Wanjiku', role: 'Program Coordinator', image: '/images/program-health.jpg' },
  { name: 'Peter Otieno', role: 'Community Outreach', image: '/images/community.jpg' },
  { name: 'Lucy Njeri', role: 'Volunteer Lead', image: '/images/contact.jpg' }
]
