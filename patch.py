import re
import numpy as np

with open('collision_logic.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. get_velocity_vector
new_func = """    def get_velocity_vector(self, frames_back=3):
        if len(self.boxes) <= frames_back:
            return (0.0, 0.0)
        c1 = get_box_center(self.boxes[-(frames_back+1)])
        c2 = get_box_center(self.boxes[-1])
        return (c2[0] - c1[0], c2[1] - c1[1])

    def get_current_box(self):"""
content = content.replace("    def get_current_box(self):", new_func)

# 2. SimpleTracker IoU
content = content.replace(
    "                distance = get_box_distance(curr_box, det_box)\n\n                if distance < best_distance and distance < self.max_distance:",
    "                distance = get_box_distance(curr_box, det_box)\n                iou = get_iou(curr_box, det_box)\n                match_score = distance * (1.0 - iou)\n\n                if match_score < best_distance and distance < self.max_distance:"
)

# 3. Angle score & Severity in detect_collision_advanced
old_logic = "        max_drop = max(drop1, drop2)\n        if max_drop > SUDDEN_SPEED_DROP_RATIO:\n            speed_drop_score = min(1.0, max_drop)\n\n    # Se"
new_logic = """        max_drop = max(drop1, drop2)
        if max_drop > SUDDEN_SPEED_DROP_RATIO:
            speed_drop_score = min(1.0, max_drop)

    vec_hist1 = track1.get_velocity_vector(frame_history)
    vec_curr1 = track1.get_velocity_vector(2)
    angle_score = 0.0
    if np.linalg.norm(vec_hist1) > 1 and np.linalg.norm(vec_curr1) > 1:
        cos_t1 = np.dot(vec_hist1, vec_curr1) / (np.linalg.norm(vec_hist1) * np.linalg.norm(vec_curr1))
        angle_diff1 = np.arccos(np.clip(cos_t1, -1.0, 1.0)) * (180 / np.pi)
        angle_score = max(angle_score, angle_diff1 / 45.0)
        
    vec_hist2 = track2.get_velocity_vector(frame_history)
    vec_curr2 = track2.get_velocity_vector(2)
    if np.linalg.norm(vec_hist2) > 1 and np.linalg.norm(vec_curr2) > 1:
        cos_t2 = np.dot(vec_hist2, vec_curr2) / (np.linalg.norm(vec_hist2) * np.linalg.norm(vec_curr2))
        angle_diff2 = np.arccos(np.clip(cos_t2, -1.0, 1.0)) * (180 / np.pi)
        angle_score = max(angle_score, angle_diff2 / 45.0)

    # Se"""
content = content.replace(old_logic, new_logic)

content = content.replace("weights = [0.1, 0.1, 0.1, 0.3, 0.4]", "weights = [0.1, 0.1, 0.1, 0.2, 0.3, 0.2]")
content = content.replace("signals = [iou, distance_score, vel_score, iou_persistence, speed_drop_score]", "signals = [iou, distance_score, vel_score, iou_persistence, speed_drop_score, min(1.0, angle_score)]")

# Fix return in detect_collision_advanced
old_ret_adv = "    return is_collision, collision_score"
new_ret_adv = """    severity = "Leve"
    try:
        max_drop_val = max_drop
    except NameError:
        max_drop_val = 0.0
        
    if max_drop_val > 0.7 or angle_score > 0.8:
        severity = "Severo"
    elif max_drop_val > 0.4 or angle_score > 0.4:
        severity = "Moderado"
        
    return is_collision, collision_score, severity"""
content = content.replace(old_ret_adv, new_ret_adv)

# Initialize max_drop so it exists
content = content.replace("speed_drop_score = 0.0\n    if speed1_hist > 1.0", "speed_drop_score = 0.0\n    max_drop = 0.0\n    if speed1_hist > 1.0")

# 4. detect_single_vehicle_crash
content = content.replace("    if len(track.boxes) < 2:\n        return False, 0.0\n", "    if len(track.boxes) < 2:\n        return False, 0.0, \"\"\n")
content = content.replace("    return False, 0.0\n", "    return False, 0.0, \"\"\n")
content = content.replace("            return True, min(1.0, drop)", "            severity = \"Severo\" if drop > 0.8 else \"Moderado\"\n            return True, min(1.0, drop), severity")

# 5. analyze_collisions
content = content.replace("t.age >= min_age", "t.age >= min_age and t.frames_since_update == 0")
content = content.replace("is_crash, conf = detect_single_vehicle_crash(track)", "is_crash, conf, severity = detect_single_vehicle_crash(track)")
content = content.replace("collisions.append((tid, tid, frame_num, conf))", "collisions.append((tid, tid, frame_num, conf, severity))")
content = content.replace("is_collision, confidence = detect_collision_advanced(track1, track2)", "is_collision, confidence, severity = detect_collision_advanced(track1, track2)")
content = content.replace("collisions.append((tid1, tid2, frame_num, confidence))", "collisions.append((tid1, tid2, frame_num, confidence, severity))")

with open('collision_logic.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Patched collision_logic.py")
