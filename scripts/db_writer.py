import datetime
import os
import sys
import time
import subprocess
from ntixl2 import xl2parser

import sqlalchemy
from sqlalchemy import *
import json
from operator import eq

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.sql.expression import cast

Base = declarative_base()
log_path = os.path.realpath(__file__)
log_path = str(log_path).replace('.py', '.txt')
record_path = os.path.dirname(os.path.realpath(__file__))+'/processed_datasets.txt'
credentials_path = os.path.dirname(os.path.realpath(__file__))+'/credentials.secret'

with open(credentials_path) as secrets:
    print(credentials_path)
    log_directory = json.load(secrets)['path']


def get_processed():
    with open(record_path,'a+') as processed:
        processed.seek(0, 0)
        return str(processed.read())


def add_processed(d):
    with open(record_path, 'a+') as record:
        record.write(d + '\n')


class Setup(Base):
    __tablename__ = 'setups'

    id = Column(Integer, primary_key=True)
    device_info = Column(String(50))
    mic_type = Column(String(100))
    mic_sensitivity_mV_per_Pa = Column(DECIMAL(3, 1))
    profile = Column(String(10))
    log_interval = Column(String(10))
    range = Column(JSON)
    def __repr__(self):
        return "<{} {}>".format(self.id, self.mic_sensitivity_mV_per_Pa)


class BatchInfo(Base):
    __tablename__ = 'batchinfos'

    id = Column(Integer, primary_key=True)
    start = Column(TIMESTAMP)
    end = Column(TIMESTAMP)
    wav_file = Column(String(300))


class SpectrumSample(Base):
    __tablename__ = 'spectra'

    id = Column(Integer, primary_key=True)
    timestamp = Column(TIMESTAMP, unique=True)
    band_hz = Column(JSON)
    spectrum_LZeq_dt_f_dB = Column(JSON)
    setup_id = Column(Integer, ForeignKey('setups.id'))
    setup = relationship("Setup")
    batchinfos_id = Column(Integer, ForeignKey('batchinfos.id'))
    batch = relationship("BatchInfo")

    def __repr__(self):
        return "<Timestamp: {} SPECTRUM>".format(self.timestamp)


class LevelSample(Base):
    __tablename__ = 'levels'

    id = Column(Integer, primary_key=True)
    timestamp = Column(TIMESTAMP, unique=True)
    LAeq_dB = Column(DECIMAL(3, 1))
    LAeq_dt_dB = Column(DECIMAL(3, 1))
    LZeq_dB = Column(DECIMAL(3, 1))
    LZeq_dt_dB = Column(DECIMAL(3, 1))
    LZFmin_dt_dB = Column(DECIMAL(3, 1))
    LZFmax_dt_dB = Column(DECIMAL(3, 1))
    setup_id = Column(Integer, ForeignKey('setups.id'))
    setup = relationship("Setup")
    batchinfos_id = Column(Integer, ForeignKey('batchinfos.id'))
    batch = relationship("BatchInfo")

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

# get maximum 1 match if entry exists in DB
    def query_setups(self, s):
        session = self.Session()
        q = session.query(Setup).filter(Setup.device_info == s.device_info).filter(Setup.mic_type == s.mic_type)\
            .filter(Setup.profile == s.profile)\
            .filter(Setup.log_interval == s.log_interval)\
            .filter(Setup.mic_sensitivity_mV_per_Pa == s.mic_sensitivity_mV_per_Pa)\
            .all()  # problem
        results = [res for res in q if False not in list(map(eq,res.range,s.range))]
        if len(results) > 0:
            q = results[0]
        else:
            q = None
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
    if len(paths) < 2:
        pass
    for i in range(0,len(paths) // 2):
        if directory + str(i) in get_processed():
            print("skipping directory")
            continue
        try:
            level_filename = [f for f in [file for file in next(os.walk(directory))[2]] if '123_Log.txt' in f][i]
            audio_filename = level_filename.replace('123_Log.txt','Audio_FS130.3dB(PK)_00.wav')
            print(audio_filename)
            write_to_file_timestamped("working on {}, filebatch #{}".format(directory, i))

            level_path = [path for path in paths if '123_Log.txt' in path][i]
            spectrum_path = [path for path in paths if '3rd_Log.txt' in path][i]

            level_dict = xl2parser.parse_broadband_file(level_path)
            spectrum_dict = xl2parser.parse_spectrum_file(spectrum_path)

            level_samples = []
            spectrum_samples = []
            time_dict = level_dict['Time']
            hw_dict = level_dict['Hardware Configuration']
            measurement_dict = level_dict['Measurement Setup']

            batch_info = BatchInfo(start=time_dict['Start'],end=time_dict['End'],wav_file=audio_filename)
            db.store([batch_info])
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
                                           LZFmin_dt_dB=sample['LZFmin_dt [dB]'],LZFmax_dt_dB=sample['LZFmax_dt [dB]'],
                                           setup=setup,batch=batch_info)
                level_samples.append(level_sample)

            for sample in spectrum_dict['RTA LOG Results LZeq_dt']:
                spectrum_sample = SpectrumSample(timestamp=sample['Timestamp'],band_hz=sample['Spectrum_Frequencies [Hz]'],
                                                 spectrum_LZeq_dt_f_dB=sample['Spectrum_LZeq_dt_f [dB]'], setup=setup,
                                                 batch=batch_info)
                spectrum_samples.append(spectrum_sample)

            samples = []
            samples.extend(spectrum_samples)
            samples.extend(level_samples)
            db.store(samples)

            add_processed(directory + str(i))
        except IntegrityError:
            write_to_file_timestamped("This dataset has already been inserted. Skipping folder...")

#except Exception as e:
#    write_to_file_timestamped(str(e))



