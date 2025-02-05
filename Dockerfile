FROM rbrandstaedter/solarflow-control-baseimage:latest

# Create stdconfig directory
WORKDIR /

COPY src/solarflow-topic-mapper.py /

RUN pip3 install paho-mqtt==2.0.0
ENTRYPOINT ["python","solarflow-topic-mapper.py"]
