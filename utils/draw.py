"""
HUD Drawer Utilities Module
Renders bounding boxes, 3D pose vectors, and HUD status overlays on OpenCV video frames.
"""


class HUDDrawer:
    """
    Modular Frame HUD Drawing interface.
    """

    @staticmethod
    def draw_head_pose(frame, head_telemetry):
        """Draws 3D head pose orientation vectors."""
        return frame

    @staticmethod
    def draw_detections(frame, yolo_telemetry):
        """Draws bounding boxes for detected phones and persons."""
        return frame

    @staticmethod
    def draw_risk_banner(frame, fusion_result):
        """Draws top HUD risk status banner."""
        return frame
