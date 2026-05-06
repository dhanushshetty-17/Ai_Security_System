import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import threading

from security_ai_system.cameras.camera_manager import CameraManager, CameraSourceConfig
from security_ai_system.detectors.bag_detector import BagDetector
from security_ai_system.detectors.weapon_detector import WeaponDetector, WeaponDetectorConfig
from security_ai_system.audio.yamnet_classifier import YamNetClassifierConfig
from security_ai_system.detectors.audio_detector import AudioThreatDetector, AudioThreatDetectorConfig
from security_ai_system.audio.audio_sources import MicrophoneAudioStream
from security_ai_system.alerts.alert_manager import AlertManager, AlertManagerConfig
from security_ai_system.ui.dashboard import run_dashboard
from security_ai_system.utils.types import ModelPathConfig, RuntimeConfig

def run_audio_capture(audio_detector, alert_manager):
    print("Starting audio capture from default microphone...")
    try:
        with MicrophoneAudioStream(chunk_seconds=1.0) as mic:
            while True:
                chunk = mic.read(timeout=2.0)
                if chunk is not None:
                    result = audio_detector.predict(chunk)
                    if result.alerts:
                        # Forward audio alerts to the common alert manager
                        events = alert_manager.handle_alerts(
                            result.alerts,
                            camera_id="microphone-1",
                            source="Audio"
                        )
                        if hasattr(alert_manager, "_audio_event_queue"):
                            alert_manager._audio_event_queue.extend(events)
    except Exception as e:
        print(f"Audio capture failed (no mic?): {e}")

def main():
    print("Initializing AI Surveillance System Demo...")
    
    alert_manager = AlertManager(config=AlertManagerConfig(alarm_enabled=True))
    alert_manager._audio_event_queue = []
    
    # Monkey-patch to inject background audio events into the dashboard refresh loop
    original_handle = alert_manager.handle_camera_result
    def patched_handle(result):
        events = original_handle(result)
        if alert_manager._audio_event_queue:
            events.extend(alert_manager._audio_event_queue)
            alert_manager._audio_event_queue.clear()
        return events
    alert_manager.handle_camera_result = patched_handle
    
    camera_manager = CameraManager()
    
    config = CameraSourceConfig(
        camera_id="webcam-1",
        source=0,
        display_name="Live Webcam",
        target_fps=20.0,
    )
    
    print("Loading vision detectors...")
    bag_detector = BagDetector(camera_id=config.camera_id)
    
    from security_ai_system.detectors.weapon_detector import DEFAULT_WEAPON_ALIASES
    aliases = DEFAULT_WEAPON_ALIASES.copy()
    aliases.update({
        "scissors": "knife",
        "fork": "knife",
        "spoon": "knife",
        "cell phone": "knife",
        "toothbrush": "knife"
    })
    
    # We map yolo_weapon_weights to the base yolov8n.pt to use its built-in 'knife' class for the demo
    weapon_config = WeaponDetectorConfig(
        model_paths=ModelPathConfig(yolo_weapon_weights=Path("models/yolov8n.pt")),
        class_aliases=aliases
    )
    weapon_runtime = RuntimeConfig(confidence_threshold=0.15) # Very sensitive for demo
    weapon_detector = WeaponDetector(camera_id=config.camera_id, runtime=weapon_runtime, config=weapon_config)
    
    camera_manager.add_camera(
        config=config,
        detectors=[bag_detector, weapon_detector]
    )
    
    print("Loading audio detector...")
    audio_config = AudioThreatDetectorConfig(
        classifier_config=YamNetClassifierConfig(confidence_threshold=0.10)
    )
    audio_detector = AudioThreatDetector(camera_id="microphone-1", config=audio_config)
    audio_detector.load()
    
    # Start audio thread
    audio_thread = threading.Thread(
        target=run_audio_capture,
        args=(audio_detector, alert_manager),
        daemon=True
    )
    audio_thread.start()
    
    print("Opening Dashboard... (Look for the PyQt5 window)")
    print("Point webcam at a bag, human, or knife.")
    print("Scream into the microphone for audio threat detection.")
    return run_dashboard(camera_manager, alert_manager=alert_manager)

if __name__ == "__main__":
    sys.exit(main())
