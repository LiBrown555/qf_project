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

class Device(Base):
    __tablename__ = 'device'
    id = Column(Integer, primary_key=True, autoincrement=True, comment="设备ID(唯一标识)")
    device_name = Column(String(100), nullable=False, comment="设备名称(如'机器人001')")
    device_type_id = Column(Integer, nullable=False, comment="设备类型ID(关联device_type表)")
    key_equipment = Column(Integer, nullable=False, comment="重点设备(0:否,1:是)")
    parent_device_id = Column(Integer, nullable=False, comment="父设备ID(关联device表的ID，用于表示设备间的父子关系，如相机绑定到机器人下)")
    location_type = Column(Integer, nullable=False, comment="设备归属位置(0:室内,1:室外)")
    location = Column(String(255), nullable=True, comment="设备归属位置(如'仓库A区')")
    device_code = Column(String(50), nullable=False, comment="设备唯一编码")
    create_time = Column(DateTime, nullable=False, comment="创建时间")
    def __repr__(self):
        return f"Device(id={self.id}, device_name={self.device_name}, device_type_id={self.device_type_id}, key_equipment={self.key_equipment}, \
            parent_device_id={self.parent_device_id}, location_type={self.location_type}, location={self.location}, device_code={self.device_code}, create_time={self.create_time})"
    
    def to_dict(self):
        return {
            "id": self.id,
            "device_name": self.device_name,
            "device_type_id": self.device_type_id,
            "key_equipment": self.key_equipment,
            "parent_device_id": self.parent_device_id,
            "location_type": self.location_type,
            "location": self.location,
            "device_code": self.device_code,
            "create_time": self.create_time,
        }


class AbilityAlgorithm(Base):
    __tablename__ = 'device_ability_algorithm'
    id = Column(Integer, primary_key=True, autoincrement=True, comment="中间表主键(唯一标识)")
    device_ability_id = Column(Integer, nullable=False, comment="设备能力id")
    algorithm_id = Column(Integer, nullable=False, comment="算法能力id")
    create_time = Column(DateTime, nullable=False, comment="创建时间")
    def __repr__(self):
        return f"AbilityAlgorithm(id={self.id}, device_ability_id={self.device_ability_id}, algorithm_id={self.algorithm_id}, create_time={self.create_time})"
    
    def to_dict(self):
        return {
            "id": self.id,
            "device_ability_id": self.device_ability_id,
            "algorithm_id": self.algorithm_id,
            "create_time": self.create_time,
        }


class AbilityDef(Base):
    __tablename__ = 'device_ability_def'
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


class Attribute(Base):
    __tablename__ = 'device_attribute'
    id = Column(Integer, primary_key=True, autoincrement=True, comment="属性值ID")
    device_id = Column(Integer, nullable=False, comment="关联设备ID")
    type_attr_id = Column(Integer, nullable=False, comment="关联属性ID")
    type_attr_value = Column(String(255), nullable=True, comment="属性值")
    create_time = Column(DateTime, nullable=False, comment="创建时间")
    def __repr__(self):
        return f"Attribute(id={self.id}, device_id={self.device_id}, type_attr_id={self.type_attr_id}, type_attr_value={self.type_attr_value}, create_time={self.create_time})"
    
    def to_dict(self):
        return {
            "id": self.id,
            "device_id": self.device_id,
            "type_attr_id": self.type_attr_id,
            "type_attr_value": self.type_attr_value,
            "create_time": self.create_time,
        }


class BindingMap(Base):
    __tablename__ = 'device_binding_map'
    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    device_id = Column(Integer, nullable=False, comment="设备id")
    map_id = Column(Integer, nullable=False, comment="设备绑定的地图id")
    create_time = Column(DateTime, nullable=False, comment="创建时间")
    def __repr__(self):
        return f"BindingMap(id={self.id}, device_id={self.device_id}, map_id={self.map_id}, create_time={self.create_time})"
    
    def to_dict(self):
        return {
            "id": self.id,
            "device_id": self.device_id,
            "map_id": self.map_id,
            "create_time": self.create_time,
        }


class Point(Base):
    __tablename__ = 'device_point'
    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    device_id = Column(Integer, nullable=False, comment="设备ID")
    point_id = Column(Integer, nullable=False, comment="点位ID")
    point_type_id = Column(Integer, nullable=False, comment="点位类型ID")
    extra_attributes = Column(JSON, nullable=True, comment="扩展属性(JSON格式)")
    description = Column(Text, nullable=True, comment="点位描述(如'园区1号设备点位')")
    create_time = Column(DateTime, nullable=False, comment="关联创建时间")
    def __repr__(self):
        return f"DevicePoint(id={self.id}, device_id={self.device_id}, point_id={self.point_id}, point_type_id={self.point_type_id}, extra_attributes={self.extra_attributes}, description={self.description}, create_time={self.create_time})"
    
    def to_dict(self):
        return {
            "id": self.id,
            "device_id": self.device_id,
            "point_id": self.point_id,
            "point_type_id": self.point_type_id,
            "extra_attributes": self.extra_attributes,
            "description": self.description,
            "create_time": self.create_time,
        }


