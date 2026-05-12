"""Tests for RingBuffer - the thread-safe data structure at the heart of the pipeline."""

import pytest
import threading
import time

from src.serial.ring_buffer import RingBuffer
from src.models.data_packet import DataPacket, Direction


def make_packet(data_byte: int) -> DataPacket:
    """Helper: create a single-byte test packet."""
    return DataPacket(data=bytes([data_byte & 0xFF]), direction=Direction.RX)


class TestRingBuffer:
    """Unit tests for RingBuffer."""

    def test_append_and_drain(self):
        buf = RingBuffer(max_size=100)
        for i in range(5):
            buf.append(make_packet(i))
        drained = buf.drain()
        assert len(drained) == 5
        assert drained[0].data == b"\x00"
        assert drained[4].data == b"\x04"
        assert buf.length == 0

    def test_drain_empty_returns_empty_list(self):
        buf = RingBuffer()
        drained = buf.drain()
        assert drained == []

    def test_drain_is_atomic(self):
        """After drain, buffer should be empty."""
        buf = RingBuffer()
        buf.append(make_packet(0))
        buf.append(make_packet(1))
        drained = buf.drain()
        assert len(drained) == 2
        assert buf.drain() == []

    def test_drain_preserves_new_appends(self):
        """Packets appended after a drain stay in the active buffer."""
        buf = RingBuffer()
        buf.append(make_packet(0))

        first = buf.drain()
        buf.append(make_packet(1))
        second = buf.drain()

        assert [packet.data for packet in first] == [b"\x00"]
        assert [packet.data for packet in second] == [b"\x01"]

    def test_max_size_enforcement(self):
        """When max_size is exceeded, oldest entries are dropped."""
        buf = RingBuffer(max_size=3)
        buf.append(make_packet(0))
        buf.append(make_packet(1))
        buf.append(make_packet(2))
        buf.append(make_packet(3))
        drained = buf.drain()
        assert len(drained) == 3
        assert drained[0].data == b"\x01"

    def test_overflow_count(self):
        buf = RingBuffer(max_size=2)
        buf.append(make_packet(0))
        buf.append(make_packet(1))
        buf.append(make_packet(2))
        buf.append(make_packet(3))
        assert buf.overflow_count == 2
        buf.drain()
        assert buf.overflow_count == 0

    def test_peek_does_not_remove(self):
        buf = RingBuffer()
        buf.append(make_packet(0))
        assert buf.length == 1
        peeked = buf.peek()
        assert len(peeked) == 1
        assert buf.length == 1

    def test_clear(self):
        buf = RingBuffer()
        buf.append(make_packet(0))
        buf.append(make_packet(1))
        buf.clear()
        assert buf.length == 0
        assert buf.drain() == []

    def test_thread_safety(self):
        """Two threads appending simultaneously should not lose data."""
        buf = RingBuffer(max_size=1000)
        n_packets = 500

        def writer(offset: int):
            for i in range(n_packets):
                buf.append(make_packet(offset * n_packets + i))

        t1 = threading.Thread(target=writer, args=(0,))
        t2 = threading.Thread(target=writer, args=(1,))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        total = buf.length
        assert total == n_packets * 2, f"Expected {n_packets * 2}, got {total}"
