FROM python:3-alpine
ARG BIN_VERSION=<unknown>

RUN mkdir /app
COPY ./requirements.txt /app
COPY ./*.py /app
RUN pip install -r /app/requirements.txt
ENTRYPOINT ["python", "/app/feedbin_archiver.py"]

LABEL license="MIT"
LABEL maintainer="Chris Dzombak <https://www.dzombak.com>"
LABEL org.opencontainers.image.authors="Chris Dzombak <https://www.dzombak.com>"
LABEL org.opencontainers.image.url="https://github.com/cdzombak/feedbin-auto-archiver"
LABEL org.opencontainers.image.documentation="https://github.com/cdzombak/feedbin-auto-archiver/blob/main/README.md"
LABEL org.opencontainers.image.source="https://github.com/cdzombak/feedbin-auto-archiver.git"
LABEL org.opencontainers.image.version="${BIN_VERSION}"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.title="feedbin-auto-archiver"
LABEL org.opencontainers.image.description="Automatically archive old unread entries in Feedbin"
