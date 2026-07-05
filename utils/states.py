"""
Lightweight in-memory conversation state manager for multi-step forms.

Each user has at most one active flow. A flow has a name, a current step,
and a mutable data dict that accumulates collected values. State is kept in
memory which is appropriate for a single Railway instance; it is rebuilt
naturally after a restart because every action starts from the menu.
"""
import threading
import time


class Flow:
    def __init__(self, name, step=None, data=None):
        self.name = name
        self.step = step
        self.data = data or {}
        self.created_at = time.time()


class StateManager:
    def __init__(self, ttl=1800):
        self._states = {}
        self._lock = threading.RLock()
        self._ttl = ttl

    def start(self, user_id, name, step=None, data=None):
        with self._lock:
            flow = Flow(name, step, data)
            self._states[user_id] = flow
            return flow

    def get(self, user_id):
        with self._lock:
            flow = self._states.get(user_id)
            if flow is None:
                return None
            if time.time() - flow.created_at > self._ttl:
                self._states.pop(user_id, None)
                return None
            return flow

    def set_step(self, user_id, step):
        with self._lock:
            flow = self._states.get(user_id)
            if flow:
                flow.step = step
                flow.created_at = time.time()
            return flow

    def update_data(self, user_id, **kwargs):
        with self._lock:
            flow = self._states.get(user_id)
            if flow:
                flow.data.update(kwargs)
                flow.created_at = time.time()
            return flow

    def clear(self, user_id):
        with self._lock:
            self._states.pop(user_id, None)

    def has_active(self, user_id):
        return self.get(user_id) is not None


# Global singleton used across handlers
states = StateManager()
