#!/usr/bin/env python3
"""Merge rosbag1 files into one, preserving every message byte-for-byte
(connections per topic, messages interleaved in bag-time order).

Used to feed ESVO2's upstream events_repacking_tool (EventMessageEditor), which
reads /davis/left/events and /davis/right/events from a SINGLE input bag. No
repacking of any kind happens here — temporal repacking is done exclusively by
the upstream tool.

Usage: merge_dvs_bags.py OUT.bag IN1.bag IN2.bag [...]
"""
import argparse
import heapq
from rosbags.rosbag1 import Reader, Writer
from rosbags.typesys import Stores, get_typestore, get_types_from_msg

DVS_EVENT = "uint16 x\nuint16 y\ntime ts\nbool polarity\n"
DVS_EVENTARRAY = "std_msgs/Header header\nuint32 height\nuint32 width\ndvs_msgs/Event[] events\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("out_bag")
    ap.add_argument("in_bags", nargs="+")
    a = ap.parse_args()

    ts = get_typestore(Stores.ROS1_NOETIC)
    types = {}
    types.update(get_types_from_msg(DVS_EVENT, "dvs_msgs/msg/Event"))
    types.update(get_types_from_msg(DVS_EVENTARRAY, "dvs_msgs/msg/EventArray"))
    ts.register(types)

    readers = [Reader(p) for p in a.in_bags]
    for r in readers:
        r.open()
    try:
        with Writer(a.out_bag) as w:
            wconns = {}
            streams = []
            for ri, r in enumerate(readers):
                for c in r.connections:
                    if c.topic not in wconns:
                        wconns[c.topic] = w.add_connection(c.topic, c.msgtype, typestore=ts)
                it = r.messages()
                first = next(it, None)
                if first:
                    conn, t, raw = first
                    heapq.heappush(streams, (t, ri, conn.topic, raw, it))
            n = 0
            while streams:
                t, ri, topic, raw, it = heapq.heappop(streams)
                w.write(wconns[topic], t, raw)
                n += 1
                nxt = next(it, None)
                if nxt:
                    conn, t2, raw2 = nxt
                    heapq.heappush(streams, (t2, ri, conn.topic, raw2, it))
        print(f"merged {n} msgs from {len(a.in_bags)} bags -> {a.out_bag} "
              f"(topics: {sorted(wconns)})")
    finally:
        for r in readers:
            r.close()


if __name__ == "__main__":
    raise SystemExit(main())
