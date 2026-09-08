FROM rust:1.90.0-slim-bookworm@sha256:64232e656c058f4468e8d024e990acff04f0fd5a5c0a88a574dc37773d7325c9 AS nanoda
COPY debian.sources /etc/apt/sources.list.d/debian.sources
RUN apt-get -o Acquire::Retries=5 -o APT::Update::Error-Mode=any update && apt-get -o Acquire::Retries=5 install -y --no-install-recommends git ca-certificates && rm -rf /var/lib/apt/lists/*
RUN git clone https://github.com/ammkrn/nanoda_lib /build/nanoda && cd /build/nanoda && git checkout 05055695879dfebb6628a67da88ceca6cd6b0421 && cargo build --release --locked

FROM ubuntu:24.04@sha256:33ceb71981b602c1a7443a53469e4dba065f7503eab3078a2d7a57a2ab987517
COPY ubuntu-packages.lock /tmp/ubuntu-packages.lock
RUN apt-get -o Acquire::Retries=5 -o APT::Update::Error-Mode=any update && xargs -r apt-get -o Acquire::Retries=5 install -y --no-install-recommends < /tmp/ubuntu-packages.lock && dpkg-query -W -f='${binary:Package}=${Version}\n' | LC_ALL=C sort > /tmp/installed-packages.lock && diff -u /tmp/ubuntu-packages.lock /tmp/installed-packages.lock && rm -rf /var/lib/apt/lists/*
RUN curl --fail --location --retry 5 https://github.com/leanprover/lean4/releases/download/v4.34.0-rc2/lean-4.34.0-rc2-linux.tar.zst -o /tmp/lean.tar.zst && echo '3d011041203acacf300d343a39673f7d233743397993797c941346ae9e5df1a8  /tmp/lean.tar.zst' | sha256sum --check && mkdir /opt/lean && tar --zstd -xf /tmp/lean.tar.zst --strip-components=1 -C /opt/lean && rm /tmp/lean.tar.zst
ENV PATH="/opt/lean/bin:/opt/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
RUN git clone https://github.com/leanprover/comparator /opt/comparator && cd /opt/comparator && git checkout 2312244ac716564a61cc0bf4e107d9abf1757a61
COPY GateReplay.lean /opt/comparator/GateReplay.lean
COPY build-comparator.py /opt/build-comparator.py
RUN cd /opt/comparator && python3 /opt/build-comparator.py && lake build lean4export gate-replay && test "$(git -C .lake/packages/lean4export rev-parse HEAD)" = cacf989bd75f608700820f6afc595f32e7a99a4d && mkdir /opt/bin && cp .lake/build/bin/gate-replay /opt/bin/ && cp .lake/packages/lean4export/.lake/build/bin/lean4export /opt/bin/

COPY --from=nanoda /build/nanoda/target/release/nanoda_bin /opt/bin/nanoda_bin
COPY export.py probe.py toolchain.json /opt/gate/
RUN sha256sum /opt/bin/* /opt/lean/bin/lean > /opt/gate/binaries.sha256 && dpkg-query -W > /opt/gate/system-packages.txt
USER 10001:10001
WORKDIR /work
