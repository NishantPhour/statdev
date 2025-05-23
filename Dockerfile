# Prepare the base environment.
#FROM ubuntu:20.04 as builder_base_docker
FROM ubuntu:24.04 as builder_base_docker
MAINTAINER asi@dbca.wa.gov.au
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Australia/Perth
ENV PRODUCTION_EMAIL=True
ENV SECRET_KEY="ThisisNotRealKey"
RUN apt-get clean
RUN apt-get update
RUN apt-get upgrade -y
RUN apt-get install --no-install-recommends -y gunicorn wget git libmagic-dev gcc binutils libproj-dev gdal-bin python3 python3-setuptools python3-dev python3-pip tzdata cron rsyslog rsyslog tzdata
#RUN apt-get install --no-install-recommends -y gunicorn wget git libmagic-dev gcc binutils libproj-dev gdal-bin python3-setuptools python3-dev python3-pip tzdata cron rsyslog rsyslog tzdata
RUN apt-get install --no-install-recommends -y libpq-dev patch
# RUN apt-get install --no-install-recommends -y postgresql-client mtr htop vim ssh
RUN apt-get install --no-install-recommends -y postgresql-client mtr htop vim virtualenv ssh
RUN apt-get install --no-install-recommends -y postfix syslog-ng syslog-ng-core
#RUN ln -s /usr/bin/python3 /usr/bin/python
#RUN ln -s /usr/bin/pip3 /usr/bin/pip
# RUN pip install --upgrade pip
# Install Python libs from requirements.txt.
COPY timezone /etc/timezone
ENV TZ=Australia/Perth
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
# Default Scripts
RUN wget https://raw.githubusercontent.com/dbca-wa/wagov_utils/main/wagov_utils/bin/default_script_installer.sh -O /tmp/default_script_installer.sh
RUN chmod 755 /tmp/default_script_installer.sh
RUN /tmp/default_script_installer.sh

RUN groupadd -g 5000 oim 
RUN useradd -g 5000 -u 5000 oim -s /bin/bash -d /app
RUN mkdir /app 
RUN chown -R oim.oim /app

FROM builder_base_docker as python_libs_docker
WORKDIR /app

USER oim
RUN virtualenv /app/venv
ENV PATH=/app/venv/bin:$PATH
RUN git config --global --add safe.directory /app

COPY requirements.txt ./
RUN pip install --upgrade pip
RUN pip3 install --no-cache-dir -r requirements.txt

# Install the project (ensure that frontend projects have been built prior to this step).
FROM python_libs_docker
COPY --chown=oim:oim gunicorn.ini manage.py ./
RUN touch /app/.env
RUN touch /app/git_hash
# StatDev Dirs
COPY --chown=oim:oim statdev ./statdev
COPY --chown=oim:oim actions ./actions
COPY --chown=oim:oim applications ./applications
COPY --chown=oim:oim approvals ./approvals
COPY --chown=oim:oim public ./public
# Git Hash (Ammended to Javascript to force cache update)
#COPY .git/refs/heads/master /app/git_hash
# Statdev Dirs
# COPY cron /etc/cron.d/dockercron
# COPY startup.sh /
RUN python manage.py collectstatic --noinput
# RUN service rsyslog start
# RUN chmod 0644 /etc/cron.d/dockercron
# RUN crontab /etc/cron.d/dockercron
# RUN touch /var/log/cron.log
# RUN service cron start
COPY --chown=oim:oim  python-cron ./
COPY --chown=oim:oim  startup.sh /
RUN chmod 755 /startup.sh
RUN mkdir /app/private-media/
EXPOSE 8080
HEALTHCHECK --interval=1m --timeout=5s --start-period=10s --retries=3 CMD ["wget", "-q", "-O", "-", "http://localhost:8080/"]
CMD ["/startup.sh"]
