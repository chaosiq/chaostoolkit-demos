FROM python:3.9-alpine

RUN pip install --no-cache-dir \
    starlette starlette_exporter prometheus-client uvicorn
EXPOSE 8004

COPY . .

ENTRYPOINT [ "uvicorn" ]
CMD [ "--host", "0.0.0.0", "--port", "8004", "app:app" ]
