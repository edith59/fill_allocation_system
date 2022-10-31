FROM python:3.9

WORKDIR /src

COPY ./requirements.txt /src/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /src/requirements.txt
COPY ./main.py /src/main.py

CMD ["uvicorn", "main:app", "--host", "aum_server", "--port", "8000"]