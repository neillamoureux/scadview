import weakref
from typing import Any, Callable


class Observable:
    """
    Manages a list of subscriber callbacks and notifies them on change.
    Uses weakrefs so observers don't keep each other alive.
    """

    def __init__(self):
        # store weak refs to bound methods or functions
        self._subscribers = []

    def subscribe(self, callback: Callable[..., Any]):
        """Register a callable to be notified."""
        # wrap bound methods and functions in a WeakMethod if possible
        try:
            ref = weakref.WeakMethod(callback)
        except TypeError:
            # plain functions aren’t bound; store a normal weakref
            ref = weakref.ref(callback)
        self._subscribers.append(ref)

    def unsubscribe(self, callback: Callable[..., Any]):
        """Remove a previously registered callback."""
        # compare original to dereferenced weakrefs
        self._subscribers[:] = [r for r in self._subscribers if r() is not callback]

    def notify(self, *args: Any, **kwargs: Any):
        """Call every subscriber, pass along any arguments."""
        dead = []
        for ref in self._subscribers:
            fn = ref()
            if fn is None:
                dead.append(ref)
            else:
                fn(*args, **kwargs)
        # clean up any dead refs
        for ref in dead:
            self._subscribers.remove(ref)
