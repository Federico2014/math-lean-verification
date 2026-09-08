ARG BASE_IMAGE=lean-gate-tools
FROM ${BASE_IMAGE}
USER root
COPY environment.json /opt/environment/environment.json
COPY project /opt/environment/project
COPY prepare-environment.py /opt/environment/prepare-environment.py
RUN python3 /opt/environment/prepare-environment.py && chmod -R a-w /opt/environment
USER 10001:10001
WORKDIR /work
