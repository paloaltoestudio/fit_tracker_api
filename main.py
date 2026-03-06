from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from app.database import engine, Base
from app.models import User, Weight, MetricEntry  # Import models so tables are created
from app.routers import auth, weights, profile, metrics, admin

# Create database tables (must import models first)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Fit Tracker API", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1", tags=["authentication"])
app.include_router(weights.router, prefix="/api/v1", tags=["weights"])
app.include_router(profile.router, prefix="/api/v1", tags=["profile"])
app.include_router(metrics.router, prefix="/api/v1", tags=["metrics"])
app.include_router(admin.router, prefix="/api/v1", tags=["admin"])


@app.get("/")
async def root():
    return {"message": "Fit Tracker API"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(request: Request):
    token = request.query_params.get("token", "")
    return HTMLResponse(content=f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Reset Password – Fit Tracker</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f5f5; display: flex; align-items: center; justify-content: center; min-height: 100vh; padding: 16px; }}
    .card {{ background: white; border-radius: 12px; padding: 32px 24px; width: 100%; max-width: 400px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); }}
    h1 {{ font-size: 22px; font-weight: 600; margin-bottom: 8px; color: #111; }}
    p {{ font-size: 14px; color: #666; margin-bottom: 24px; }}
    label {{ display: block; font-size: 13px; font-weight: 500; color: #333; margin-bottom: 6px; }}
    input {{ width: 100%; padding: 10px 12px; border: 1px solid #ddd; border-radius: 8px; font-size: 15px; margin-bottom: 16px; outline: none; transition: border-color 0.2s; }}
    input:focus {{ border-color: #4f46e5; }}
    button {{ width: 100%; padding: 12px; background: #4f46e5; color: white; border: none; border-radius: 8px; font-size: 15px; font-weight: 500; cursor: pointer; transition: background 0.2s; }}
    button:hover {{ background: #4338ca; }}
    button:disabled {{ background: #a5b4fc; cursor: not-allowed; }}
    .message {{ margin-top: 16px; padding: 12px; border-radius: 8px; font-size: 14px; text-align: center; display: none; }}
    .message.success {{ background: #f0fdf4; color: #166534; display: block; }}
    .message.error {{ background: #fef2f2; color: #991b1b; display: block; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>Reset your password</h1>
    <p>Enter your new password below.</p>
    <form id="form">
      <label for="password">New password</label>
      <input type="password" id="password" placeholder="At least 6 characters" required minlength="6" />
      <label for="confirm">Confirm password</label>
      <input type="password" id="confirm" placeholder="Repeat new password" required minlength="6" />
      <button type="submit" id="btn">Reset password</button>
    </form>
    <div class="message" id="msg"></div>
  </div>
  <script>
    const token = "{token}";
    document.getElementById("form").addEventListener("submit", async (e) => {{
      e.preventDefault();
      const password = document.getElementById("password").value;
      const confirm = document.getElementById("confirm").value;
      const btn = document.getElementById("btn");
      const msg = document.getElementById("msg");
      msg.className = "message";
      msg.textContent = "";
      if (password !== confirm) {{
        msg.className = "message error";
        msg.textContent = "Passwords do not match.";
        return;
      }}
      btn.disabled = true;
      btn.textContent = "Resetting...";
      try {{
        const res = await fetch("/api/v1/reset-password", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{ token, new_password: password }}),
        }});
        const data = await res.json();
        if (res.ok) {{
          msg.className = "message success";
          msg.textContent = "Password reset successfully. You can now log in to the app.";
          document.getElementById("form").style.display = "none";
        }} else {{
          msg.className = "message error";
          msg.textContent = data.detail || "Something went wrong. The link may have expired.";
          btn.disabled = false;
          btn.textContent = "Reset password";
        }}
      }} catch (_) {{
        msg.className = "message error";
        msg.textContent = "Network error. Please try again.";
        btn.disabled = false;
        btn.textContent = "Reset password";
      }}
    }});
  </script>
</body>
</html>
""")
