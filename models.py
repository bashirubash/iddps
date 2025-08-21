from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

db = SQLAlchemy()

class Account(db.Model):
    id = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    account_number = db.Column(db.String, unique=True, nullable=False)
    holder_name = db.Column(db.String, nullable=False)
    balance = db.Column(db.Float, default=0.0)

class BankTransaction(db.Model):
    id = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tx_type = db.Column(db.String, nullable=False)  # e.g., transfer
    from_account = db.Column(db.String, db.ForeignKey("account.id"))
    to_account = db.Column(db.String, db.ForeignKey("account.id"))
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String, default="pending")  # pending, committed, aborted
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    meta = db.Column(db.JSON, default={})

    @staticmethod
    def new(tx_type, from_id, to_id, amount):
        tx = BankTransaction(
            tx_type=tx_type,
            from_account=from_id,
            to_account=to_id,
            amount=amount
        )
        db.session.add(tx)
        db.session.commit()
        return tx

class ResourceLock(db.Model):
    id = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    resource_type = db.Column(db.String, nullable=False)   # e.g., account
    resource_id = db.Column(db.String, nullable=False)
    tx_id = db.Column(db.String, nullable=False)
    lock_mode = db.Column(db.String, default="exclusive")  # exclusive
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class WaitEdge(db.Model):
    id = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    waiting_tx = db.Column(db.String, nullable=False)
    holding_tx = db.Column(db.String, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @staticmethod
    def estimated_wait_depth(tx_id):
        # rough heuristic: count wait edges
        return WaitEdge.query.filter_by(waiting_tx=tx_id).count()

class DeadlockEvent(db.Model):
    id = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tx_victim = db.Column(db.String, nullable=False)
    cycle = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
