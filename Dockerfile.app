FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir streamlit==1.56.0 requests==2.33.1 httpx==0.28.1 streamlit-float==0.4.0

COPY app .

EXPOSE 8501

CMD [ "streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
