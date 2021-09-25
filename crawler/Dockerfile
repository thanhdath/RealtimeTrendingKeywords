FROM python:3.6.1-alpine
COPY . /crawler
WORKDIR /crawler
RUN pip install -r requirements.txt
CMD [ "python", "./crawl_vnexpress.py" ]
