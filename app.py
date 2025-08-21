import os, uuid
from flask import Flask, request, jsonify, render_template
from models import db, Account, BankTransaction, ResourceLock, WaitEdge, DeadlockEvent
from lock_manager import LockManager
from ml import MLGuard, get_default_guard

def create_app():
    app = Flask(__name__, template_folder="templates")
    db_url = os.getenv("DATABASE_URL", "sqlite:///local.db")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    with app.app_context():
    try:
        db.create_all()
    except Exception as e:
        app.logger.warning(f"DB init skipped: {e}")
        if Account.query.count() == 0:
            db.session.add_all([
                Account(account_number="0001", holder_name="Alice", balance=10000.00),
                Account(account_number="0002", holder_name="Bob", balance=8000.00),
                Account(account_number="0003", holder_name="Charlie", balance=5000.00),
            ])
            db.session.commit()
    lm = LockManager(); guard: MLGuard = get_default_guard()
    @app.get("/")
    def home():
        stats = {"accounts": Account.query.count(),"transactions": BankTransaction.query.count(),
                 "locks": ResourceLock.query.count(),"waits": WaitEdge.query.count(),
                 "deadlocks": DeadlockEvent.query.count()}
        latest = BankTransaction.query.order_by(BankTransaction.created_at.desc()).limit(10).all()
        return render_template("dashboard.html", stats=stats, latest=latest)
    @app.get("/api/dashboard")
    def dashboard():
        return jsonify({"accounts": Account.query.count(),"transactions": BankTransaction.query.count(),
                        "locks": ResourceLock.query.count(),"waits": WaitEdge.query.count(),
                        "deadlocks": DeadlockEvent.query.count()})
    @app.post("/api/transfer")
    def transfer():
        data = request.get_json(force=True)
        for k in ["from_account","to_account","amount"]:
            if k not in data: return jsonify({"error": f"Missing field: {k}"}), 400
        if data["from_account"] == data["to_account"]:
            return jsonify({"error":"from_account and to_account must differ"}), 400
        try:
            amount = float(data["amount"]); assert amount>0
        except: return jsonify({"error":"amount must be positive number"}), 400
        from_acct = Account.query.filter_by(account_number=data["from_account"]).first()
        to_acct   = Account.query.filter_by(account_number=data["to_account"]).first()
        if not from_acct or not to_acct: return jsonify({"error":"Invalid account number(s)"}), 404
        tx = BankTransaction.new("transfer", from_acct.id, to_acct.id, amount)
        features = guard.build_features(system_load=0.6, wait_depth=WaitEdge.estimated_wait_depth(tx.id),
                                        amount=amount, hotspot=1 if from_acct.balance < 1000 else 0)
        risk = guard.predict_risk(features); mitigation = "reorder" if risk>=0.8 else None
        order = sorted([from_acct.id, to_acct.id]); 
        if mitigation=="reorder": order = sorted(order, reverse=True)
        got_all=True
        for rid in order:
            if not lm.request_exclusive("account", rid, tx.id): got_all=False
        if tx.status=="aborted": return jsonify({"status":"deadlock_aborted","tx":tx.id}), 409
        if not got_all:
            for rid in order:
                if not lm.request_exclusive("account", rid, tx.id):
                    return jsonify({"status":"pending","tx":tx.id}), 202
        if from_acct.balance < amount:
            lm.release_all(tx.id); tx.status="aborted"; tx.meta={"reason":"insufficient_funds"}; 
            db.session.commit(); return jsonify({"status":"insufficient_funds"}), 422
        from_acct.balance -= amount; to_acct.balance += amount; tx.status="committed"; 
        db.session.commit(); lm.release_all(tx.id); return jsonify({"status":"ok","tx":tx.id}), 200
    @app.post("/api/reset")
    def reset():
        WaitEdge.query.delete(); ResourceLock.query.delete(); DeadlockEvent.query.delete()
        BankTransaction.query.delete(); Account.query.delete(); db.session.commit()
        db.session.add_all([
            Account(account_number="0001", holder_name="Alice", balance=10000.00),
            Account(account_number="0002", holder_name="Bob", balance=8000.00),
            Account(account_number="0003", holder_name="Charlie", balance=5000.00),
        ]); db.session.commit(); return jsonify({"status":"reset_ok"})
    return app
app = create_app()
