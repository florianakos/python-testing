class DataDogStatsDHelper:
    """
        Class that captures values submitted via fake statsd handler to DataDog
    """
    event_title = None
    event_text = None
    event_alert_type = None
    event_tags = None
    event_counter = 0
    gauge_metric_name = None
    gauge_metric_value = None
    gauge_tags = None
    gauge_counter = 0

    def event(self, title, text, alert_type=None, aggregation_key=None, source_type_name=None,
              date_happened=None, priority=None, tags=None, hostname=None):
        """ Fake method with identical signature to datadog.statsd.event() """

        self.event_title = title
        self.event_text = text
        self.event_alert_type = alert_type
        self.event_tags = tags
        self.event_counter += 1

    def gauge(self, metric, value, tags=None, sample_rate=None):
        """ Fake method with identical signature to datadog.statsd.gauge() """

        self.gauge_metric_name = metric
        self.gauge_metric_value = value
        self.gauge_tags = tags
        self.gauge_counter += 1

    def reset(self):
        self.event_title = None
        self.event_text = None
        self.event_alert_type = None
        self.event_tags = None
        self.event_counter = 0
        self.gauge_metric_name = None
        self.gauge_metric_value = None
        self.gauge_tags = None
        self.gauge_counter = 0

