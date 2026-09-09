ARG BASE_IMAGE=lean-gate-tools
FROM ${BASE_IMAGE}
USER root
COPY environment.json /opt/environment/environment.json
COPY project /opt/environment/project
COPY prepare-environment.py /opt/environment/prepare-environment.py
COPY cache_guard.py /opt/environment/cache_guard.py
# Cache archives can contain owner-only trace files. Make public dependency
# inputs readable/traversable by the sandbox UID while keeping them immutable.
RUN python3 /opt/environment/prepare-environment.py && chmod -R a+rX,a-w /opt/environment
USER 10001:10001
WORKDIR /work
