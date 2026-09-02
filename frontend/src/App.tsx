import { BrowserRouter, Route, Routes, useParams } from 'react-router-dom'
import Navbar from './components/Navbar'
import Footer from './components/Footer'
import VideoUpload from './components/VideoUpload'
import ProcessingView from './components/ProcessingView'
import ResultsPage from './pages/ResultsPage'

function JobRoute() {
  const { jobId } = useParams()
  if (!jobId) return null
  return <ProcessingView jobId={jobId} />
}

function ResultsRoute() {
  const { jobId } = useParams()
  if (!jobId) return null
  return <ResultsPage jobId={jobId} />
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-svh flex flex-col">
      <Navbar />
      <main className="flex-1 flex flex-col justify-center py-4 md:py-6">{children}</main>
      <Footer />
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Shell>
        <Routes>
          <Route path="/" element={<VideoUpload />} />
          <Route path="/jobs/:jobId" element={<JobRoute />} />
          <Route path="/jobs/:jobId/results" element={<ResultsRoute />} />
        </Routes>
      </Shell>
    </BrowserRouter>
  )
}
