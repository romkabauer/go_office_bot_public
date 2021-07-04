FROM python:3.7.5

WORKDIR /home
ADD . ./app

RUN apt-get -y update
RUN  apt-get install --no-install-recommends -y python3-distutils

RUN pip install --upgrade pip
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

ENTRYPOINT ["python3", "app/bot.py"]