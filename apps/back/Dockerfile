FROM python:3.9-alpine

RUN pip install --no-cache-dir starlette uvicorn httpx
EXPOSE 8002

COPY . .

ENTRYPOINT [ "uvicorn" ]
CMD [ "--host", "0.0.0.0", "--port", "8002", "app:app" ]
