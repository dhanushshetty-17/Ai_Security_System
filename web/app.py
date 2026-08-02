from fastapi import FastAPI, Request, Form, Depends, HTTPException, Response
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
from typing import Optional
import json

from .auth import VALID_USERNAME, VALID_PASSWORD, create_access_token, get_current_user, get_current_user_optional
from .streamer import generate_mjpeg_stream
from security_ai_system.cameras.camera_manager import CameraManager, CameraSourceConfig, infer_source_type
from dotenv import set_key
import os
import psutil
from dataclasses import replace

app = FastAPI(title="AI Security Web Dashboard")

# Settings helpers
SETTINGS_FILE = Path(__file__).resolve().parent.parent / "outputs" / "settings.json"

def load_settings():
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "alarm_enabled": True,
        "bag_enabled": True,
        "bag_conf": 50,
        "weapon_enabled": True,
        "weapon_conf": 50,
        "behavior_enabled": True,
        "behavior_conf": 50,
        "audio_enabled": True,
        "audio_conf": 35,
        "gemini_api_key": ""
    }

def save_settings(settings):
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f)

# Setup directories
WEB_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = WEB_ROOT.parent

app.mount("/static", StaticFiles(directory=WEB_ROOT / "static"), name="static")

# Mount snapshots for web UI access
snapshots_dir = PROJECT_ROOT / "outputs" / "snapshots"
snapshots_dir.mkdir(parents=True, exist_ok=True)
app.mount("/snapshots", StaticFiles(directory=snapshots_dir), name="snapshots")

