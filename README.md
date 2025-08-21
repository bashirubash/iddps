# IDDPS (Integrated Deadlock Detection & Prevention System)
Stack: Flask + SQLAlchemy + (optional) ML guard
Deploy: Render Blueprint via render.yaml (provisions free Postgres)

Local:
  pip install -r requirements.txt
  set DATABASE_URL=sqlite:///local.db  # or export on macOS/Linux
  python app.py
Open: http://localhost:5000

API:
  POST /api/transfer  { "from_account":"0001","to_account":"0002","amount": 50 }
  GET  /api/dashboard
  POST /api/reset
