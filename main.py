'''Сервер REST API с возможностью сохранения в базе данных запросов с сайта с англоязычными вопросами для викторин'''
from fastapi import FastAPI
from pydantic import BaseModel

from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import CreateSchema
from sqlalchemy import create_engine, Table, Column, Integer, DateTime, Text, select, inspect, MetaData, TIMESTAMP
from sqlalchemy.engine.url import URL
from sqlalchemy.ext.declarative import declarative_base

from datetime import datetime

import logging
import json
import requests
import subprocess
import os

logging.basicConfig(filename='app.log', filemode='a', 
                    format='[%(asctime)s] %(levelname)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S')
logger = logging.getLogger('logger')

app = FastAPI()
base = declarative_base()
metadata = MetaData(schema="test")


TABLE_ARGS = {'schema': 'test'}

DATABASE = {
    "drivername": "postgresql",
    "host": "postgres",
    "port": "5432",
    "username": "test",
    "password": "test",
    "database": "test"
    }

engine = create_engine(URL(**DATABASE))
inspector = inspect(engine)
metadata = MetaData(engine)

#Создание схемы в базе данных, если таковой нет
if not engine.dialect.has_schema(engine, 'test'):
    engine.execute(CreateSchema('test'))

#Создание таблицы в базе данных, если таковой нет
if 'records' not in inspector.get_table_names(schema='test'):

    records_table = Table('records', metadata,

          Column('id_question', Integer(), primary_key=True, unique=True), 
          Column('text_question', Text()),
          Column('text_answer', Text()),
          Column('dt_insert', TIMESTAMP()),
          Column('created_at', TIMESTAMP()))

    records_table.create(engine)


class records(base): 
    '''Класс для запросов из БД'''
    __tablename__ = 'records'

    id_question = Column('id_question', Integer(), primary_key=True)
    text_question = Column('text_question', Text())
    text_answer = Column('text_answer', Text())
    dt_insert = Column('dt_insert', TIMESTAMP())
    created_at = Column('created_at', TIMESTAMP())

    __table_args__ = TABLE_ARGS


class question(BaseModel):
    '''Класс для ответов на запросы'''
    questions_num: int


def input_data(cnt):
    '''Функция, которая нужна для заполнения БД уникальными вопросами
       Если вопрос уже есть в БД, то функция вызывает сама себя для того,
       чтобы добавить уникальные вопросы'''

    try:
        
        r = requests.get(f'https://jservice.io/api/random?count={cnt}')

        data = json.loads(r.text)

        exists = 0

        Session = sessionmaker(engine)  
        session = Session()
        
        for segment in data:

            if (session.query(records).filter(records.id_question==segment.get('id')).count() != 0) or segment.get('question') == '' or segment.get('answer') == '':

                exists += 1

            else:

                add = records(id_question=segment.get('id'), text_question=segment.get('question'), 
                    text_answer=segment.get('answer'),dt_insert=datetime.now(), created_at=segment.get('created_at'))
                session.add(add)
                session.commit()

        if exists != 0:
            
            input_data(exists)

    except:

        session.rollback()
        session.close()

        raise


@app.post("/")
async def add_row(questions_num: question):
    '''Принимает и обрабатывает входящие POST запросы.
       Возвращает ответ в формате {
                                    "text_answer": "text",
                                    "created_at": "datetime",
                                    "id_question": int,
                                    "dt_insert": "datetime",
                                    "text_question": "text"
                                  }'''

    Session = sessionmaker(engine)  
    session = Session()

    if questions_num.questions_num == 0:

        response = session.query(records).order_by(records.dt_insert.desc()).first()
        session.close()

        return response

    elif type(questions_num.questions_num) == int and questions_num.questions_num > 0:

        try:
            
            cnt = questions_num.questions_num

            while True:

                input_data(cnt)

                cnt -= 100

                if cnt <= 0:
                    break
                

            response = session.query(records).order_by(records.dt_insert.desc()).first()
            session.close()
            
            return response
        
        except:

            session.rollback()
            session.close()

            raise


