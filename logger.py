"""
日志模块 - 记录所有操作到文件和控制台
"""
import logging
import os
from datetime import datetime
from rich.logging import RichHandler
from rich.console import Console


class Logger:
    """统一的日志管理器"""
    
    def __init__(self, log_file='install.log'):
        """
        初始化日志系统
        
        Args:
            log_file: 日志文件路径（相对路径，会自动放入 logs/ 文件夹）
        """
        # 获取脚本所在目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        logs_dir = os.path.join(script_dir, 'logs')
        
        # 确保 logs 目录存在
        os.makedirs(logs_dir, exist_ok=True)
        
        # 构建完整日志文件路径
        if os.path.isabs(log_file):
            self.log_file = log_file
        else:
            self.log_file = os.path.join(logs_dir, log_file)
        self.logger = logging.getLogger('FalloutHelper')
        self.logger.setLevel(logging.DEBUG)
        
        # 避免重复添加处理器
        if not self.logger.handlers:
            # 文件处理器（使用完整路径）
            file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            file_format = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_format)
            self.logger.addHandler(file_handler)
            
            # 控制台处理器 - 使用 RichHandler 美化输出
            console_handler = RichHandler(
                console=Console(stderr=True),
                show_time=False,
                show_path=False,
                rich_tracebacks=True
            )
            console_handler.setLevel(logging.INFO)
            console_format = logging.Formatter('%(message)s')
            console_handler.setFormatter(console_format)
            self.logger.addHandler(console_handler)
    
    def debug(self, message):
        """记录调试信息"""
        self.logger.debug(message)
    
    def info(self, message):
        """记录一般信息"""
        self.logger.info(message)
    
    def warning(self, message):
        """记录警告信息"""
        self.logger.warning(message)
    
    def error(self, message):
        """记录错误信息"""
        self.logger.error(message)
    
    def critical(self, message):
        """记录严重错误信息"""
        self.logger.critical(message)


# 全局日志实例
_logger_instance = None


def get_logger():
    """获取全局日志实例"""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = Logger()
    return _logger_instance

