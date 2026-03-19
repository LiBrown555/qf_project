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

class Task(Base):
    __tablename__ = 'iot_task'
    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    srv_id = Column(Integer, nullable=True, comment="平台端ID")
    task_name = Column(String(100), nullable=False, comment="任务名称（如园区巡检）")
    device_id = Column(Integer, nullable=False, comment="执行设备ID（关联`device`表，如机器人的ID）")
    description = Column(Text, nullable=True, comment="任务描述（如覆盖园区主要通道的巡检）")
    operator_id = Column(Integer, nullable=True, comment="最后操作者的用户ID（如创建任务的用户）")
    status = Column(Integer, nullable=False, comment="任务状态（0：启用；1：禁用，避免删除数据）")
    is_delete = Column(Integer, nullable=False, comment="是否被删除（1 被删除，0未被删除）")
    create_time = Column(DateTime, nullable=False, comment="任务创建时间")
    update_time = Column(DateTime, nullable=False, comment="任务更新时间（精确到微秒，自动同步）")

    def __repr__(self):
        return f"Task(id={self.id}, srv_id={self.srv_id}, task_name={self.task_name}, device_id={self.device_id}, description={self.description}, operator_id={self.operator_id}, status={self.status}, is_delete={self.is_delete}, create_time={self.create_time}, update_time={self.update_time})"
    
    def to_dict(self):
        return {
            "id": self.id,
            "srv_id": self.srv_id,
            "task_name": self.task_name,
            "device_id": self.device_id,
            "description": self.description,
            "operator_id": self.operator_id,
            "status": self.status,
            "is_delete": self.is_delete,
            "create_time": self.create_time,
            "update_time": self.update_time,
        }
    

class Action(Base):
    __tablename__ = 'iot_task_action'
    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    srv_id = Column(Integer, nullable=True, comment="平台ID")
    task_id = Column(Integer, nullable=False, comment="任务ID")
    device_id = Column(Integer, nullable=False, comment="执行设备的ID")
    device_ability_id = Column(Integer, nullable=False, comment="执行的设备能力ID")
    preset_id = Column(Integer, nullable=True, comment="使用的预置位ID（可为空）")
    sort_order = Column(Integer, nullable=False, comment="动作执行顺序")
    action_params = Column(JSON, nullable=True, comment="动作执行参数（JSON格式）")
    create_time = Column(DateTime, nullable=False, comment="创建时间")
    def __repr__(self):
        return f"Action(id={self.id}, srv_id={self.srv_id}, task_id={self.task_id}, device_id={self.device_id}, device_ability_id={self.device_ability_id}, preset_id={self.preset_id}, sort_order={self.sort_order}, action_params={self.action_params}, create_time={self.create_time})"
    
    def to_dict(self):
        return {
            "id": self.id,
            "srv_id": self.srv_id,
            "task_id": self.task_id,
            "device_id": self.device_id,
            "device_ability_id": self.device_ability_id,
            "preset_id": self.preset_id,
            "sort_order": self.sort_order,
            "action_params": self.action_params,
            "create_time": self.create_time,
        }


class Plan(Base):
    __tablename__ = 'iot_task_plan'
    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    srv_id = Column(Integer, nullable=True, comment="平台ID")
    task_id = Column(Integer, nullable=False, comment="关联任务ID（关联`task`表的`ID`）")
    plan_name = Column(String(255), nullable=False, comment="计划名称")
    plan_type = Column(Integer, nullable=False, comment="计划类型（0：单次执行；1：每天执行；2：每周执行；3：每月执行）")
    execute_time = Column(DateTime, nullable=True, comment="单次执行时间（仅当 plan_type=0 时有效，如2025-09-01 14:30:00）")
    cycle_config = Column(JSON, nullable=True, comment="周期配置（仅当plan_type=1/2/3时有效，示例：")
    cycle_start_time = Column(DateTime, nullable=True, comment="周期开始时间（仅当plan_type=1/2/3时有效，如2025-09-0）")
    cycle_end_time = Column(DateTime, nullable=True, comment="周期结束时间（仅当plan_type=1/2/3时有效，如2025-12-31）")
    plan_status = Column(Integer, nullable=False, comment="计划状态（0：未启用；1：启用；2：已过期）")
    progress_generate = Column(Integer, nullable=False, comment="任务生成（0：未生成；1：生成中；2：已生成；3：异常）")
    create_time = Column(DateTime, nullable=False, comment="计划创建时间")
    update_time = Column(DateTime, nullable=False, comment="计划更新时间（自动同步）")
    def __repr__(self):
        return f"Plan(id={self.id}, srv_id={self.srv_id}, task_id={self.task_id}, plan_name={self.plan_name}, plan_type={self.plan_type}, execute_time={self.execute_time}, cycle_config={self.cycle_config}, cycle_start_time={self.cycle_start_time}, cycle_end_time={self.cycle_end_time}, plan_status={self.plan_status}, progress_generate={self.progress_generate}, create_time={self.create_time}, update_time={self.update_time})"
    
    def to_dict(self):
        return {
            "id": self.id,
            "srv_id": self.srv_id,
            "task_id": self.task_id,
            "plan_name": self.plan_name,
            "plan_type": self.plan_type,
            "execute_time": self.execute_time,
            "cycle_config": self.cycle_config,
            "cycle_start_time": self.cycle_start_time,
            "cycle_end_time": self.cycle_end_time,
            "plan_status": self.plan_status,
            "progress_generate": self.progress_generate,
            "create_time": self.create_time,
            "update_time": self.update_time,
        }
        
    
