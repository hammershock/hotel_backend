from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()


class RoomRecord(Base):
    __tablename__ = 'room_records'

    id = Column(Integer, primary_key=True)
    room_number = Column(Integer)
    temperature = Column(Float)


engine = create_engine('sqlite:///example.db')
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()


new_record = RoomRecord(room_number=101, temperature=23.5)
session.add(new_record)
session.commit()


records = session.query(RoomRecord).filter_by(room_number=101).all()
for record in records:
    print(f"Room {record.room_number}, Temperature: {record.temperature}")


session.close()

