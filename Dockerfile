FROM ubuntu:latest

ENV DEBIAN_FRONTEND noninteractive

ADD https://bootstrap.pypa.io/get-pip.py /tmp/get-pip.py
ADD . /tmp/mteor

RUN set -e \
      && ln -sf bash /bin/sh \
      && ln -s python3.8 /usr/bin/python3 \
      && ln -s python3 /usr/bin/python

RUN set -e \
      && apt-get -y update \
      && apt-get -y dist-upgrade \
      && apt-get -y install --no-install-recommends --no-install-suggests \
        apt-transport-https ca-certificates curl python3.8 \
        python3.8-distutils wine-development winetricks \
      && apt-get -y autoremove \
      && apt-get clean \
      && rm -rf /var/lib/apt/lists/*

RUN set -e \
      && winetricks cjkfonts

RUN set -e \
      && curl -SL -o /tmp/mt5setup.exe \
        https://download.mql5.com/cdn/web/metaquotes.software.corp/mt5/mt5setup.exe \
      && /usr/bin/wine mt5setup.exe

ENTRYPOINT [ "/usr/bin/wine" ]
CMD [ "/opt/MetaTrader/terminal64.exe", "/portable" ]

# RUN set -e \
#       && /usr/bin/python3 /tmp/get-pip.py \
#       && pip install -U --no-cache-dir pip /tmp/mteor \
#       && rm -rf /tmp/mteor /tmp/get-pip.py
#
# ENTRYPOINT ["/usr/local/bin/mteor"]
