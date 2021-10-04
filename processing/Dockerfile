FROM python:3.7
COPY . /processing
WORKDIR /processing
# RUN apk --no-cache add musl-dev linux-headers g++
# RUN apk --update add --virtual scipy-runtime python py-pip
# RUN apk add --virtual scipy-build
RUN pip install --no-cache-dir -U pip wheel setuptools

RUN pip install --upgrade pip
RUN pip install cython
RUN pip install numpy==1.19.5
RUN pip install -r requirements.txt

# CMD [ "sh", "run_all.sh" ]
