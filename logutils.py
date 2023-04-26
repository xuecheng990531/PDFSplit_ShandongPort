import time
import logging
import logging.handlers

# logging初始化工作
logging.basicConfig()
logger = logging.getLogger('script')
logger.setLevel(logging.INFO)
# 添加TimedRotatingFileHandler
timefilehandler = logging.handlers.TimedRotatingFileHandler(
    "log/test.log",    #日志路径
    when='D',      # S秒 M分 H时 D天 W周 按时间切割 测试选用S
    interval=1,    # 多少天切割一次
    backupCount=7  # 保留多少天
)
# 设置后缀名称，跟strftime的格式一样
timefilehandler.suffix = "%Y-%m-%d_%H-%M-%S.log"
formatter = logging.Formatter('%(asctime)s|%(name)s | %(levelname)s | %(message)s')
timefilehandler.setFormatter(formatter)

logger.addHandler(timefilehandler)