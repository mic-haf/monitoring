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

#TODO: change working directory
Base = declarative_base()
log_path = os.path.realpath(__file__)
log_path = str(log_path).replace('.py', '.txt')
record_path = os.path.dirname(os.path.realpath(__file__))+'/processed_datasets.txt'
credentials_path = os.path.dirname(os.path.realpath(__file__))+'/credentials.secret'
min_Lz = 0

with open(credentials_path) as secrets:
    print("credentials at:" + credentials_path)
    credentials = json.load(secrets)
    log_directory = credentials['path']
    min_Lz = credentials['min_LZeq_dt']


def get_processed():
    with open(record_path,'a+') as processed:
        processed.seek(0, 0)
        return str(processed.read())


def add_processed(d):
    with open(record_path, 'a+') as record:
        record.write(d + '\n')


class WeatherSample(Base):
    __tablename__ = 'weathersample'

    weathersample_id = Column(Integer, primary_key=True)
    timestamp = Column(TIMESTAMP)
    temperature = Column(DECIMAL(3,1))
    sunshine = Column(DECIMAL(3,1))
    precipitation = Column(DECIMAL(3.1))
    wind_direction = Column(SMALLINT)
    wind_speed = Column(DECIMAL(3,1))
    gust_peak = Column(DECIMAL(3,1))
    humidity = Column(SMALLINT)

    station = Column(JSON)


class Setup(Base):
    __tablename__ = 'setup'

    setup_id = Column(Integer, primary_key=True)
    device_info = Column(String(50))
    mic_type = Column(String(100))
    mic_sensitivity_mV_per_Pa = Column(DECIMAL(3, 1))
    profile = Column(String(10))
    log_interval = Column(String(10))
    range = Column(JSON)
    def __repr__(self):
        return "<{} {}>".format(self.id, self.mic_sensitivity_mV_per_Pa)


class BatchInfo(Base):
    __tablename__ = 'batchinfo'

    batchinfo_id = Column(Integer, primary_key=True)
    start = Column(TIMESTAMP)
    end = Column(TIMESTAMP)
    wav_file = Column(String(300))


class SpectrumSample(Base):
    __tablename__ = 'spectrum'

    spectrum_id = Column(Integer, primary_key=True)
    timestamp = Column(TIMESTAMP, unique=True)
    band_hz = Column(JSON)
    spectrum_LZeq_dt_f_dB = Column(JSON)
    setup_id = Column(Integer, ForeignKey('setup.setup_id'))
    setup = relationship("Setup", foreign_keys=[setup_id])

    batchinfo_id = Column(Integer, ForeignKey('batchinfo.batchinfo_id'))
    batch = relationship("BatchInfo", foreign_keys=[batchinfo_id])

    weathersample_id = Column(Integer, ForeignKey('weathersample.weathersample_id'))
    weather_sample = relationship("WeatherSample", foreign_keys=[weathersample_id])

    def __repr__(self):
        return "<Timestamp: {} SPECTRUM>".format(self.timestamp)


class LevelSample(Base):
    __tablename__ = 'level'

    level_id = Column(Integer, primary_key=True)
    timestamp = Column(TIMESTAMP, unique=True)
    LAeq_dB = Column(DECIMAL(3, 1))
    LAeq_dt_dB = Column(DECIMAL(3, 1))
    LZeq_dB = Column(DECIMAL(3, 1))
    LZeq_dt_dB = Column(DECIMAL(3, 1))
    LZFmin_dt_dB = Column(DECIMAL(3, 1))
    LZFmax_dt_dB = Column(DECIMAL(3, 1))
    setup_id = Column(Integer, ForeignKey('setup.setup_id'))
    setup = relationship("Setup", foreign_keys=[setup_id])

    batchinfo_id = Column(Integer, ForeignKey('batchinfo.batchinfo_id'))
    batch = relationship("BatchInfo", foreign_keys=[batchinfo_id])

    weathersample_id = Column(Integer, ForeignKey('weathersample.weathersample_id'))
    weather_sample = relationship("WeatherSample", foreign_keys=[weathersample_id])

    def __repr__(self):
        return "<Timestamp: {}, LAeq [dB]: {}, LAeq_dt [dB]: {}, LZeq [dB]: {}, LZeq_dt [dB]: {}, LZFmin_dt [dB]: {}, " \
               "LZFmax_dt [dB]: {} >".format(self.timestamp, self.LAeq_dB, self.LAeq_dt_dB, self.LZeq_dB,
                                             self.LZeq_dt_dB, self.LZFmin_dt_dB, self.LZFmax_dt_dB)


