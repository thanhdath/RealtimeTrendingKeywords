FROM python:3.6.1-alpine
COPY . /processing
WORKDIR /processing
RUN pip install -r requirements.txt

CMD [ "sh", "run_all.sh" ]
