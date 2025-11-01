"""
游戏启动模块 - 启动 Fallout 76 游戏
"""
import os
import subprocess
import webbrowser
import json
from pathlib import Path
from logger import get_logger

logger = get_logger()


class GameLauncher:
    """游戏启动器"""
    
    def __init__(self, config_path='config.json'):
        """
        初始化游戏启动器
        
        Args:
            config_path: 配置文件路径（相对路径，会自动放入 configs/ 文件夹）
        """
        # 获取脚本所在目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 如果是相对路径，放入 configs 文件夹
        if not os.path.isabs(config_path):
            config_dir = os.path.join(script_dir, 'configs')
            os.makedirs(config_dir, exist_ok=True)
            self.config_path = os.path.join(config_dir, config_path)
        else:
            self.config_path = config_path
        
        self.config = self._load_config()
        self.game_path = None
    
    def _load_config(self):
        """加载配置文件"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"加载配置文件失败: {e}")
        return {}
    
    def set_game_path(self, game_path):
        """
        设置游戏路径
        
        Args:
            game_path: 游戏安装路径
        """
        self.game_path = game_path
    
    def _launch_via_url(self, url):
        """
        通过 URL scheme 启动游戏
        
        Args:
            url: URL scheme（如 steam://rungameid/1151340）
        
        Returns:
            是否成功启动
        """
        try:
            logger.info(f"通过 URL 启动游戏: {url}")
            webbrowser.open(url)
            logger.info("游戏启动命令已执行")
            return True
        except Exception as e:
            logger.error(f"通过 URL 启动游戏失败: {e}")
            return False
    
    def _launch_via_executable(self, exe_path):
        """
        通过可执行文件启动游戏
        
        Args:
            exe_path: 游戏可执行文件路径
        
        Returns:
            是否成功启动
        """
        if not os.path.exists(exe_path):
            logger.error(f"游戏可执行文件不存在: {exe_path}")
            return False
        
        try:
            logger.info(f"启动游戏可执行文件: {exe_path}")
            # 获取游戏目录作为工作目录
            game_dir = os.path.dirname(exe_path)
            subprocess.Popen([exe_path], cwd=game_dir)
            logger.info("游戏启动命令已执行")
            return True
        except Exception as e:
            logger.error(f"启动游戏可执行文件失败: {e}")
            return False
    
    def launch(self):
        """
        启动游戏
        
        Returns:
            是否成功启动
        """
        # 优先使用 launch_url
        launch_url = self.config.get('launch_url')
        if launch_url:
            logger.info("使用配置的 launch_url 启动游戏")
            return self._launch_via_url(launch_url)
        
        # 如果没有 launch_url，尝试使用可执行文件
        if self.game_path:
            # Fallout76.exe 路径
            exe_path = os.path.join(self.game_path, 'Fallout76.exe')
            if os.path.exists(exe_path):
                logger.info("使用游戏可执行文件启动")
                return self._launch_via_executable(exe_path)
            else:
                logger.warning(f"游戏可执行文件不存在: {exe_path}")
        
        # 如果配置中有可执行文件路径
        exe_path_config = self.config.get('launch_exe')
        if exe_path_config:
            expanded_path = os.path.expandvars(exe_path_config)
            if os.path.exists(expanded_path):
                logger.info("使用配置的 launch_exe 启动游戏")
                return self._launch_via_executable(expanded_path)
        
        logger.error("无法启动游戏: 未找到有效的启动方式")
        logger.error("请在 configs/config.json 中配置 launch_url 或 launch_exe")
        return False

