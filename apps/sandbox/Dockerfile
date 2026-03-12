FROM python:3.12-alpine

# Build deps for numpy/scipy C extensions
RUN apk add --no-cache gcc musl-dev linux-headers libffi-dev

RUN pip install --no-cache-dir \
    flask==3.0.3         \
    numpy==1.26.4        \
    pandas==2.2.2        \
    matplotlib==3.9.0    \
    scikit-learn==1.5.0  \
    scipy==1.13.0        \
    pdfplumber==0.11.0

# Non-root execution — mandatory
RUN adduser -D -u 1001 sandbox
USER sandbox
WORKDIR /home/sandbox

COPY --chown=sandbox:sandbox server.py .

# Non-interactive matplotlib backend
ENV MPLBACKEND=Agg
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 5000
CMD ["python", "server.py"]
