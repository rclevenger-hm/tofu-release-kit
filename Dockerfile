FROM python:3.12-slim AS builder
WORKDIR /build
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN python -m pip wheel --no-deps --wheel-dir /wheels .
COPY scripts/install_tools.py /install_tools.py
RUN python /install_tools.py --directory /tools

FROM python:3.12-slim
COPY --from=builder /wheels /wheels
RUN python -m pip install --no-cache-dir /wheels/*.whl && rm -rf /wheels \
    && useradd --uid 10001 --create-home toolkit
COPY --from=builder /tools/opa /usr/local/bin/opa
USER 10001
WORKDIR /work
ENTRYPOINT ["tofu-release-kit"]
