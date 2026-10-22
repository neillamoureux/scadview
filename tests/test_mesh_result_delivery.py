"""Controlled queue interleavings; no GUI or timing-dependent polling."""

import logging
import queue
from unittest.mock import Mock

import pytest

from scadview.mesh_loader_process import (
    LoadCompletionEvent,
    LoadEventChannel,
    LoadPhase,
    LoadResult,
    LoadResultEvent,
    MeshLoaderProcess,
)


@pytest.mark.parametrize("handoff", ["worker-loader", "loader-gui"])
@pytest.mark.parametrize("phase", [LoadPhase.PROGRESS, LoadPhase.FINAL])
@pytest.mark.parametrize("refill", [None, 1, 3])
def test_result_delivery_retries_after_consumer_removes_item(handoff, phase, refill):
    transport = ConsumerRaceQueue()
    publish, wrap = publication_handoff(handoff, transport)
    previous = wrap(result(1, LoadPhase.PROGRESS))
    incoming = wrap(result(2, phase))
    competing = wrap(result(refill, phase)) if refill else None
    transport.put_nowait(previous)
    transport.refill = competing
    transport.drain_on_full = True

    publish(incoming)

    expected = competing if refill == 3 else incoming
    assert transport.get_nowait() is expected
    assert transport.empty()
    assert transport.consumer_removals == 1


@pytest.mark.parametrize("handoff", ["worker-loader", "loader-gui"])
@pytest.mark.parametrize("phase", [LoadPhase.PROGRESS, LoadPhase.FINAL])
def test_older_generation_does_not_replace_newer_result(handoff, phase):
    transport = queue.Queue(maxsize=1)
    publish, wrap = publication_handoff(handoff, transport)
    newer = wrap(result(3, phase))
    transport.put_nowait(newer)

    publish(wrap(result(2, phase)))

    assert transport.get_nowait() is newer
    assert transport.empty()


def publication_handoff(handoff, transport):
    if handoff == "worker-loader":
        channel = LoadEventChannel()
        channel._queue = transport
        return channel.put_latest, wrap_event
    process = MeshLoaderProcess(Mock(), transport, Mock(), Mock(), logging.INFO)
    return process._publish_load_result, lambda value: value


def wrap_event(value):
    event_type = LoadCompletionEvent if value.complete else LoadResultEvent
    return event_type(value)


def result(generation, phase):
    return LoadResult(1, 1, None, None, phase, 1, False, False, generation=generation)


class ConsumerRaceQueue(queue.Queue):
    def __init__(self):
        super().__init__(maxsize=1)
        self.drain_on_full = False
        self.consumer_removals = 0
        self.refill = None

    def put(self, item, block=True, timeout=None):
        try:
            return super().put(item, block=False)
        except queue.Full:
            if self.drain_on_full:
                self.drain_on_full = False
                super().get(block=False)
                self.consumer_removals += 1
            raise

    def get_nowait(self):
        try:
            return super().get_nowait()
        except queue.Empty:
            # Another sender fills the slot after the empty removal attempt.
            if self.refill is not None:
                super().put(self.refill, block=False)
                self.refill = None
            raise
