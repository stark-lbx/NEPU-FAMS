# 业务类型（对应审批流）
BUSINESS_TYPE_BORROW = 1
BUSINESS_TYPE_REPAIR = 2
BUSINESS_TYPE_SCRAP = 3
BUSINESS_TYPE_CHECK = 4

# 附件类型
ATTACH_TYPE_INVOICE = 1
ATTACH_TYPE_PHOTO = 2
ATTACH_TYPE_REPAIR = 3

# 审批结果
AUDIT_WAIT = "WAIT"
AUDIT_PASS = "PASS"
AUDIT_REJECT = "REJECT"

# 盘点状态
TASK_WAIT = "WAIT"
TASK_DOING = "DOING"
TASK_FINISH = "FINISH"

# ==================== RabbitMQ 全局配置 ====================
# 死信交换机（所有队列共用）
DLX_EXCHANGE = "dlx_exchange"
DLX_EXCHANGE_TYPE = "direct"

# 消息最大重试次数
MAX_RETRY_COUNT = 3
# 重试延迟秒数
RETRY_DELAY_SECONDS = 5

# 删除文件队列（存储服务消费）
QUEUE_DELETE_FILE = {
    "exchange": "delete_file_exchange",
    "type": "direct",
    "queue": "delete_file_queue",
    "binding_key": "delete_file_queue"
}

# 全局延迟删除缓存交换机（所有服务共用）
_DELETE_CACHE_EXCHANGE = "delete_cache_exchange"
_CACHE_QUEUE_TYPE = "delayed"
_DEFAULT_CACHE_DELAY_TTL = 3  # 默认延迟秒数

# 用户服务-延迟删除缓存队列
QUEUE_DELETE_CACHE_USER = {
    "exchange": _DELETE_CACHE_EXCHANGE,
    "type": _CACHE_QUEUE_TYPE,
    "queue": "delete_cache_user_queue",
    "binding_key": "user.cache",
    "delayed_ttl": _DEFAULT_CACHE_DELAY_TTL
}

# 资产服务-延迟删除缓存队列
QUEUE_DELETE_CACHE_ASSET = {
    "exchange": _DELETE_CACHE_EXCHANGE,
    "type": _CACHE_QUEUE_TYPE,
    "queue": "delete_cache_asset_queue",
    "binding_key": "asset.cache",
    "delayed_ttl": _DEFAULT_CACHE_DELAY_TTL
}

# 流程服务-延迟删除缓存队列
QUEUE_DELETE_CACHE_FLOW = {
    "exchange": _DELETE_CACHE_EXCHANGE,
    "type": _CACHE_QUEUE_TYPE,
    "queue": "delete_cache_flow_queue",
    "binding_key": "flow.cache",
    "delayed_ttl": _DEFAULT_CACHE_DELAY_TTL
}