class Progress(Base):
    __tablename__ = 'iot_task_progress'
    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    task_plan_id = Column(Integer, nullable=False, comment="关联执行计划ID（`task_plan`.`id`，必选）")
    task_id = Column(Integer, nullable=False, comment="关联任务ID（`task`.`ID`，冗余字段，加速查询）")
    device_id = Column(Integer, nullable=False, comment="执行任务的机器人ID（`device`.`id`，必选）")
    progress = Column(Integer, nullable=False, comment="任务进度（0-100，百分比，如`50`表示50%）")
    task_detail = Column(JSON, nullable=True, comment="任务详情（{总点位:20,已执行点位:4,当前点位:5,...}）")
    status = Column(Integer, nullable=False, comment="执行状态（0：执行中；1：已完成；2：失败；3：暂停；4：待执行；5：异常）")
    pause_time = Column(DateTime, nullable=True, comment="暂停时间（机器人端记录，如2025-09-01 14:40:00）")
    pause_reason = Column(String(255), nullable=True, comment="暂停原因（如用户手动暂停）")
    resume_time = Column(DateTime, nullable=True, comment="恢复时间")
    start_time = Column(DateTime, nullable=True, comment="任务执行开始时间")
    end_time = Column(DateTime, nullable=True, comment="任务执行结束时间")
    failure_reason = Column(String(255), nullable=True, comment="失败原因")
    progress_status = Column(Integer, nullable=False, comment="启用0/禁用1")
    progress_uuid = Column(String(255), nullable=False, comment="任务唯一ID")
    sync_time = Column(DateTime, nullable=False, comment="机器人同步到平台的时间（机器人端时间，必选）")
    create_time = Column(DateTime, nullable=False, comment="任务进度创建时间")
    update_time = Column(DateTime, nullable=False, comment="任务进度更新时间")
    def __repr__(self):
        return f"Progress(id={self.id}, task_plan_id={self.task_plan_id}, task_id={self.task_id}, device_id={self.device_id}, progress={self.progress}, task_detail={self.task_detail}, status={self.status}, pause_time={self.pause_time}, pause_reason={self.pause_reason}, resume_time={self.resume_time}, start_time={self.start_time}, end_time={self.end_time}, failure_reason={self.failure_reason}, progress_status={self.progress_status}, progress_uuid={self.progress_uuid}, sync_time={self.sync_time}, create_time={self.create_time}, update_time={self.update_time})"
    
    def to_dict(self):
        return {
            "id": self.id,
            "task_plan_id": self.task_plan_id,
            "task_id": self.task_id,
            "device_id": self.device_id,
            "progress": self.progress,
            "task_detail": self.task_detail,
            "status": self.status,
            "pause_time": self.pause_time,
            "pause_reason": self.pause_reason,
            "resume_time": self.resume_time,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "failure_reason": self.failure_reason,
            "progress_status": self.progress_status,
            "progress_uuid": self.progress_uuid,
            "sync_time": self.sync_time,
            "create_time": self.create_time,
            "update_time": self.update_time,
        }


class Result(Base):
    __tablename__ = 'iot_task_result'
    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    task_plan_id = Column(Integer, nullable=False, comment="任务计划ID")
    task_action_id = Column(Integer, nullable=False, comment="任务动作ID")
    task_progress_id = Column(Integer, nullable=False, comment="任务进度ID")
    device_id = Column(Integer, nullable=False, comment="设备ID")
    file_path = Column(String(255), nullable=False, comment="文件地址")
    item_values = Column(JSON, nullable=True, comment="检测项与值")
    parameters = Column(JSON, nullable=True, comment="扩展参数 例如 message_id")
    error_info = Column(String(255), nullable=True, comment="异常信息")
    post_status = Column(Integer, nullable=False, comment="推送状态 0/未推送 1/已推送 2/推送异常")
    create_time = Column(DateTime, nullable=False, comment="创建时间")
    def __repr__(self):
        return f"Result(id={self.id}, task_plan_id={self.task_plan_id}, task_action_id={self.task_action_id}, task_progress_id={self.task_progress_id}, device_id={self.device_id}, file_path={self.file_path}, item_values={self.item_values}, parameters={self.parameters}, error_info={self.error_info}, post_status={self.post_status}, create_time={self.create_time})"
    
    def to_dict(self):
        return {
            "id": self.id,
            "task_plan_id": self.task_plan_id,
            "task_action_id": self.task_action_id,
            "task_progress_id": self.task_progress_id,
            "device_id": self.device_id,
            "file_path": self.file_path,
            "item_values": self.item_values,
            "parameters": self.parameters,
            "error_info": self.error_info,
            "post_status": self.post_status,
            "create_time": self.create_time,
        }

