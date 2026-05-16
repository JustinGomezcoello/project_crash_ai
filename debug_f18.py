import sys, os, cv2
sys.path.insert(0, '.')
from config import INPUT_DIR
from src.detector import VehicleDetector
from src.collision_logic import detect_dashcam_collision, set_frame_dimensions, reset_state, _track_lost_at

video_path = os.path.join(INPUT_DIR, 'ccd_crash_02.mp4')
cap = cv2.VideoCapture(video_path)
fw = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
fh = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
cap.release()
set_frame_dimensions(fw, fh)
reset_state()
detector = VehicleDetector()
cap = cv2.VideoCapture(video_path)
fn = 0
while True:
    ret, frame = cap.read()
    if not ret: break
    tracks = detector.process_frame(frame)
    if fn in [18, 19, 20, 21, 22]:
        if 36 in tracks:
            print(f'F{fn} TID 36 pre: missed={tracks[36].frames_since_update} lost_at={list(_track_lost_at.keys())}')
    cols = detect_dashcam_collision(tracks, fn)
    if fn in [18, 19, 20, 21, 22]:
        if 36 in tracks:
            print(f'F{fn} TID 36 post: lost_at={list(_track_lost_at.keys())}')
            if 36 in _track_lost_at:
                info = _track_lost_at[36]
                print(f'   -> info: frame={info["frame"]} growth={info.get("growth")}')
        if cols:
            print(f'F{fn} COLLISION: {cols}')
    fn += 1
cap.release()
