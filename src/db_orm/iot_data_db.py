import yaml
from sqlalchemy.orm import (
    sessionmaker, 
    scoped_session, 
    declarative_base
)
from sqlalchemy import (
    create_engine, 
    Column, 
    Integer, 
    String, 
    Float, 
    DateTime, 
    Boolean)

with open('data/configuration/sql_db.yaml', 'r', encoding='utf-8') as f:
    db_config = yaml.safe_load(f)

db_username = db_config['db']['username']
db_passwd = db_config['db']['passwd']
db_ip = db_config['db']['ip']
db_port = db_config['db']['port']
db_name = db_config['db']['name']

# 创建引擎
engine = create_engine(
    f"mysql+pymysql://{db_username}:{db_passwd}@{db_ip}:{db_port}/{db_name}?charset=utf8mb4",
    # 超过链接池大小外最多创建的链接
    max_overflow=db_config['db']['max_overflow'],
    # 链接池大小
    pool_size=db_config['db']['pool_size'],
    pool_timeout=db_config['db']['pool_timeout'],
    # 多久之后对链接池中的链接进行一次回收
    pool_recycle=db_config['db']['pool_recycle'],
    pool_pre_ping=db_config['db']['pool_pre_ping'],
    # 查看原生语句（未格式化）
    # echo=True
)
Base = declarative_base()
Session = sessionmaker(bind=engine)
session = scoped_session(Session)

class ItemDefinition(Base):
    __tablename__ = 'iot_data_item_definition'
    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    srv_id = Column(Integer, nullable=True, comment="平台ID")
    device_type_id = Column(Integer, nullable=False)
    item_code = Column(String(255), nullable=False, comment="如 temp, humi, gas_ch4, gas_co, etc")
    item_name = Column(String(255), nullable=False, comment="可读名：温度 / 湿度 / 甲烷 / 一氧化碳")
    unit = Column(String(255), nullable=False, comment="单位，如 ℃、%RH、ppm")
    data_type = Column(String(255), nullable=False, comment="float / int / bool / string")
    sort_order = Column(String(255), nullable=False, comment="前端展示排序")
    create_time = Column(DateTime, nullable=False, comment="创建时间")

    def __repr__(self):
        return f"ItemDefinition(id={self.id}, srv_id={self.srv_id}, device_type_id={self.device_type_id}, item_code={self.item_code}, item_name={self.item_name}, unit={self.unit}, data_type={self.data_type}, sort_order={self.sort_order}, create_time={self.create_time})"

    def to_dict(self):
        return {
            "id": self.id,
            "srv_id": self.srv_id,
            "device_type_id": self.device_type_id,
            "item_code": self.item_code,
            "item_name": self.item_name,
            "unit": self.unit,
            "data_type": self.data_type,
            "sort_order": self.sort_order,
            "create_time": self.create_time,
        }