class DBConnector:
    q = None
    session = None

    def __init__(self):
        with open(credentials_path) as secrets:
            credentials = json.load(secrets)
        db_engine = create_engine("mysql://{}:{}@127.0.0.1:{}/{}".format(credentials['user'],
                                                                        credentials['password'],
                                                                        credentials['port'],
                                                                        credentials['database']))
        Base.metadata.create_all(bind=db_engine)
        self.Session = sessionmaker(bind=db_engine)

    # takes a list of mapped objects and commits to db
    def store(self, list):
        if self.session is None:
            self.session = self.Session()
        session = self.session
        session.add_all(list)
        session.commit()

# get maximum 1 match if entry exists in DB
    def query_setups(self, s):
        session = self.Session()
        q = session.query(Setup).filter(Setup.device_info == s.device_info).filter(Setup.mic_type == s.mic_type)\
            .filter(Setup.profile == s.profile)\
            .filter(Setup.log_interval == s.log_interval)\
            .filter(Setup.mic_sensitivity_mV_per_Pa == s.mic_sensitivity_mV_per_Pa)\
            .all()
        results = [res for res in q if False not in list(map(eq,res.range,s.range))]
        session.close()
        if len(results) > 0:
            q = results[0]
        else:
            q = None
        return q

    def refresh_weather(self):
        session = self.Session()
        self.q = list(session.query(WeatherSample).filter(WeatherSample.timestamp >
                                                          (datetime.datetime.now() - datetime.timedelta(weeks=1))).all())
        session.close()

    def get_weather(self, timestamp):
        if self.q is None:
            db.refresh_weather()
        q = self.q
        if len(q) is 0:
            return None

        closest_weather = q[0]
        closest_time = abs((timestamp - datetime.datetime(2000, 4, 4)).total_seconds())
        for weather in q:
            seconds = abs((timestamp - weather.timestamp).total_seconds())
            if seconds < closest_time:
                closest_weather = weather
                closest_time = seconds
        if closest_time > (60 * 60):
            closest_weather = None
        return closest_weather


def write_to_file_timestamped(msg):
    print(msg)
    with open(log_path, "a") as logfile:
        logfile.write(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        logfile.write(' {0}\n'.format(msg))


def evaluate_spectrum(sample):
    level_s = [lev for lev in level_samples if sample.timestamp == lev.timestamp]
    if level_s is None:
        return True
    LZ = level_s[0].LZeq_dt_dB
    return LZ > min_Lz


#try:
db = DBConnector()
print(db)
print(os.walk(log_directory))

directories = [os.path.join(log_directory, directory) for directory in next(os.walk(log_directory))[1] if "PROCESSED" not in directory]
if len(sys.argv) > 1:
    if sys.argv[1] == '-weather':
        import requests
        url = 'http://data.netcetera.com/smn/smn/REH'
        response = requests.get(url)
        if response.status_code is not 200:
            write_to_file_timestamped("ERROR: Weather could not be fetched")
            sys.exit()

        content = json.loads(response.content.decode('ISO-8859-1'))
        write_to_file_timestamped("Weather fetched")

        weather_sample = WeatherSample(station=content['station'], timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                       temperature=float(content['temperature']), sunshine=float(content['sunshine']),
                                       precipitation=float(content['precipitation']),
                                       wind_direction=float(content['windDirection']),
                                       wind_speed=float(content['windSpeed']), gust_peak=float(content['gustPeak']),
                                       humidity=float(content['humidity']))
        db.store([weather_sample])
        sys.exit()
    else:
        write_to_file_timestamped("Command not recognized")
        sys.exit()

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
                level_sample.weather_sample = db.get_weather(level_sample.timestamp)
                level_samples.append(level_sample)

            for sample in spectrum_dict['RTA LOG Results LZeq_dt']:
                spectrum_sample = SpectrumSample(timestamp=sample['Timestamp'],band_hz=sample['Spectrum_Frequencies [Hz]'],
                                                 spectrum_LZeq_dt_f_dB=sample['Spectrum_LZeq_dt_f [dB]'], setup=setup,
                                                 batch=batch_info)
                spectrum_sample.weather_sample = db.get_weather(spectrum_sample.timestamp)
                if evaluate_spectrum(spectrum_sample):
                    spectrum_samples.append(spectrum_sample)
                else:
                    print("dropping sample")

            samples = []
            samples.extend(spectrum_samples)
            samples.extend(level_samples)
            db.store(samples)

            add_processed(directory + str(i))
        except IntegrityError:
            write_to_file_timestamped("This dataset has already been inserted. Skipping folder...")

#except Exception as e:
#    write_to_file_timestamped(str(e))




