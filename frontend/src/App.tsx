import { Routes, Route } from 'react-router-dom'
import { Sparkles } from 'lucide-react'
import BestPracticesPage from './pages/BestPractices'

function App() {
  return (
    <div className="min-h-screen flex">
      <nav className="w-64 bg-[#1B365D] p-4 flex flex-col">
        <img
          src="https://edge.sitecorecloud.io/perficienti28ad-prft2d8b-prod513c-63c8/media/project/perficient-public/prft-public-site/logos/perficient/logo_perficient_full-color_registered-300.svg?iar=0"
          alt="Perficient"
          className="h-8 w-auto brightness-0 invert mb-8"
        />
        <div className="space-y-2">
          <div className="flex items-center gap-3 px-3 py-2 rounded-lg bg-[#E8F4FD] text-[#1B365D]">
            <Sparkles size={20} />
            <span className="font-medium">DataDLC</span>
          </div>
        </div>
        <div className="mt-auto pt-4 border-t border-white/10">
          <p className="text-xs text-gray-400 text-center">Powered by Perficient AI</p>
        </div>
      </nav>
      <main className="flex-1 p-8 overflow-auto">
        <Routes>
          <Route path="*" element={<BestPracticesPage />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
