# -*- coding: UTF-8 -*-


class MonitorConfig:
    """Configuration for monitoring different asset types"""
    def __init__(
            self,
            asset_type,
            subject_prefix,
            snapshot_file="snapshot.json",
            notification_days=1,
            low_threshold=-500,
            high_threshold=1000,
            drawdown_threshold=0.2,
            daily_change_threshold=0.1
    ):
        self.asset_type = asset_type  # e.g. 'stock' or 'crypto'
        self.snapshot_file = snapshot_file
        self.subject_prefix = subject_prefix
        self.notification_days = notification_days
        self.low_threshold = low_threshold
        self.high_threshold = high_threshold
        self.drawdown_threshold = drawdown_threshold
        self.daily_change_threshold = daily_change_threshold  # abs pct change vs previous close to trigger