templates = Jinja2Templates(directory=WEB_ROOT / "templates")

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Redirect to dashboard, which will redirect to login if not authenticated."""
    return RedirectResponse(url="/dashboard", status_code=303)

@app.on_event("startup")
async def startup_event():
    app.state.settings = load_settings()

@app.get("/settings", response_class=HTMLResponse)
async def get_settings(request: Request, username: Optional[str] = Depends(get_current_user_optional)):
    if not username:
        return RedirectResponse(url="/login", status_code=303)
        
    api_key = os.getenv("GEMINI_API_KEY", app.state.settings.get("gemini_api_key", ""))
    app.state.settings["gemini_api_key"] = api_key
    
    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context={"username": username, "settings": app.state.settings, "success": request.query_params.get("success")}
    )

@app.post("/settings")
async def post_settings(request: Request, username: str = Depends(get_current_user)):
    form = await request.form()
    
    settings = app.state.settings
    settings["gemini_api_key"] = form.get("gemini_api_key", "")
    settings["alarm_enabled"] = form.get("alarm_enabled") == "on"
    settings["bag_enabled"] = form.get("bag_enabled") == "on"
    settings["bag_conf"] = int(form.get("bag_conf", 50))
    settings["weapon_enabled"] = form.get("weapon_enabled") == "on"
    settings["weapon_conf"] = int(form.get("weapon_conf", 50))
    settings["behavior_enabled"] = form.get("behavior_enabled") == "on"
    settings["behavior_conf"] = int(form.get("behavior_conf", 50))
    settings["audio_enabled"] = form.get("audio_enabled") == "on"
    settings["audio_conf"] = int(form.get("audio_conf", 35))
    
    save_settings(settings)
    
    if settings["gemini_api_key"]:
        env_path = Path(request.app.state.project_root) / ".env"
        if not env_path.exists(): env_path.touch()
        set_key(str(env_path), "GEMINI_API_KEY", settings["gemini_api_key"])
        os.environ["GEMINI_API_KEY"] = settings["gemini_api_key"]
        
    # Dynamically update the pipeline by turning models on or off
    manager: CameraManager = request.app.state.camera_manager
    for worker in manager.workers():
        new_detectors = []
        for det in worker._all_detectors: # Assuming we store all in _all_detectors
            name = type(det).__name__
            if name in ("BagDetector", "SuspiciousBagDetector") and settings["bag_enabled"]:
                det.runtime = replace(det.runtime, confidence_threshold=settings["bag_conf"] / 100.0)
                new_detectors.append(det)
            elif name == "WeaponDetector" and settings["weapon_enabled"]:
                det.runtime = replace(det.runtime, confidence_threshold=settings["weapon_conf"] / 100.0)
                new_detectors.append(det)
            elif name == "BehaviorDetector" and settings["behavior_enabled"]:
                det.runtime = replace(det.runtime, confidence_threshold=settings["behavior_conf"] / 100.0)
                new_detectors.append(det)
        worker.detectors = new_detectors
        
    # Update system alarm state and audio detector dynamically
    alert_mgr = getattr(request.app.state, "alert_manager", None)
    if alert_mgr:
        alert_mgr.config = replace(alert_mgr.config, alarm_enabled=settings["alarm_enabled"])

    audio_det = getattr(request.app.state, "audio_detector", None)
    if audio_det:
        audio_det.classifier.config = replace(
            audio_det.classifier.config, 
            confidence_threshold=settings["audio_conf"] / 100.0
        )

    return RedirectResponse(url="/settings?success=1", status_code=303)

@app.post("/api/add_source")
async def add_source(request: Request, source: str = Form(...), username: str = Depends(get_current_user)):
    manager: CameraManager = request.app.state.camera_manager
    # Generate new camera ID
    cam_count = len(manager.workers())
    camera_id = f"camera-{cam_count + 1}"
    
    parsed_source = int(source) if str(source).isdigit() else source
    
    # We need to import the detectors and configure them just like in build_basic_camera_manager
    from security_ai_system.detectors.bag_detector import BagDetector
    from security_ai_system.detectors.weapon_detector import WeaponDetector, WeaponDetectorConfig
    from security_ai_system.detectors.behavior_detector import BehaviorDetector, BehaviorDetectorConfig
    from security_ai_system.trackers.tracker import DeepSortTracker
    from security_ai_system.utils.reid_manager import GlobalReIDManager
    from security_ai_system.utils.types import ModelPathConfig
    
    # Simple hack: create a new tracker (or we could share the reid_manager if we stored it in app.state, 
    # but for simplicity we'll just create a fresh one)
    reid_manager = GlobalReIDManager(similarity_threshold=0.75)
    tracker = DeepSortTracker(reid_manager=reid_manager)
    
    bag_detector = BagDetector(camera_id=camera_id, tracker=tracker)
    
    behavior_config = BehaviorDetectorConfig(
        model_paths=ModelPathConfig(yolo_pose_weights=Path("models/yolov8m-pose.pt"))
    )
    behavior_detector = BehaviorDetector(camera_id=camera_id, config=behavior_config)
    
    weapon_detector_config = WeaponDetectorConfig(
        model_paths=ModelPathConfig(yolo_weapon_weights=Path("models/yolov8m.pt"))
    )
    weapon_detector = WeaponDetector(camera_id=camera_id, config=weapon_detector_config)
    
    config = CameraSourceConfig(
        camera_id=camera_id,
        source=parsed_source,
        source_type=infer_source_type(parsed_source),
        display_name=f"Camera {cam_count + 1}",
        target_fps=20.0,
    )
    
    worker = manager.add_camera(config, detectors=[bag_detector, weapon_detector, behavior_detector])
    worker._all_detectors = [bag_detector, weapon_detector, behavior_detector]
    worker.start()
    
    return RedirectResponse(url="/dashboard", status_code=303)

@app.get("/login", response_class=HTMLResponse)
async def get_login(request: Request):
    """Serve the login page."""
    return templates.TemplateResponse(request=request, name="login.html")

@app.post("/login")
async def post_login(username: str = Form(...), password: str = Form(...)):
    """Handle login form submission."""
    if username == VALID_USERNAME and password == VALID_PASSWORD:
        token = create_access_token(data={"sub": username})
        response = RedirectResponse(url="/dashboard", status_code=303)
        response.set_cookie(key="session_token", value=token, httponly=True, max_age=86400)
        return response
    
    # Simple error fallback for demo
    return RedirectResponse(url="/login?error=1", status_code=303)

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("session_token")
    return response

@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard(request: Request, username: Optional[str] = Depends(get_current_user_optional)):
    """Serve the main dashboard page."""
    if not username:
        return RedirectResponse(url="/login", status_code=303)
        
    # We will get the camera manager from app.state
    manager: CameraManager = request.app.state.camera_manager
    cameras = [w.config.camera_id for w in manager.workers()]
    
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "username": username,
            "cameras": cameras
        }
    )

@app.get("/video_feed/{camera_id}")
async def video_feed(request: Request, camera_id: str, username: str = Depends(get_current_user)):
    """Stream MJPEG video for a specific camera."""
    manager: CameraManager = request.app.state.camera_manager
    return StreamingResponse(
        generate_mjpeg_stream(camera_id, manager, request),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@app.get("/api/events")
async def get_events(request: Request, username: str = Depends(get_current_user)):
    """Return latest threats and overall system status."""
    manager: CameraManager = request.app.state.camera_manager
    
    # We'll just read from the logs/threats.jsonl (simplest way to get historical alerts)
    # Or for real-time, just return current statuses. Let's return camera statuses.
    statuses = manager.statuses()
    
    # Parse the threat JSONL file to get the last 10 events
    events = []
    log_file = Path(request.app.state.project_root) / "outputs" / "logs" / "threat_events.jsonl"
    if log_file.exists():
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in reversed(lines[-20:]):  # Get last 20 and reverse them
                    events.append(json.loads(line.strip()))
        except Exception:
            pass

    alert_mgr = getattr(request.app.state, "alert_manager", None)
    current_level = alert_mgr.threat_engine.current_state().level.value if alert_mgr else "LOW"

    return JSONResponse(content={
        "sys_health": {
            "cpu": psutil.cpu_percent(interval=None),
            "ram": psutil.virtual_memory().percent
        },
        "current_threat_level": current_level,
        "statuses": [{"camera_id": s.camera_id, "fps": round(s.fps, 1), "connected": s.connected} for s in statuses],
        "events": events[:10]  # top 10 latest
    })

@app.get("/api/reports")
async def get_reports(request: Request, username: str = Depends(get_current_user)):
    """Return all generated AI incident reports."""
    return JSONResponse(content=_load_reports(request.app.state.project_root))

@app.get("/api/search")
async def search_reports(request: Request, query: str, username: str = Depends(get_current_user)):
    """Search AI reports for a specific text query."""
    reports = _load_reports(request.app.state.project_root)
    query = query.lower()
    
    results = [
        r for r in reports 
        if query in r.get("ai_summary", "").lower() or query in r.get("threat_label", "").lower()
    ]
    return JSONResponse(content=results)

def _load_reports(project_root: str) -> list[dict]:
    reports_dir = Path(project_root) / "outputs" / "reports"
    reports = []
    if not reports_dir.exists():
        return reports
        
    for report_file in sorted(reports_dir.glob("*.json"), reverse=True):
        try:
            with open(report_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                
                # Convert absolute snapshot path to web URL
                img_path = data.get("image_path", "")
                if img_path:
                    filename = Path(img_path).name
                    data["image_url"] = f"/snapshots/{filename}"
                
                reports.append(data)
        except Exception:
            pass
            
    return reports
