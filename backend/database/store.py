import json
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import declarative_base, sessionmaker
Base=declarative_base()
class Record(Base):
    __tablename__='records'
    id=Column(Integer,primary_key=True)
    kind=Column(String,index=True)
    payload=Column(Text)
engine=create_engine('sqlite:///data/twin.db',connect_args={'check_same_thread':False})
Base.metadata.create_all(engine)
Session=sessionmaker(bind=engine)
def save(kind,payload):
    with Session.begin() as s: s.add(Record(kind=kind,payload=json.dumps(payload)))
def read(kind,limit=100):
    with Session() as s: return [json.loads(r.payload) for r in s.query(Record).filter_by(kind=kind).order_by(Record.id.desc()).limit(limit).all()][::-1]
