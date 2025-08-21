from models import db, ResourceLock, WaitEdge, DeadlockEvent, BankTransaction
import uuid

class LockManager:
    def request_exclusive(self, resource_type, resource_id, tx_id):
        # check if lock exists
        existing = ResourceLock.query.filter_by(resource_type=resource_type, resource_id=resource_id).first()
        if existing and existing.tx_id != tx_id:
            # create wait edge
            edge = WaitEdge(waiting_tx=tx_id, holding_tx=existing.tx_id)
            db.session.add(edge)
            db.session.commit()

            # check for deadlock
            cycle = self.detect_cycle(tx_id)
            if cycle:
                # abort victim
                victim = cycle[-1]
                self.abort_transaction(victim, cycle)
                return False
            return False

        # otherwise, grant lock
        lock = ResourceLock(resource_type=resource_type, resource_id=resource_id, tx_id=tx_id)
        db.session.add(lock)
        db.session.commit()
        return True

    def release_all(self, tx_id):
        ResourceLock.query.filter_by(tx_id=tx_id).delete()
        WaitEdge.query.filter_by(waiting_tx=tx_id).delete()
        WaitEdge.query.filter_by(holding_tx=tx_id).delete()
        db.session.commit()

    def detect_cycle(self, start_tx):
        graph = {}
        for e in WaitEdge.query.all():
            graph.setdefault(e.waiting_tx, []).append(e.holding_tx)

        visited = set()
        stack = []

        def dfs(node):
            visited.add(node)
            stack.append(node)
            for neigh in graph.get(node, []):
                if neigh not in visited:
                    if dfs(neigh):
                        return True
                elif neigh in stack:
                    # cycle found
                    idx = stack.index(neigh)
                    cycle = stack[idx:] + [neigh]
                    self.record_deadlock(cycle)
                    return True
            stack.pop()
            return False

        dfs(start_tx)
        return None

    def record_deadlock(self, cycle):
        victim = cycle[-1]
        event = DeadlockEvent(tx_victim=victim, cycle=cycle)
        db.session.add(event)
        db.session.commit()

    def abort_transaction(self, tx_id, cycle):
        BankTransaction.query.filter_by(id=tx_id).update({"status": "aborted"})
        self.release_all(tx_id)
        event = DeadlockEvent(tx_victim=tx_id, cycle=cycle)
        db.session.add(event)
        db.session.commit()
