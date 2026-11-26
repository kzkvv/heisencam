"""Verify the archived installation's HTTP and MQTT behavior without a camera."""
from types import SimpleNamespace
from unittest.mock import Mock, patch

from flask import Flask

from frigate.comms.dispatcher import Dispatcher
from frigate.http import config_raw, config_save
from frigate.version import VERSION

assert VERSION.startswith("0.12.1-367d724"), VERSION
app = Flask(__name__)
with app.test_request_context("/config/raw"):
    assert config_raw() == ("This feature is disabled", 200)
with app.test_request_context("/config/save", method="POST", data="invalid"):
    assert config_save() == ("This feature is disabled", 200)
camera = SimpleNamespace(detect=SimpleNamespace(enabled=True), record=SimpleNamespace(enabled=True))
metrics = {key: SimpleNamespace(value=True) for key in ("detection_enabled", "motion_enabled")}
transport = Mock()
dispatcher = Dispatcher(SimpleNamespace(cameras={"demo": camera}), {"demo": metrics}, [transport])
dispatcher._receive("demo/detect/set", "OFF")
assert camera.detect.enabled and metrics["detection_enabled"].value
transport.publish.assert_called_with("demo/detect/state", "OFF", True)
dispatcher._receive("demo/recordings/set", "OFF")
assert camera.record.enabled
with patch("frigate.comms.dispatcher.restart_frigate") as restart:
    dispatcher._receive("restart", "")
    restart.assert_not_called()
print("Verified legacy version, blocked raw config and config writes, restart, detection and recording.")
