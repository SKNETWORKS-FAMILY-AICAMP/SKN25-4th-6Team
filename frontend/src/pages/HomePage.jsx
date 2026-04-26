import client from "../api/client";

function HomePage() {
  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

  const handleHealthCheck = async () => {
    try {
      const response = await client.get("/api/health/");
      window.alert(`Backend status: ${response.data.status}`);
    } catch (error) {
      window.alert("Backend health check failed.");
    }
  };

  return (
    <main className="app-shell">
      <section className="hero-panel">
        <p className="eyebrow">Official Vite Base + Project Structure</p>
        <h1>SKN25 4th 6Team Frontend Starter</h1>
        <p className="description">
          React official scaffold is in place. Frontend development can continue from{" "}
          <code>src/pages</code>, <code>src/components</code>, and <code>src/api</code>.
        </p>
        <div className="actions">
          <button type="button" className="primary-button" onClick={handleHealthCheck}>
            Backend Health Check
          </button>
          <span className="api-pill">API: {apiBaseUrl}</span>
        </div>
      </section>
    </main>
  );
}

export default HomePage;
