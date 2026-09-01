from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(
    title="Cherry Memory Ledger",
    description="Hackathon prototype for load-bearing accounting memory across fresh sessions.",
    version="0.1.0",
)


@app.get("/api/health")
def health() -> dict[str, str]:
    """Simple deployment health check."""
    return {"status": "ok", "service": "cherry-memory-ledger"}


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    """Temporary landing page until the hackathon UI is implemented."""
    return """
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Cherry Memory Ledger</title>
        <style>
          body { font-family: system-ui, sans-serif; margin: 0; background: #f7f7f5; color: #171717; }
          main { max-width: 760px; margin: 12vh auto; padding: 32px; }
          .card { background: white; border: 1px solid #e5e5e5; border-radius: 20px; padding: 36px; box-shadow: 0 10px 35px rgba(0,0,0,.05); }
          h1 { margin-top: 0; font-size: clamp(2rem, 5vw, 3.4rem); }
          p { font-size: 1.1rem; line-height: 1.6; }
          code { background: #f1f1ef; padding: 3px 7px; border-radius: 6px; }
        </style>
      </head>
      <body>
        <main>
          <section class="card">
            <h1>Cherry Memory Ledger</h1>
            <p><strong>Accounting decisions that compound, instead of disappearing.</strong></p>
            <p>This is the deployment scaffold for the Sibyl Labs hackathon build. The load-bearing Sibyl Memory workflow is being implemented next.</p>
            <p>Health check: <code>/api/health</code></p>
          </section>
        </main>
      </body>
    </html>
    """
