import logging
import logging.handlers
from serial import Serial
import collections
import threading
#import click
import requests
import json
import sys
import time
from queue import Empty
import codecs
import datetime

API_BASE = "https://"
API_TOKEN = ""
SERIAL_DEVICE = "/dev/ttyACM0"
SYSLOG_DEFAULT_FACILITY = 'syslog'

ROOT_LOGGER = logging.getLogger()
DEFAULT_SYSLOG = logging.getLogger("DEFAULT")
DATA_LOGGER = logging.getLogger("data_logger")

DEFAULT_SYSLOG_handler = logging.handlers.SysLogHandler()
DEFAULT_SYSLOG.addHandler(DEFAULT_SYSLOG_handler)
syslog_handler = logging.handlers.SysLogHandler()
DATA_LOGGER.addHandler(syslog_handler)

def to_string(data):
    return codecs.decode(data)

def excepthook(type, value, traceback):
    ROOT_LOGGER.error("Unhandled error: '{}' '{}' '{}'".format(type, value, traceback))
    exit(1)

sys.excepthook = excepthook

class GeneralProcessor():
    def __init__(self, logger):
        self._logger = logger

    def __call__(self, data):
        return self._process(data)

    def _process(self, data):
        self._logger.debug("Starting processing ...")
        ret = self.process(data)
        self._logger.debug("Processing ended")
        return ret

    def process(self, data):
        return True

class SyslogProcessor(GeneralProcessor):
    def __init__(self, syslog_logger, logger=logging.getLogger()):
        self._syslog = syslog_logger
        super().__init__(logger)

    def process(self, data):
        self._syslog.info("{}".format(to_string(data)))
        return True

class RESTProcessor(GeneralProcessor):
    def __init__(self, api_url_base, api_token, logger=logging.getLogger()):
        self.api_url_base = api_url_base
        self.api_token = api_token
        super().__init__(logger)

    def process(self, data):
        api_url = '{0}v1/garden_sensors'.format(self.api_url_base)
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer {0}'.format(self.api_token)
        }
        try:
            data = to_string(data)
            try:
                json_payload = json.loads(data)
            except:
                self._logger.debug("json_loads failed for '{}'".format(data))
                json_payload = {"data": data, "err": "failed_conversion_json"}
        except:
            self._logger.debug("to_string failed for '{}'".format(data))
            json_payload = {"data": data, "err": "failed_conversion_text"}
            
        response = requests.post(api_url, headers=headers, json=json_payload)
        self._logger.debug("api_url={},data={}, response={}".format(api_url, json_payload, response))
        if response.status_code == 200:
            self._logger.info("Succesfully sended data to API.")
            return True
        return False

class SerialProcessor():

    def __init__(self, serial_instance, buff_size=4096, sleep_time=5, logger=logging.getLogger()):
        self._serial = serial_instance
        self._buff_size = buff_size
        self._buffer_ready_to_process = collections.deque()
        self.reading_thread = None
        self._logger = logger
        self._processors = []
        self._failed_to_process = []
        self._sleep_time = sleep_time
        self.running = True

    def read_log(self):
        #no lock is required
        while self.running:
            ret_bytes = self._serial.read_until(size=self._buff_size)
            #print(ret_bytes)
            self._buffer_ready_to_process.append(ret_bytes)
            time.sleep(self._sleep_time)

    def thread_reader_stop(self):
        self.running = False
        if self.reading_thread:
            self.reading_thread.join()
    
    def thread_reader_start(self):
        if self.running and self.reading_thread:
            return False
        self.reading_thread = threading.Thread(target=self.read_log)
        self.running = True
        self.reading_thread.start()
        return True

    def addProcessor(self, processor):
        if processor not in self._processors:
            self._processors.append(processor)

    def process(self):
        q_el = None
        with open("data.log", "a") as f:
            while self.running:
                try:
                    if len(self._buffer_ready_to_process) > 0:
                        q_el = self._buffer_ready_to_process.popleft()
                        for processor in self._processors:
                            el_str = to_string(q_el)
                            # obj_data = json.loads(el_str, strict=False)
                            # obj_data['time'] = time.time()
                            # print(el_str)
                            f.write(str(datetime.datetime.now()))
                            f.write(" ")
                            f.write(el_str)
                            f.flush()
                            #f.write("\n")
                            #DEFAULT_SYSLOG.info(el_str)
                            #processor(q_el)
                except Exception as e:
                    self._logger.error(e, exc_info=True)
                    self._failed_to_process.append(q_el)
                time.sleep(0.05)

    def __del__(self):
        self.thread_reader_stop()

if __name__ == "__main__":
    s = Serial(port=SERIAL_DEVICE)
    sp = SerialProcessor(s)
    sp.addProcessor(SyslogProcessor(DATA_LOGGER, ROOT_LOGGER))
    #sp.addProcessor(RESTProcessor(API_BASE, API_TOKEN, ROOT_LOGGER))
    sp.thread_reader_start()
    sp.process()
