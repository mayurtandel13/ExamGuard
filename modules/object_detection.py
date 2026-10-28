"""
YOLOv8 Mobile Phone and Multi-Person Detection Module wrapper
Re-exports YOLOObjectDetector from yolo package.
"""

from yolo.detector import YOLOObjectDetector

__all__ = ["YOLOObjectDetector"]
