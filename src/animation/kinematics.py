"""
Kinematics & Motion Trajectory Engine (Inspired by gestura-ai/stick-gen).
Models skeletal joint angles, momentum curves, and keyframe pose interpolation:
- Root position & velocity (x, y, vx, vy)
- 10-DOF Joint Rotations (spine, shoulders, elbows, hips, knees)
- Eased phase transitions between action keyframes
"""

import math

def ease_in_out(t):
    """Hermite smoothstep easing curve for natural cartoon acceleration/deceleration."""
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)

# Canonical 10-DOF Joint Angle Presets (angles in radians)
# [spine, l_shoulder, l_elbow, r_shoulder, r_elbow, l_hip, l_knee, r_hip, r_knee]
POSE_PRESETS = {
    "stand": {
        "spine_lean": 0.0,
        "l_shoulder": 0.35, "l_elbow": 0.25,
        "r_shoulder": -0.35, "r_elbow": -0.25,
        "l_hip": 0.15, "l_knee": 0.0,
        "r_hip": -0.15, "r_knee": 0.0
    },
    "celebrating": {
        "spine_lean": 0.0,
        "l_shoulder": -2.2, "l_elbow": 0.8,
        "r_shoulder": 2.2, "r_elbow": -0.8,
        "l_hip": 0.25, "l_knee": 0.1,
        "r_hip": -0.25, "r_knee": 0.1
    },
    "pointing": {
        "spine_lean": 0.05,
        "l_shoulder": 0.4, "l_elbow": 0.3,
        "r_shoulder": 1.45, "r_elbow": 0.1,
        "l_hip": 0.1, "l_knee": 0.0,
        "r_hip": -0.1, "r_knee": 0.0
    },
    "facepalm": {
        "spine_lean": 0.15,
        "l_shoulder": 0.3, "l_elbow": 0.4,
        "r_shoulder": 1.9, "r_elbow": 2.1,
        "l_hip": 0.1, "l_knee": 0.05,
        "r_hip": -0.1, "r_knee": 0.05
    },
    "hands_up": {
        "spine_lean": 0.0,
        "l_shoulder": -1.8, "l_elbow": -0.5,
        "r_shoulder": 1.8, "r_elbow": 0.5,
        "l_hip": 0.2, "l_knee": 0.0,
        "r_hip": -0.2, "r_knee": 0.0
    }
}

def interpolate_joint_angles(pose_a_name, pose_b_name, progress):
    """
    Interpolates joint rotations between two pose presets with smoothstep easing
    (gestura-ai style continuous joint trajectory).
    """
    p_a = POSE_PRESETS.get(pose_a_name, POSE_PRESETS["stand"])
    p_b = POSE_PRESETS.get(pose_b_name, POSE_PRESETS["stand"])
    alpha = ease_in_out(progress)

    blended = {}
    for k in p_a:
        blended[k] = p_a[k] + alpha * (p_b[k] - p_a[k])
    return blended

def compute_run_stride_angles(phase):
    """
    Computes dynamic running joint angles using sinusoidal momentum curves.
    """
    sin_p = math.sin(phase)
    cos_p = math.cos(phase)

    return {
        "spine_lean": 0.28,
        # Arms pump opposite to legs
        "l_shoulder": -sin_p * 0.9 + 0.3,
        "l_elbow": max(0.4, cos_p * 0.7 + 0.6),
        "r_shoulder": sin_p * 0.9 + 0.3,
        "r_elbow": max(0.4, -cos_p * 0.7 + 0.6),
        # Legs stride
        "l_hip": sin_p * 0.85,
        "l_knee": max(0.0, -cos_p * 1.1 + 0.5),
        "r_hip": -sin_p * 0.85,
        "r_knee": max(0.0, cos_p * 1.1 + 0.5)
    }

if __name__ == "__main__":
    angles = interpolate_joint_angles("stand", "celebrating", 0.5)
    print("Blended 50% Pose:", angles)
