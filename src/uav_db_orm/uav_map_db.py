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
    Boolean,
    JSON,
    Text)

with open('data/configuration/sql_db.yaml', 'r', encoding='utf-8') as f:
    db_config = yaml.safe_load(f)

db_username = db_config['db']['username']
db_passwd = db_config['db']['passwd']
db_ip = db_config['db']['ip']
db_port = db_config['db']['port']
db_name = db_config['db']['uav_name']

# 创建引擎
engine = create_engine(
    f"mysql+pymysql://{db_username}:{db_passwd}@{db_ip}:{db_port}/{db_name}?charset=utf8mb4",
    # 超过链接池大小外最多创建的链接
    max_overflow=db_config['db']['max_overflow'],
    # 链接池大小
    pool_size=db_config['db']['pool_size'],
    # 链接池中没有可用链接则最多等待的秒数，超过该秒数后报错
    pool_timeout=db_config['db']['pool_timeout'],
    # 多久之后对链接池中的链接进行一次回收（MySQL默认wait_timeout 8小时）
    pool_recycle=db_config['db']['pool_recycle'],
    # 使用前检测连接是否存活，防止使用已被服务端关闭的连接
    pool_pre_ping=db_config['db']['pool_pre_ping'],
    # 查看原生语句（未格式化）
    # echo=True
)
Base = declarative_base()
Session = sessionmaker(bind=engine)
session = scoped_session(Session)

class Map(Base):
    __tablename__ = 'map'
    id = Column(Integer, primary_key=True, autoincrement=True, comment="地图ID(唯一标识)")
    map_name = Column(String(100), nullable=False, comment="地图名称(如'仓库A区地图')")
    file_path = Column(String(255), nullable=False, comment="地图文件路径/URL(如'/maps/warehouse_a.png'或'https://oss.example.com/maps/warehouse_a.json')")
    corner_lr = Column(JSON, nullable=True, comment="地图经纬度")
    scale_ratio = Column(Float, nullable=True, comment="地图分辨率")
    description = Column(Text, nullable=True, comment="地图描述(如'仓库A区,包含10个货架点位')")
    create_time = Column(DateTime, nullable=False, comment="创建时间")
    def __repr__(self):
        return f"Map(id={self.id}, map_name={self.map_name}, file_path={self.file_path}, corner_lr={self.corner_lr}, scale_ratio={self.scale_ratio}, description={self.description}, create_time={self.create_time})"
    
    def to_dict(self):
        return {
            "id": self.id,
            "map_name": self.map_name,
            "file_path": self.file_path,
            "corner_lr": self.corner_lr,
            "scale_ratio": self.scale_ratio,
            "description": self.description,
            "create_time": self.create_time,
        }
