FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir streamlit==1.56.0 requests==2.33.1

COPY app/app.py .

EXPOSE 8501

CMD [ "streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
