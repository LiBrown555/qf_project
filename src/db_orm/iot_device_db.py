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
db_name = db_config['db']['name']

# 创建引擎
engine = create_engine(
    f"mysql+pymysql://{db_username}:{db_passwd}@{db_ip}:{db_port}/{db_name}?charset=utf8mb4",
    # 超过链接池大小外最多创建的链接
    max_overflow=db_config['db']['max_overflow'],
    # 链接池大小
    pool_size=db_config['db']['pool_size'],
    # 链接池中没有可用链接则最多等待的秒数，超过该秒数后报错
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

class Device(Base):
    __tablename__ = 'iot_device'
    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    device_name = Column(String(255), nullable=False, comment="设备名称（如“相机001”）")
    device_type_id = Column(Integer, nullable=False, comment="设备类型ID（关联device_type表）")
    parent_device_id = Column(Integer, nullable=True, comment="父设备ID（关联device表的ID，用于表示设备间的父子关系，如相机绑定到机器人下）")
    device_code = Column(String(50), nullable=False, comment="设备唯一编码")
    create_time = Column(DateTime, nullable=False, comment="创建时间")

    def __repr__(self):
        return f"Device(id={self.id}, device_name={self.device_name}, device_type_id={self.device_type_id}, parent_device_id={self.parent_device_id}, device_code={self.device_code}, create_time={self.create_time})"
    
    def to_dict(self):
        return {
            "id": self.id,
            "device_name": self.device_name,
            "device_type_id": self.device_type_id,
            "parent_device_id": self.parent_device_id,
            "device_code": self.device_code,
            "create_time": self.create_time,
        }


class AbilityDef(Base):
    __tablename__ = 'iot_device_ability_def'
    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    device_ability_name = Column(String(255), nullable=False, comment="硬件能力名称")
    description = Column(Text, nullable=True, comment="能力描述")
    create_time = Column(DateTime, nullable=False, comment="创建时间")

    def __repr__(self):
        return f"AbilityDef(id={self.id}, device_ability_name={self.device_ability_name}, description={self.description}, create_time={self.create_time})"
    
    def to_dict(self):
        return {
            "id": self.id,
            "device_ability_name": self.device_ability_name,
            "description": self.description,
            "create_time": self.create_time,
        }


class Attr(Base):
    __tablename__ = 'iot_device_attr'
    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    device_code = Column(String(255), nullable=False, comment="设备唯一编码")
    ip = Column(String(255), nullable=True, comment="设备网络地址")
    port = Column(Integer, nullable=True, comment="设备通讯端口")
    username = Column(String(255), nullable=True, comment="用户名")
    password = Column(String(255), nullable=True, comment="登录密码")
    factory_type = Column(Integer, nullable=True, comment="厂家类型")
    parameter = Column(JSON, nullable=True, comment="扩展参数")
    online_status = Column(Integer, nullable=True, comment="在离线状态 0/离线 1/在线")
    create_time = Column(DateTime, nullable=False, comment="创建时间")

    def __repr__(self):
        return f"Attr(id={self.id}, device_code={self.device_code}, ip={self.ip}, port={self.port}, username={self.username}, password={self.password}, factory_type={self.factory_type}, parameter={self.parameter}, online_status={self.online_status}, create_time={self.create_time})"
    
    def to_dict(self):
        return {
            "id": self.id,
            "device_code": self.device_code,
            "ip": self.ip,
            "port": self.port,
            "username": self.username,
            "password": self.password,
            "factory_type": self.factory_type,
            "parameter": self.parameter,
            "online_status": self.online_status,
            "create_time": self.create_time,
        }


class Preset(Base):
    __tablename__ = 'iot_device_preset'
    preset_id = Column(Integer, primary_key=True, nullable=False, comment="平台创建的ID")
    device_id = Column(Integer, nullable=False, comment="设备ID")
    preset_name = Column(String(255), nullable=False, comment="预置位名称")
    preset_params = Column(JSON, nullable=False, comment="预置位参数（JSON类型，存储不同设备的异构参数，如相机PTZ的pan/tilt/zoom，机械臂的joint角度）")
    description = Column(String(255), nullable=True, comment="预置位描述(园区入口全景)")
    create_time = Column(DateTime, nullable=False, comment="创建时间")

    def __repr__(self):
        return f"Preset(preset_id={self.preset_id}, device_id={self.device_id}, preset_name={self.preset_name}, preset_params={self.preset_params}, description={self.description}, create_time={self.create_time})"
    
    def to_dict(self):
        return {
            "preset_id": self.preset_id,
            "device_id": self.device_id,
            "preset_name": self.preset_name,
            "preset_params": self.preset_params,
            "description": self.description,
            "create_time": self.create_time,
        }


class DeviceType(Base):
    __tablename__ = 'iot_device_type'
    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    type_name = Column(String(100), nullable=False, comment="设备类型名称（如“移动机器人”）")
    description = Column(String(255), nullable=True, comment="类型描述（如“可自主移动的机器人”）")
    category = Column(Integer, nullable=False, comment="设备大类:0:相机 1:传感器 2:机器人 3:硬盘录像机 4:传感器监控主机")
    create_time = Column(DateTime, nullable=False, comment="创建时间")

    def __repr__(self):
        return f"DeviceType(id={self.id}, type_name={self.type_name}, description={self.description}, category={self.category}, create_time={self.create_time})"
    
    def to_dict(self):
        return {
            "id": self.id,
            "type_name": self.type_name,
            "description": self.description,
            "category": self.category,
            "create_time": self.create_time,
        }
        

class TypeAbility(Base):
    __tablename__ = 'iot_device_type_ability'
    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    device_ability_id = Column(Integer, nullable=False, comment="绑定的设备能力定义的id")
    device_type_id = Column(Integer, nullable=False, comment="绑定的设备类型的id")
    create_time = Column(DateTime, nullable=False, comment="创建时间")

    def __repr__(self):
        return f"TypeAbility(id={self.id}, device_ability_id={self.device_ability_id}, device_type_id={self.device_type_id}, create_time={self.create_time})"
    
    def to_dict(self):
        return {
            "id": self.id,
            "device_ability_id": self.device_ability_id,
            "device_type_id": self.device_type_id,
            "create_time": self.create_time,
        }
