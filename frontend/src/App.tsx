import { BrowserRouter, Route, Routes } from "react-router-dom"
import { HomePage } from "./pages/Home"
import { ResultsPage } from "./pages/Results"

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/results/:jobId" element={<ResultsPage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
