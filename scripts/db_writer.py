import datetime
import os
import sys
import time
import subprocess
from ntixl2 import xl2parser

import sqlalchemy
from sqlalchemy import *
import json

from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
log_path = os.path.realpath(__file__)
log_path = str(log_path).replace('.py', '.txt')


with open('credentials.secret') as secrets:
    log_directory = json.load(secrets)['path']


class Setup(Base):
    __tablename__ = 'setups'

    id = Column(Integer, primary_key=True)
    device_info = Column(String(50))
    mic_type = Column(String(100))
    mic_sensitivity_mV_per_Pa = Column(Float)
    profile = Column(String(10))
    log_interval = Column(String(10))
    range = Column(JSON)
    def __repr__(self):
        return "<{} {}>".format(self.id, self.mic_sensitivity_mV_per_Pa)

class LevelSample(Base):
    __tablename__ = 'levels'

    id = Column(Integer, primary_key=True)
    timestamp = Column(TIMESTAMP)
    LAeq_dB = Column(Float)
    LAeq_dt_dB = Column(Float)
    LZeq_dB = Column(Float)
    LZeq_dt_dB = Column(Float)
    LZFmin_dt_dB = Column(Float)
    LZFmax_dt_dB = Column(Float)
    setup_id = Column(Integer, ForeignKey('setups.id'))
    setup = relationship("Setup")

    def __repr__(self):
        return "<Timestamp: {}, LAeq [dB]: {}, LAeq_dt [dB]: {}, LZeq [dB]: {}, LZeq_dt [dB]: {}, LZFmin_dt [dB]: {}, " \
               "LZFmax_dt [dB]: {} >".format(self.timestamp, self.LAeq_dB, self.LAeq_dt_dB, self.LZeq_dB,
                                             self.LZeq_dt_dB, self.LZFmin_dt_dB, self.LZFmax_dt_dB)


class DBConnector:
    def __init__(self):
        with open('credentials.secret') as secrets:
            credentials = json.load(secrets)
        db_engine = create_engine("mysql://{}:{}@127.0.0.1:3333/{}".format(credentials['user'],
                                                                           credentials['password'],
                                                                           credentials['database']))
        Base.metadata.create_all(bind=db_engine)
        self.Session = sessionmaker(bind=db_engine)

    # takes a list of mapped objects and commits to db
    def store(self, list):
        session = self.Session()
        session.add_all(list)
        session.commit()

    def query_setups(self, setup):
        session = self.Session()
        print("input "+ str(setup))
        q = session.query(Setup).first()
        print(q)
        return q


def write_to_file_timestamped(msg):
    print(msg)
    with open(log_path, "a") as logfile:
        logfile.write(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        logfile.write(' {0}\n'.format(msg))

#try:
db = DBConnector()
print(db)
print(os.walk(log_directory))

directories = [os.path.join(log_directory, directory) for directory in next(os.walk(log_directory))[1] if "PROCESSED" not in directory]


for directory in directories:
    paths = [os.path.join(directory, file) for file in next(os.walk(directory))[2]]
    write_to_file_timestamped("working on {}".format(directory))
    if len(paths) < 2:
        # TODO: rename to something like EMPTY_PROCESSED
        pass
    level_path = [path for path in paths if '123_Log.txt' in path][0]
    spectrum_path = [path for path in paths if '3rd_Log.txt' in path][0]

    level_dict = xl2parser.parse_broadband_file(level_path)
    spectrum_dict = xl2parser.parse_spectrum_file(spectrum_path)

    level_samples = []
    hw_dict = level_dict['Hardware Configuration']
    measurement_dict = level_dict['Measurement Setup']
    setup = Setup(device_info=hw_dict['Device Info'],mic_type=hw_dict['Mic Type'],
                  mic_sensitivity_mV_per_Pa=hw_dict['Mic Sensitivity [mV/Pa]'],
                  profile=measurement_dict['Profile'],log_interval=measurement_dict['Log-Interval'],
                  range=measurement_dict['Range [dB]'])

    existing = db.query_setups(setup)

    if existing is None:
        db.store([setup])
    else:
        setup = existing

    for sample in level_dict['Broadband LOG Results']:
        level_sample = LevelSample(timestamp=sample['Timestamp'],LAeq_dB=sample['LAeq [dB]'],
                                   LAeq_dt_dB=sample['LAeq_dt [dB]'],LZeq_dB=sample['LZeq [dB]'],
                                   LZeq_dt_dB=sample['LZeq_dt [dB]'],
                                   LZFmin_dt_dB=sample['LZFmin_dt [dB]'],LZFmax_dt_dB=sample['LZFmax_dt [dB]'],setup=setup)
        level_samples.append(level_sample)

    db.store(level_samples)

#except Exception as e:
#    write_to_file_timestamped(str(e))