def Preset(Base):
    __tablename__ = 'device_preset'
    id = Column(Integer, primary_key=True, autoincrement=True, comment="预置位ID")
    srv_id = Column(Integer, nullable=False, comment="平台ID")
    device_id = Column(Integer, nullable=False, comment="设备ID")
    device_type_id = Column(Integer, nullable=False, comment="设备类型ID")
    name = Column(String(100), nullable=False, comment="预置位名称")
    preset_params = Column(JSON, nullable=False, comment="预置位参数")
    description = Column(String(255), nullable=True, comment="预置位描述")
    create_time = Column(DateTime, nullable=False, comment="创建时间")
    def __repr__(self):
        return f"Preset(id={self.id}, srv_id={self.srv_id}, device_id={self.device_id}, device_type_id={self.device_type_id}, name={self.name}, preset_params={self.preset_params}, description={self.description}, create_time={self.create_time})"
    
    def to_dict(self):
        return {
            "id": self.id,
            "srv_id": self.srv_id,
            "device_id": self.device_id,
            "device_type_id": self.device_type_id,
            "name": self.name,
            "preset_params": self.preset_params,
            "description": self.description,
            "create_time": self.create_time,
        }


class Status(Base):
    __tablename__ = 'device_status'
    id = Column(Integer, primary_key=True, autoincrement=True, comment="状态记录ID")
    device_id = Column(Integer, nullable=False, comment="设备ID")
    device_type_id = Column(Integer, nullable=False, comment="设备类型ID")
    online_status = Column(Integer, nullable=False, comment="在线状态")
    status_params = Column(JSON, nullable=False, comment="设备特有状态参数")
    update_time = Column(DateTime, nullable=False, comment="状态更新时间")
    def __repr__(self):
        return f"Status(id={self.id}, device_id={self.device_id}, device_type_id={self.device_type_id}, online_status={self.online_status}, status_params={self.status_params}, update_time={self.update_time})"
    
    def to_dict(self):
        return {
            "id": self.id,
            "device_id": self.device_id,
            "device_type_id": self.device_type_id,
            "online_status": self.online_status,
            "status_params": self.status_params,
            "update_time": self.update_time,
        }


class Type(Base):
    __tablename__ = 'device_type'
    id = Column(Integer, primary_key=True, autoincrement=True, comment="设备类型ID")
    type_name = Column(String(100), nullable=False, comment="设备类型名称")
    description = Column(String(255), nullable=True, comment="类型描述")
    category = Column(Integer, nullable=False, comment="设备大类")
    create_time = Column(DateTime, nullable=False, comment="创建时间")
    def __repr__(self):
        return f"Type(id={self.id}, type_name={self.type_name}, description={self.description}, category={self.category}, create_time={self.create_time})"
    
    def to_dict(self):
        return {
            "id": self.id,
            "type_name": self.type_name,
            "description": self.description,
            "category": self.category,
            "create_time": self.create_time,
        }


class TypeAbility(Base):
    __tablename__ = 'device_type_ability'
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


def TypeAttr(Base):
    __tablename__ = 'device_type_attr'
    id = Column(Integer, primary_key=True, autoincrement=True, comment="属性ID")
    type_id = Column(Integer, nullable=False, comment="关联设备类型ID")
    attr_key = Column(String(50), nullable=False, comment="属性键名(英文标识)")
    attr_name = Column(String(100), nullable=False, comment="属性名称(显示用)")
    data_type = Column(String(20), nullable=False, comment="数据类型(string/int/float/bool/enum)")
    constraints = Column(JSON, nullable=True, comment="约束条件(JSON格式)")
    enum_values = Column(JSON, nullable=True, comment="枚举值(JSON数组)")
    is_required = Column(Integer, nullable=False, comment="是否必填(1是,0否)")
    sort_order = Column(Integer, nullable=False, comment="排序")
    create_time = Column(DateTime, nullable=False, comment="创建时间")
    def __repr__(self):
        return f"TypeAttr(id={self.id}, type_id={self.type_id}, attr_key={self.attr_key}, attr_name={self.attr_name},\
            data_type={self.data_type}, constraints={self.constraints}, enum_values={self.enum_values}, is_required={self.is_required},\
            sort_order={self.sort_order}, create_time={self.create_time})"
    
    def to_dict(self):
        return {
            "id": self.id,
            "type_id": self.type_id,
            "attr_key": self.attr_key,
            "attr_name": self.attr_name,
            "data_type": self.data_type,
            "constraints": self.constraints,
            "enum_values": self.enum_values,
            "is_required": self.is_required,
            "sort_order": self.sort_order,
            "create_time": self.create_time,
        }


