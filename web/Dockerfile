FROM python
WORKDIR /srv/app
COPY ./web/ ./
COPY ./*.py ./
RUN pip install -r requirements.txt
CMD [ "python", "-u", "./app.py" ]
