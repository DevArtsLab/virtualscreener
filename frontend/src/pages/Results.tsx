import { useEffect, useRef, useState } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { ArrowLeft, RefreshCw } from "lucide-react"
import {
  api,
  type JobResponse,
  type MoleculeResult,
  type ScreeningResults,
} from "../api/client"
import { ProgressTracker } from "../components/ProgressTracker"
import { ResultsTable } from "../components/ResultsTable"
import { MolViewer } from "../components/MolViewer"

const POLL_INTERVAL_MS = 2000

export function ResultsPage() {
  const { jobId } = useParams<{ jobId: string }>()
  const navigate = useNavigate()

  const [job, setJob] = useState<JobResponse | null>(null)
  const [results, setResults] = useState<ScreeningResults | null>(null)
  const [loadingResults, setLoadingResults] = useState(false)
  const [viewerMol, setViewerMol] = useState<MoleculeResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const pollerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (!jobId) return

    async function poll() {
      if (!jobId) return
      try {
        const j = await api.getJobStatus(jobId)
        setJob(j)
        if (j.status === "done") {
          stopPolling()
          fetchResults(jobId, 1)
        } else if (j.status === "error") {
          stopPolling()
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to fetch status")
        stopPolling()
      }
    }

    poll()
    pollerRef.current = setInterval(poll, POLL_INTERVAL_MS)
    return () => stopPolling()
  }, [jobId])

  function stopPolling() {
    if (pollerRef.current) {
      clearInterval(pollerRef.current)
      pollerRef.current = null
    }
  }

  async function fetchResults(id: string, p: number) {
    setLoadingResults(true)
    try {
      const r = await api.getResults(id, p, 50, true, "rank", true)
      setResults(r)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch results")
    } finally {
      setLoadingResults(false)
    }
  }

  function handlePageChange(p: number) {
    if (jobId) fetchResults(jobId, p)
  }

  const isDone = job?.status === "done"
  const isError = job?.status === "error"
  const isRunning = job && !isDone && !isError

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      {/* Top bar */}
      <div className="border-b border-slate-800 bg-slate-900/80 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-6 py-3 flex items-center justify-between">
          <button
            onClick={() => navigate("/")}
            className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-slate-200 transition-colors"
          >
            <ArrowLeft size={15} /> New screening
          </button>
          <div className="text-xs font-mono text-slate-600 truncate max-w-xs">
            {jobId}
          </div>
          {isRunning && (
            <div className="flex items-center gap-1.5 text-xs text-blue-400">
              <RefreshCw size={12} className="animate-spin" />
              Running…
            </div>
          )}
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 py-8 space-y-8">
        {/* Error */}
        {error && (
          <div className="rounded-xl bg-red-950/40 border border-red-800 p-4">
            <p className="text-sm text-red-300">{error}</p>
          </div>
        )}

        {/* Progress tracker */}
        {job && <ProgressTracker job={job} />}

        {/* Results */}
        {isDone && results && !loadingResults && (
          <ResultsTable
            data={results}
            jobId={jobId!}
            onViewPose={setViewerMol}
            onPageChange={handlePageChange}
            exportCsvUrl={api.exportCsvUrl(jobId!)}
          />
        )}

        {loadingResults && (
          <div className="flex items-center justify-center py-16">
            <div className="flex flex-col items-center gap-3">
              <div className="h-8 w-8 rounded-full border-2 border-blue-500 border-t-transparent animate-spin" />
              <p className="text-sm text-slate-400">Loading results…</p>
            </div>
          </div>
        )}

        {/* Waiting state */}
        {isRunning && !results && (
          <div className="rounded-xl border border-slate-800 bg-slate-900/30 p-12 text-center">
            <div className="flex flex-col items-center gap-4">
              <div className="h-10 w-10 rounded-full border-2 border-blue-500/50 border-t-blue-500 animate-spin" />
              <div>
                <p className="text-slate-300 font-medium">Pipeline running…</p>
                <p className="text-slate-500 text-sm mt-1">
                  Results will appear automatically when complete.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 3D Viewer modal */}
      {viewerMol && jobId && (
        <MolViewer
          jobId={jobId}
          molId={viewerMol.mol_id}
          molName={viewerMol.name}
          onClose={() => setViewerMol(null)}
        />
      )}
    </div>
  )
}
