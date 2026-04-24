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
    <main
      style={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        padding: "24px",
      }}
    >
      <section
        style={{
          width: "min(720px, 100%)",
          background: "#ffffff",
          borderRadius: "24px",
          padding: "40px",
          boxShadow: "0 18px 50px rgba(18, 32, 51, 0.12)",
        }}
      >
        <p style={{ margin: 0, color: "#4d6480", fontWeight: 700 }}>React + Django Base</p>
        <h1 style={{ margin: "12px 0", fontSize: "2.5rem", lineHeight: 1.15 }}>
          SKN25 4th 6Team Starter
        </h1>
        <p style={{ margin: 0, color: "#58687d" }}>
          Docker base is ready. Frontend can start from <code>frontend/src</code>, backend can
          start from <code>backend/apps</code> and <code>backend/rag</code>.
        </p>

        <div
          style={{
            marginTop: "28px",
            display: "flex",
            flexWrap: "wrap",
            gap: "12px",
          }}
        >
          <button
            type="button"
            onClick={handleHealthCheck}
            style={{
              border: "none",
              borderRadius: "999px",
              background: "#122033",
              color: "#ffffff",
              padding: "12px 20px",
              cursor: "pointer",
            }}
          >
            Backend Health Check
          </button>
          <div
            style={{
              borderRadius: "999px",
              background: "#eef3f8",
              color: "#24364a",
              padding: "12px 18px",
            }}
          >
            API: {apiBaseUrl}
          </div>
        </div>
      </section>
    </main>
  );
}

export default HomePage;
