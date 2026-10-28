"""
Data Logging Module wrapper for session recording, DataFrame generation, and export capabilities.
Connects to centralized BehavioralTimeline.
"""

from timeline.timeline import BehavioralTimeline


class SessionDataLogger:
    """
    Data Logging Engine integrated with Phase 8 Behavioral Timeline.
    """

    def __init__(self):
        self.timeline = BehavioralTimeline()

    @property
    def session_start_time(self):
        return self.timeline.session_start_time

    @property
    def timeseries_data(self):
        return self.timeline.risk_history

    @property
    def event_logs(self):
        return self.timeline.events

    def start_session(self, start_time=None):
        """Initializes a new recording session."""
        self.timeline.start_session(start_time=start_time)

    def log_frame(self, head_tel, gaze_tel, yolo_tel, kb_telemetry_or_events, fusion_res):
        """Logs single frame telemetry and fusion results."""
        return self.timeline.record_snapshot(
            head_telemetry=head_tel,
            gaze_telemetry=gaze_tel,
            yolo_telemetry=yolo_tel,
            kb_telemetry_or_events=kb_telemetry_or_events,
            fusion_result=fusion_res,
        )

    def get_timeseries_df(self):
        """Returns session time-series as Pandas DataFrame."""
        return self.timeline.get_risk_history_df()

    def get_events_df(self):
        """Returns logged events as Pandas DataFrame."""
        return self.timeline.get_events_df()

    def get_session_summary(self):
        """Computes aggregate metrics for post-exam summary report."""
        return self.timeline.get_session_summary()

    def export_to_csv(self, file_path_prefix=None):
        """Converts timeseries and events data to CSV strings."""
        return self.timeline.export_to_csv(file_path_prefix=file_path_prefix)
