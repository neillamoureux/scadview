"""Controlled queue interleavings; no GUI or timing-dependent polling."""

import logging
import queue
from unittest.mock import Mock

import pytest

from scadview.mesh_loader_process import (
    LoadEventChannel,
    LoadPhase,
    LoadResult,
    MeshLoaderProcess,
)


@pytest.mark.parametrize("handoff", ["worker-loader", "loader-gui"])
@pytest.mark.parametrize("phase", [LoadPhase.PROGRESS, LoadPhase.FINAL])
@pytest.mark.parametrize("refill", [None, 1, 3])
def test_result_delivery_retries_after_consumer_removes_item(handoff, phase, refill):
    transport = ConsumerRaceQueue()
    publish = publication_handoff(handoff, transport)
    previous = result(1, LoadPhase.PROGRESS)
    incoming = result(2, phase)
    competing = result(refill, phase) if refill else None
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
    publish = publication_handoff(handoff, transport)
    newer = result(3, phase)
    transport.put_nowait(newer)

    publish(result(2, phase))

    assert transport.get_nowait() is newer
    assert transport.empty()


@pytest.mark.parametrize("reader", ["get", "get_nowait"])
def test_load_event_channel_returns_load_result_directly(reader):
    channel = LoadEventChannel()
    value = result(1, LoadPhase.FINAL)
    channel.put_latest(value)

    assert getattr(channel, reader)() is value


def publication_handoff(handoff, transport):
    if handoff == "worker-loader":
        channel = LoadEventChannel()
        channel._queue = transport
        return channel.put_latest
    process = MeshLoaderProcess(Mock(), transport, Mock(), Mock(), logging.INFO)
    return process._publish_load_result


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
