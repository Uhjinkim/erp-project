import { useEffect, useState } from "react"

type ApiStatus = "checking" | "online" | "offline"

function App() {
  const [apiStatus, setApiStatus] = useState<ApiStatus>("checking")

  useEffect(() => {
    fetch("/api/health/")
      .then((response) => {
        if (!response.ok) throw new Error("Backend health check failed")
        setApiStatus("online")
      })
      .catch(() => setApiStatus("offline"))
  }, [])

  return (
    <main>
      <h1>ERP Project</h1>
      <p>React + Django development environment is ready.</p>
      <p className={`status status--${apiStatus}`}>
        Backend: {apiStatus}
      </p>
    </main>
  )
}

export default App
