import { Routes, Route } from 'react-router-dom'
import { useToast } from '../components/admin/adminHelpers'
import Toast from '../components/admin/Toast'
import FamilyOverview from './family/FamilyOverview'
import FamilyVisits from './family/FamilyVisits'
import FamilyPrograms from './family/FamilyPrograms'
import FamilyMessages from './family/FamilyMessages'
import FamilyNotifications from './family/FamilyNotifications'
import FamilyProfile from './family/FamilyProfile'

// Distinct from both AdminDashboard and VolunteerPortal — no approval
// gate like VolunteerPortal's (a family account only ever exists after
// an admin creates it and links + approves a FamilyMemberAccess row;
// there's no "pending self-registration" state to show here), and no
// admin-navigation surface at all (see FamilyShell).
export default function FamilyPortal() {
  const [toast, showToast] = useToast()

  return <>
    <Routes>
      <Route index element={<FamilyOverview />} />
      <Route path="visits" element={<FamilyVisits />} />
      <Route path="programs" element={<FamilyPrograms />} />
      <Route path="messages" element={<FamilyMessages showToast={showToast} />} />
      <Route path="notifications" element={<FamilyNotifications />} />
      <Route path="profile" element={<FamilyProfile showToast={showToast} />} />
    </Routes>
    <Toast message={toast} />
  </>
}
