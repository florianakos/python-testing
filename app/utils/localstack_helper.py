import localstack_client.session
import time

import socket
import pytest

class LocalStackHelper:

    def __init__(self):
        """ Wait for localstack to start, then init session with dummy credentials """
        self.wait_for_localstack()
        self.session = localstack_client.session.Session(aws_access_key_id="foo", aws_secret_access_key="bar")

    def get_sqs_client(self):
        """ return client for sqs """
        return self.session.client("sqs")

    def get_s3_client(self):
        """ return client for s3 """
        return self.session.client("s3")

    def wait_for_localstack(self):
        """ implement function that blocks until localstack is available or deadline passes """
        deadline = 0
        while not self.localstack_is_up("localstack", 4563):
            deadline += 1
            if deadline > 120:
                pytest.exit("Localstack initialization failed! Exiting ...")
            time.sleep(1)
        time.sleep(5)

    def localstack_is_up(self, host, port):
        """ checks if the localstack is available by trying to open a connection to it """
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((host, int(port)))
            s.shutdown(2)
            return True
        except socket.error:
            return False
