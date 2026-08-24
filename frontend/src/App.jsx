import { Routes, Route, useLocation } from 'react-router-dom'
import { useEffect } from 'react'
import Header from './components/Header'
import Footer from './components/Footer'
import Home from './pages/Home'
import About from './pages/About'
import Programs from './pages/Programs'
import ProgramDetail from './pages/ProgramDetail'
import Gallery from './pages/Gallery'
import Blog from './pages/Blog'
import BlogPost from './pages/BlogPost'
import Sponsor from './pages/Sponsor'
import Donate from './pages/Donate'
import Contact from './pages/Contact'
import Crafts from './pages/Crafts'
import BecomeAVolunteer from './pages/BecomeAVolunteer'
import AdminLogin from './pages/AdminLogin'
import AdminDashboard from './pages/AdminDashboard'
import VolunteerPortal from './pages/VolunteerPortal'

function ScrollToTop() {
  const { pathname, hash } = useLocation()
  useEffect(() => { if (!hash) window.scrollTo(0, 0) }, [pathname, hash])
  return null
}

export default function App() {
  const { pathname } = useLocation()
  const isAdminArea = pathname.startsWith('/admin') || pathname.startsWith('/volunteer')

  return <>
    <ScrollToTop />
    {!isAdminArea && <div className="print:hidden"><Header /></div>}
    <main>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/about" element={<About />} />
        <Route path="/programs" element={<Programs />} />
        <Route path="/programs/:id" element={<ProgramDetail />} />
        <Route path="/gallery" element={<Gallery />} />
        <Route path="/blog" element={<Blog />} />
        <Route path="/blog/:id" element={<BlogPost />} />
        <Route path="/sponsor" element={<Sponsor />} />
        <Route path="/donate" element={<Donate />} />
        <Route path="/contact" element={<Contact />} />
        <Route path="/crafts" element={<Crafts />} />
        <Route path="/become-a-volunteer" element={<BecomeAVolunteer />} />
        <Route path="/admin/login" element={<AdminLogin />} />
        <Route path="/admin/*" element={<AdminDashboard />} />
        <Route path="/volunteer/*" element={<VolunteerPortal />} />
      </Routes>
    </main>
    {!isAdminArea && <div className="print:hidden"><Footer /></div>}
  </>
}
