FROM python:3.10.17-slim-bookworm

WORKDIR /app

COPY * /app
RUN apt update 
RUN apt install libgl-dev libglib2.0-0 -y
RUN apt clean

RUN pip3 install -r requirements.txt -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
RUN pip3 cache purge

# ENTRYPOINT [ "/bin/bash" ]

ENTRYPOINT ["python3"]
CMD ["bot.py"]
