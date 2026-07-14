#!/usr/bin/env python3
"""Convert a Prophesee event rosbag (e.g. VECtor) to ESVIO's dvs_msgs form,
optionally repacking events into fixed-rate frames.

`prophesee_event_msgs/EventArray` and `dvs_msgs/EventArray` share an identical
wire layout:

    Header header
    uint32 height
    uint32 width
    Event[] events           # Event = uint16 x, uint16 y, time ts, bool polarity

so the per-event bytes are copied verbatim; only the connection type/topic change
and (optionally) events are re-binned into 1/hz-second frames.

Why repack: ESVIO's event tracker keeps only the *most recent* EventArray each
cycle (feature_tracker/src/stereo_event_tracker_node.cpp), expecting dense ~60 Hz
event frames. VECtor ships ~3.9 k tiny arrays/s, which would starve it. This
replicates volkbay's `events_repacking_helper` (hard-coded 60 Hz): accumulate
events into 1/hz windows, emit one array per window stamped at the window end.

Runs host-side with pure-Python `rosbags` (no ROS needed).

Usage:
  prophesee_to_dvs_bag.py IN.bag OUT.bag --out-topic /davis/left/events --repack-hz 60
"""
import argparse
import struct
import sys
from pathlib import Path

from rosbags.highlevel import AnyReader
from rosbags.rosbag1 import Reader, Writer
from rosbags.typesys import Stores, get_typestore, get_types_from_msg

DVS_EVENT = "uint16 x\nuint16 y\ntime ts\nbool polarity\n"
DVS_EVENTARRAY = "std_msgs/Header header\nuint32 height\nuint32 width\ndvs_msgs/Event[] events\n"
EXPECT_MD5 = "5e8beee5a6c107e504c2e78903c224b8"  # dvs_msgs/EventArray (rpg_dvs_ros)
EVENT_SIZE = 13  # bytes per event: x(2) y(2) ts.sec(4) ts.nsec(4) polarity(1)

_U32 = struct.Struct("<I")
_3U32 = struct.Struct("<III")


def parse_envelope(raw):
    """ROS1-serialized EventArray bytes -> fields + raw events block."""
    seq, sec, nsec = _3U32.unpack_from(raw, 0)
    off = 12
    (flen,) = _U32.unpack_from(raw, off); off += 4
    frame_id = raw[off:off + flen]; off += flen
    (height,) = _U32.unpack_from(raw, off); off += 4
    (width,) = _U32.unpack_from(raw, off); off += 4
    (count,) = _U32.unpack_from(raw, off); off += 4
    return seq, sec, nsec, frame_id, height, width, count, raw[off:off + count * EVENT_SIZE]


def build_envelope(seq, sec, nsec, frame_id, height, width, count, events_bytes):
    return b"".join((
        _U32.pack(seq), _U32.pack(sec), _U32.pack(nsec),
        _U32.pack(len(frame_id)), frame_id,
        _U32.pack(height), _U32.pack(width),
        _U32.pack(count), events_bytes,
    ))


