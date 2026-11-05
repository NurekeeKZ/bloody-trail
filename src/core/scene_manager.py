class SceneManager:
    """Stack preserves the exploration instance and exact position during overlays."""
    def __init__(self):
        self.stack = []

    @property
    def current(self):
        return self.stack[-1]

    def replace(self, scene):
        for old in reversed(self.stack):
            getattr(old, 'on_exit', lambda: None)()
        self.stack = [scene]

    def push(self, scene):
        if self.stack:
            getattr(self.current, 'on_cover', lambda: None)()
        self.stack.append(scene)

    def pop(self):
        if len(self.stack) > 1:
            getattr(self.stack.pop(), 'on_exit', lambda: None)()

    def close(self):
        for scene in reversed(self.stack):
            getattr(scene, 'on_exit', lambda: None)()
