FROM python:3.13

WORKDIR /app

RUN apt-get update && apt-get install -y default-mysql-server default-mysql-client && rm -rf /var/lib/apt/lists/*
ENV TZ=Asia/Ho_Chi_Minh
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

COPY requirements.txt .
RUN pip install -r requirements.txt

RUN useradd -M nguoiyeuhayaseyuuka

COPY . .
COPY ./init.sql /tmp/init.sql

RUN chmod +x run.sh

RUN chown -R nguoiyeuhayaseyuuka:nguoiyeuhayaseyuuka /app 
RUN chmod -R 750 /app

EXPOSE 5000
CMD ["./run.sh"]