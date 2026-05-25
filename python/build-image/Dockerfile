ARG BASE_IMAGE=piwikpro.azurecr.io/framework/base-image:1.4.0
ARG UV_VERSION=latest

FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

FROM ${BASE_IMAGE} AS builder
COPY --from=uv /uv /uvx /bin/

ENV UV_PROJECT=/app
ENV UV_NO_CACHE=1
ENV UV_FROZEN=1
ENV UV_NO_EDITABLE=1
ENV UV_MANAGED_PYTHON=1
ENV UV_PYTHON_INSTALL_DIR=/opt/python
ENV VIRTUAL_ENV=/opt/venv

ENV BUILD_DEPENDENCIES=""
RUN if [ -f /etc/debian_version ]; then \
		apt-get update && apt-get install -y --no-install-recommends ${BUILD_DEPENDENCIES} \
			&& rm -rf /var/lib/apt/lists/*; \
	elif [ -f /etc/alpine-release ]; then \
		apk add --no-cache ${BUILD_DEPENDENCIES}; \
	fi

COPY pyproject.toml uv.lock LICENSE.md README.md /app/
RUN uv sync --no-dev --active --no-install-project

ARG PACKAGES
COPY ${PACKAGES} /app/
RUN uv sync --no-dev --active

FROM ${BASE_IMAGE}

ENV RUN_DEPENDENCIES=""
RUN if [ -f /etc/debian_version ]; then \
		apt-get update && apt-get install -y --no-install-recommends ${RUN_DEPENDENCIES} \
			&& rm -rf /var/lib/apt/lists/*; \
	elif [ -f /etc/alpine-release ]; then \
		apk add --no-cache ${RUN_DEPENDENCIES}; \
	fi

USER piwikpro
COPY --from=builder /opt /opt
WORKDIR /home/piwikpro
ENV PATH="/opt/venv/bin:$PATH"

ARG COMMAND=""
CMD ${COMMAND}
