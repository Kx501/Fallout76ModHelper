"""
路径检测模块 - 自动检测 Fallout 76 游戏路径和配置目录
"""
import os
import json
from pathlib import Path
from logger import get_logger

logger = get_logger()


class PathDetector:
    """路径检测器"""
    
    def __init__(self, config_path='config.json'):
        """
        初始化路径检测器
        
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
        self.data_path = None
        self.config_dir = None
        
    def _load_config(self):
        """加载配置文件"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"加载配置文件失败: {e}")
        return {}
    
    def _expand_path(self, path_str):
        """
        展开路径中的环境变量
        
        Args:
            path_str: 包含环境变量的路径字符串
            
        Returns:
            展开后的路径
        """
        if not path_str:
            return None
        return os.path.expandvars(path_str)
    
    def _detect_steam_paths(self):
        """
        检测 Steam 安装路径（支持多库目录）
        
        Returns:
            可能的游戏路径列表
        """
        possible_paths = []
        
        # 默认 Steam 安装路径
        default_steam_paths = [
            r"C:\Program Files (x86)\Steam\steamapps\common\Fallout76",
            r"C:\Program Files\Steam\steamapps\common\Fallout76",
        ]
        
        # 检查默认路径
        for path in default_steam_paths:
            if os.path.exists(path) and os.path.isdir(path):
                possible_paths.append(path)
                logger.debug(f"找到默认 Steam 路径: {path}")
        
        # 检测库文件夹配置（libraryfolders.vdf）
        libraryfolders_paths = [
            os.path.expandvars(r"%ProgramFiles(x86)%\Steam\steamapps\libraryfolders.vdf"),
            os.path.expandvars(r"%ProgramFiles%\Steam\steamapps\libraryfolders.vdf"),
        ]
        
        for vdf_path in libraryfolders_paths:
            if os.path.exists(vdf_path):
                try:
                    # 简单解析 libraryfolders.vdf（格式较简单）
                    with open(vdf_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # 查找所有路径（"path" "xxx"格式）
                        import re
                        path_pattern = r'"path"\s+"([^"]+)"'
                        matches = re.findall(path_pattern, content)
                        for match in matches:
                            game_path = os.path.join(match.replace('\\\\', '\\'), 
                                                    'steamapps', 'common', 'Fallout76')
                            if os.path.exists(game_path) and game_path not in possible_paths:
                                possible_paths.append(game_path)
                                logger.debug(f"从 libraryfolders.vdf 找到路径: {game_path}")
                except Exception as e:
                    logger.warning(f"解析 libraryfolders.vdf 失败: {e}")
        
        return possible_paths
    
    def detect_game_path(self):
        """
        检测游戏安装路径
        
        Returns:
            游戏路径字符串，如果未找到返回 None
        """
        # 首先检查配置文件中的手动设置
        if self.config.get('game_path'):
            config_path = self._expand_path(self.config['game_path'])
            if config_path and os.path.exists(config_path):
                logger.info(f"使用配置文件中的游戏路径: {config_path}")
                self.game_path = config_path
                return config_path
            else:
                logger.warning(f"配置文件中指定的游戏路径不存在: {config_path}")
        
        # 自动检测 Steam 路径
        steam_paths = self._detect_steam_paths()
        if steam_paths:
            # 使用第一个找到的路径
            self.game_path = steam_paths[0]
            logger.info(f"自动检测到游戏路径: {self.game_path}")
            return self.game_path
        
        logger.error("未找到游戏安装路径，请在 configs/config.json 中手动配置 game_path")
        return None
    
    def detect_data_path(self):
        """
        检测 Data 目录路径
        
        Returns:
            Data 目录路径，如果未找到返回 None
        """
        if not self.game_path:
            if not self.detect_game_path():
                return None
        
        data_path = os.path.join(self.game_path, 'Data')
        if os.path.exists(data_path) and os.path.isdir(data_path):
            self.data_path = data_path
            logger.debug(f"找到 Data 目录: {data_path}")
            return data_path
        
        # 如果不存在，尝试创建
        try:
            os.makedirs(data_path, exist_ok=True)
            self.data_path = data_path
            logger.info(f"创建 Data 目录: {data_path}")
            return data_path
        except Exception as e:
            logger.error(f"无法创建 Data 目录: {e}")
            return None
    
    def detect_config_dir(self):
        """
        检测配置目录（Documents\My Games\Fallout 76）
        
        Returns:
            配置目录路径，如果未找到返回 None
        """
        userprofile = os.environ.get('USERPROFILE', '')
        if not userprofile:
            logger.error("无法获取 USERPROFILE 环境变量")
            return None
        
        config_dir = os.path.join(userprofile, 'Documents', 'My Games', 'Fallout 76')
        
        # 如果不存在，尝试创建
        try:
            os.makedirs(config_dir, exist_ok=True)
            self.config_dir = config_dir
            logger.debug(f"找到/创建配置目录: {config_dir}")
            return config_dir
        except Exception as e:
            logger.error(f"无法创建配置目录: {e}")
            return None
    
    def get_all_paths(self):
        """
        获取所有路径（一次性检测）
        
        Returns:
            dict: 包含 game_path, data_path, config_dir 的字典
        """
        game_path = self.detect_game_path()
        data_path = self.detect_data_path()
        config_dir = self.detect_config_dir()
        
        return {
            'game_path': game_path,
            'data_path': data_path,
            'config_dir': config_dir
        }

