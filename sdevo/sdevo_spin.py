#!/usr/bin/env python3
"""Headless entry point for the upstream sdevo node.

Upstream DEVO/src/sdevo.py's __main__ does:
    rospy.set_param("/use_sim_time", False); listener = VoxelListener()
i.e. it constructs the listener but never calls its own run() (= rospy.spin()),
so under roslaunch the process can exit before any voxel arrives. This wrapper
replicates the upstream __main__ exactly and then calls the UPSTREAM run()
method. No upstream code is modified.
"""
import sys

sys.path.insert(0, "/catkin_ws/src/SDEVO/DEVO/src")

import rospy  # noqa: E402

rospy.set_param("/use_sim_time", False)   # exactly what upstream __main__ does

import sdevo  # noqa: E402  (imports upstream module; reads sdevoDirStr rosparam)

listener = sdevo.VoxelListener()
listener.run()                            # upstream method: rospy.spin()
