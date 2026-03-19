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

class Point(Base):
    __tablename__ = 'point'
    id = Column(Integer, primary_key=True, autoincrement=True, comment="点位ID(唯一标识)")
    srv_id = Column(Integer, nullable=False, comment="平台端传入ID")
    map_id = Column(Integer, nullable=False, comment="关联地图ID(确保点位属于有效地图)")
    point_name = Column(String(128), nullable=False, comment="点位名称")
    longitude = Column(Float, nullable=False, comment="点位经度(地理坐标,如'120.123456')")
    latitude = Column(Float, nullable=False, comment="点位纬度(地理坐标,如'30.654321')")
    x_coord = Column(Float, nullable=False, comment="地图X坐标")
    y_coord = Column(Float, nullable=False, comment="地图Y坐标")
    z_coord = Column(Float, nullable=False, comment="地图Z坐标")
    yaw = Column(Float, nullable=False, comment="弧度")
    description = Column(Text, nullable=True, comment="点位描述(如'货架1号,存放电子元件')")
    create_time = Column(DateTime, nullable=False, comment="创建时间")
    def __repr__(self):
        return f"Point(id={self.id}, srv_id={self.srv_id}, map_id={self.map_id}, point_name={self.point_name}, longitude={self.longitude}, latitude={self.latitude},\
            x_coord={self.x_coord}, y_coord={self.y_coord}, z_coord={self.z_coord}, yaw={self.yaw},\
            description={self.description}, create_time={self.create_time})"
    
    def to_dict(self):
        return {
            "id": self.id,
            "srv_id": self.srv_id,
            "map_id": self.map_id,
            "point_name": self.point_name,
            "longitude": self.longitude,
            "latitude": self.latitude,
            "x_coord": self.x_coord,
            "y_coord": self.y_coord,
            "z_coord": self.z_coord,
            "yaw": self.yaw,
            "description": self.description,
            "create_time": self.create_time,
        }


class Attr(Base):
    __tablename__ = 'point_attr'
    id = Column(Integer, primary_key=True, autoincrement=True, comment="属性ID")
    device_type_id = Column(Integer, nullable=False, comment="关联机器人类型")
    attribute_name = Column(String(50), nullable=False, comment="属性名称")
    display_name = Column(String(100), nullable=False, comment="显示名称")
    data_type = Column(String(20), nullable=False, comment="数据类型(tinyint,smallint,int,float,varchar,json)")
    constraints = Column(JSON, nullable=True, comment="约束条件(如取值说明)")
    default_value = Column(String(255), nullable=True, comment="默认值")
    create_time = Column(DateTime, nullable=False, comment="创建时间")
    update_time = Column(DateTime, nullable=False, comment="更新时间")
    def __repr__(self):
        return f"Attr(id={self.id}, device_type_id={self.device_type_id}, attribute_name={self.attribute_name}, \
            display_name={self.display_name}, data_type={self.data_type}, constraints={self.constraints}, \
            default_value={self.default_value}, create_time={self.create_time}, update_time={self.update_time})"
    
    def to_dict(self):
        return {
            "id": self.id,
            "device_type_id": self.device_type_id,
            "attribute_name": self.attribute_name,
            "display_name": self.display_name,
            "data_type": self.data_type,
            "constraints": self.constraints,
            "default_value": self.default_value,
            "create_time": self.create_time,
            "update_time": self.update_time,
        }

class Type(Base):
    __tablename__ = 'point_type'
    id = Column(Integer, primary_key=True, autoincrement=True, comment="点位类型ID(唯一标识)")
    type_name = Column(String(100), nullable=False, comment="点位类型名称(如'充电点'、'路径点')")
    description = Column(String(255), nullable=True, comment="点位类型描述(如'用于机器人充电的点位')")
    status = Column(Integer, nullable=False, comment="类型状态(0:启用;1:禁用,禁用后无法关联新点位)")
    is_delete = Column(Integer, nullable=False, comment="是否删除(1:已删除;0:未删除)")
    create_time = Column(DateTime, nullable=False, comment="创建时间")
    update_time = Column(DateTime, nullable=False, comment="更新时间")
    def __repr__(self):
        return f"Type(id={self.id}, type_name={self.type_name}, description={self.description}, status={self.status}, is_delete={self.is_delete}, create_time={self.create_time}, update_time={self.update_time})"
    
    def to_dict(self):
        return {
            "id": self.id,
            "type_name": self.type_name,
            "description": self.description,
            "status": self.status,
            "is_delete": self.is_delete,
            "create_time": self.create_time,
            "update_time": self.update_time,
        }


