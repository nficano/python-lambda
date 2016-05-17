# -*- coding: utf-8 -*-

class MockContext(object):
    def __init__(self, context):
        self.function_name = 'Mock'
        self.function_version = 'm1'
        self.memory_limit_in_mb = '500'
        self.aws_request_id = None
        self.log_groupd_name = None
        self.log_stream_name = None
        self.identiy = FakeObject()
        self.client_context = ClientContext(context)

    def get_remaining_time_in_millis(self):
        # Returns the remaining execution time, in milliseconds, until
        # AWS Lambda terminates the function.
        return 0


class FakeObject(object):
    def __init__(self, context=None):
        self._context = context or {} # if None was passed

    def __getattr__(self, attr):
        return self._context.get(attr, None)


class ClientContext(object):
    def __init__(self, context):
        self.custom = FakeObject(context)
        self.client = FakeObject()
        self.env = {}