def validate_parser(in_bag, src_topic, n=50):
    """Cross-check the byte parser against rosbags' deserializer on the first n msgs."""
    with AnyReader([Path(in_bag)]) as r:
        conn = [c for c in r.connections if c.topic == src_topic][0]
        for i, (con, t, raw) in enumerate(r.messages(connections=[conn])):
            m = r.deserialize(raw, con.msgtype)
            _, _, _, _, h, w, cnt, ev = parse_envelope(raw)
            assert (h, w, cnt) == (m.height, m.width, len(m.events)), (h, w, cnt)
            if cnt:
                x, y = struct.unpack_from("<HH", ev, 0)
                assert (x, y) == (m.events[0].x, m.events[0].y), (x, y)
            if i + 1 >= n:
                break


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("in_bag")
    ap.add_argument("out_bag")
    ap.add_argument("--in-topic", default=None, help="source topic (default: the EventArray topic)")
    ap.add_argument("--out-topic", required=True)
    ap.add_argument("--repack-hz", type=float, default=0.0,
                    help="re-bin events into 1/hz-second frames (0 = keep native packaging)")
    ap.add_argument("--downscale", type=int, default=1,
                    help="integer spatial downscale N: x//N, y//N, width/N, height/N "
                         "(ESVO2 authors' fast-sequence recipe, NAIL-HNU/ESVO2 issue #9)")
    a = ap.parse_args()

    if a.downscale > 1:
        import numpy as np
        _EV_DT = np.dtype([("x", "<u2"), ("y", "<u2"), ("sec", "<u4"),
                           ("nsec", "<u4"), ("pol", "u1")])

        def downscale_block(block, n):
            arr = np.frombuffer(block, dtype=_EV_DT).copy()
            arr["x"] //= n
            arr["y"] //= n
            return arr.tobytes()

    ts = get_typestore(Stores.ROS1_NOETIC)
    types = {}
    types.update(get_types_from_msg(DVS_EVENT, "dvs_msgs/msg/Event"))
    types.update(get_types_from_msg(DVS_EVENTARRAY, "dvs_msgs/msg/EventArray"))
    ts.register(types)

    with Reader(a.in_bag) as reader:
        conns = list(reader.connections)
        src = ([c for c in conns if c.topic == a.in_topic] if a.in_topic
               else [c for c in conns if c.msgtype.endswith("EventArray")])
        if not src:
            print(f"ERROR: no EventArray topic in {a.in_bag} (have {[c.topic for c in conns]})",
                  file=sys.stderr)
            return 2
        src_topic = src[0].topic
        validate_parser(a.in_bag, src_topic)
        n_in = sum(c.msgcount for c in src)
        print(f"src {src_topic} ({src[0].msgtype}, {n_in} msgs) -> "
              f"{a.out_topic} dvs_msgs/EventArray  repack_hz={a.repack_hz}")

        n_out = ev_total = 0
        with Writer(a.out_bag) as writer:
            wconn = writer.add_connection(a.out_topic, "dvs_msgs/msg/EventArray", typestore=ts)
            if a.repack_hz <= 0:
                for conn, t, raw in reader.messages(connections=src):
                    if a.downscale > 1:
                        seq_, sec, nsec, fid, h, w, c, ev = parse_envelope(raw)
                        raw = build_envelope(seq_, sec, nsec, fid, h // a.downscale,
                                             w // a.downscale, c,
                                             downscale_block(ev, a.downscale))
                    writer.write(wconn, t, raw); n_out += 1
            else:
                period = int(round(1e9 / a.repack_hz))
                win_end = None
                buf, cnt, W, H, seq = [], 0, 0, 0, 0
                for conn, t, raw in reader.messages(connections=src):
                    _, sec, nsec, _, h, w, c, ev = parse_envelope(raw)
                    if a.downscale > 1:
                        ev = downscale_block(ev, a.downscale)
                        h //= a.downscale
                        w //= a.downscale
                    W, H = w, h
                    tns = sec * 1_000_000_000 + nsec
                    if win_end is None:
                        win_end = tns + period
                    while tns >= win_end:
                        if cnt:
                            s, ns = divmod(win_end, 1_000_000_000)
                            writer.write(wconn, win_end,
                                         build_envelope(seq, s, ns, b"", H, W, cnt, b"".join(buf)))
                            n_out += 1; ev_total += cnt; seq += 1
                        buf, cnt = [], 0
                        win_end += period
                    buf.append(ev); cnt += c
                if cnt:  # flush last partial window
                    s, ns = divmod(win_end, 1_000_000_000)
                    writer.write(wconn, win_end,
                                 build_envelope(seq, s, ns, b"", H, W, cnt, b"".join(buf)))
                    n_out += 1; ev_total += cnt

    with Reader(a.out_bag) as r:
        c = next(iter(r.connections))
        md5 = getattr(c, "digest", None)
        extra = f", {ev_total} events" if a.repack_hz > 0 else ""
        print(f"wrote {n_out} msgs{extra}; topic={c.topic} type={c.msgtype} md5={md5}")
        if md5 and md5 != EXPECT_MD5:
            print(f"ERROR: md5 {md5} != expected {EXPECT_MD5}", file=sys.stderr)
            return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
