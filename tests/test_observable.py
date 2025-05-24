import pytest
from meshsee.observable import Observable


def test_subscribe_and_notify():
    observable = Observable()
    results = []

    def callback(arg):
        results.append(arg)

    observable.subscribe(callback)
    observable.notify("test")

    assert results == ["test"]


def test_unsubscribe():
    observable = Observable()
    results = []

    def callback(arg):
        results.append(arg)

    observable.subscribe(callback)
    observable.unsubscribe(callback)
    observable.notify("test")

    assert results == []


def test_multiple_subscribers():
    observable = Observable()
    results = []

    def callback1(arg):
        results.append(f"callback1: {arg}")

    def callback2(arg):
        results.append(f"callback2: {arg}")

    observable.subscribe(callback1)
    observable.subscribe(callback2)
    observable.notify("test")

    assert results == ["callback1: test", "callback2: test"]


def test_weakref_cleanup():
    observable = Observable()
    results = []

    class TestObserver:
        def callback(self, arg):
            results.append(arg)

    observer = TestObserver()
    observable.subscribe(observer.callback)
    del observer  # Remove strong reference to observer
    observable.notify("test")

    assert results == []  # Callback should not be called since observer is deleted
