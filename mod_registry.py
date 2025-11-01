"""
Mod 信息记录模块 - 记录已安装的 mod 信息（版本号、安装时间等）
"""
import os
import json
import re
from datetime import datetime
from pathlib import Path
from logger import get_logger

logger = get_logger()


class ModRegistry:
    """Mod 注册表管理器"""
    
    def __init__(self, registry_path='mods_registry.json'):
        """
        初始化 Mod 注册表
        
        Args:
            registry_path: 注册表文件路径（相对路径，会自动放入 configs/ 文件夹）
        """
        # 获取脚本所在目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_dir = os.path.join(script_dir, 'configs')
        
        # 确保 configs 目录存在
        os.makedirs(config_dir, exist_ok=True)
        
        # 构建完整注册表文件路径
        if os.path.isabs(registry_path):
            self.registry_path = registry_path
        else:
            self.registry_path = os.path.join(config_dir, registry_path)
        self.mods = {}
        self._load_registry()
    
    def _load_registry(self):
        """加载注册表"""
        try:
            if os.path.exists(self.registry_path):
                with open(self.registry_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.mods = data.get('mods', {})
                logger.debug(f"加载 Mod 注册表: {len(self.mods)} 个 mod")
            else:
                self.mods = {}
                logger.debug("创建新的 Mod 注册表")
        except Exception as e:
            logger.warning(f"加载 Mod 注册表失败: {e}")
            self.mods = {}
    
    def _save_registry(self):
        """保存注册表"""
        try:
            os.makedirs(os.path.dirname(self.registry_path), exist_ok=True)
            data = {
                'mods': self.mods,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.registry_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug(f"保存 Mod 注册表: {len(self.mods)} 个 mod")
            return True
        except Exception as e:
            logger.error(f"保存 Mod 注册表失败: {e}")
            return False
    
    def _extract_nexus_info_from_filename(self, filename):
        """
        从 Nexus Mods 标准文件名格式中提取 Mod ID 和版本号
        
        Nexus 标准格式：...-{modid}-{version}-{timestamp}.zip
        从文件末尾开始解析，更可靠：
        - 最后的数字：timestamp
        - 倒数第二部分：version（可能是单个数字或多个连字符分隔）
        - 倒数第三部分：mod ID
        
        例如：
        - HUDChallenges-2860-1-2-4-1761234069.zip
          Mod ID: 2860, Version: 1.2.4
        - HUDModLoader - HUDTools-3144-63-1761061516.zip
          Mod ID: 3144, Version: 63
        - BetterInventory-UO-3402-1-0-2-1761066832.zip
          Mod ID: 3402, Version: 1.0.2
        
        Args:
            filename: 文件名
        
        Returns:
            (mod_id, version) 元组，如果未找到返回 (None, None)
        """
        # 移除扩展名
        name_without_ext = os.path.splitext(filename)[0]
        
        # 从末尾开始分割，匹配模式：...-{modid}-{version}-{timestamp}
        # Nexus 格式：ModName-{modid}-{v1}-{v2}-{v3}-...-{timestamp}
        # 从末尾开始解析更可靠
        
        parts = name_without_ext.split('-')
        
        # 查找末尾连续的数字段（用于识别 mod_id, version, timestamp）
        # 从末尾开始，找出所有连续的数字段
        digit_parts = []
        for i in range(len(parts) - 1, -1, -1):
            part_cleaned = parts[i].strip()
            if part_cleaned.isdigit():
                digit_parts.insert(0, part_cleaned)
            else:
                break
        
        # 至少需要3段数字：mod_id, version(可能多段), timestamp
        if len(digit_parts) >= 3:
            # 最后一段是 timestamp
            timestamp = digit_parts[-1]
            # 倒数第二段是 version 的最后一部分
            # 如果有多段 version，则从倒数第二段开始往前都是 version
            # 倒数第三段（或更前）是 mod_id
            
            if len(digit_parts) >= 4:
                # 多段版本号：...-modid-v1-v2-v3-timestamp
                # 例如：HUDChallenges-2860-1-2-4-1761234069
                mod_id = digit_parts[0]  # 第一段数字是 mod_id
                version_parts = digit_parts[1:-1]  # 中间的段是版本号
                version = '.'.join(version_parts)
                
                logger.debug(f"从 Nexus 格式文件名提取(多段版本): Mod ID={mod_id}, Version={version}")
                return mod_id, version
            else:
                # 单段版本号：...-modid-version-timestamp
                # 例如：HUDModLoader - HUDTools-3144-63-1761061516
                mod_id = digit_parts[-3]
                version = digit_parts[-2]
                
                logger.debug(f"从 Nexus 格式文件名提取(单段版本): Mod ID={mod_id}, Version={version}")
                return mod_id, version
        
        # 如果上面没匹配到，尝试正则表达式匹配（更精确）
        # 匹配模式：任意内容-数字-数字或数字-数字-数字-数字-数字
        # 先匹配多段版本号
        nexus_pattern_multi = r'^(.+)-(\d+)-(\d+(?:-\d+)+)-(\d+)$'
        match = re.match(nexus_pattern_multi, name_without_ext)
        
        if match:
            mod_name = match.group(1)
            mod_id = match.group(2)
            version_with_dashes = match.group(3)
            timestamp = match.group(4)
            # 将版本号从 "1-2-4" 转换为 "1.2.4"
            version = version_with_dashes.replace('-', '.')
            
            logger.debug(f"从 Nexus 格式文件名提取(正则多段): Mod ID={mod_id}, Version={version}")
            return mod_id, version
        
        # 匹配单数字版本号
        nexus_pattern_single = r'^(.+)-(\d+)-(\d+)-(\d+)$'
        match = re.match(nexus_pattern_single, name_without_ext)
        
        if match:
            mod_name = match.group(1)
            mod_id = match.group(2)
            version = match.group(3)
            timestamp = match.group(4)
            
            logger.debug(f"从 Nexus 格式文件名提取(正则单数字): Mod ID={mod_id}, Version={version}")
            return mod_id, version
        
        return None, None
    
    def _extract_version_from_filename(self, filename):
        """
        从文件名中提取版本号
        
        优先尝试 Nexus Mods 标准格式
        - Nexus 格式: ModName-{modid}-{version}-{timestamp}.zip
        
        Args:
            filename: 文件名
        
        Returns:
            版本号字符串，如果未找到返回 None
        """
        # 首先尝试 Nexus 标准格式
        _, nexus_version = self._extract_nexus_info_from_filename(filename)
        if nexus_version:
            return nexus_version
        
        logger.debug(f"无法从文件名 {filename} 提取版本号")
        return None
    
    def _extract_nexus_mod_id_from_filename(self, filename):
        """
        从文件名中提取 Nexus Mod ID
        
        Args:
            filename: 文件名（或文件夹名）
        
        Returns:
            Nexus Mod ID 字符串，如果未找到返回 None
        """
        mod_id, _ = self._extract_nexus_info_from_filename(filename)
        return mod_id
    
    def _extract_version_from_zip_comment(self, zip_path):
        """
        从 ZIP 文件的注释中读取版本号
        
        Args:
            zip_path: ZIP 文件路径
        
        Returns:
            版本号字符串，如果未找到返回 None
        """
        try:
            import zipfile
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                comment = zip_ref.comment
                if comment:
                    # 尝试解析注释中的版本信息
                    comment_str = comment.decode('utf-8', errors='ignore')
                    version_match = re.search(r'[vV]?(\d+\.\d+\.\d+)', comment_str)
                    if version_match:
                        version = version_match.group(1)
                        logger.debug(f"从 ZIP 注释提取版本号: {version}")
                        return version
        except Exception as e:
            logger.debug(f"读取 ZIP 注释失败: {e}")
        
        return None
    
    def detect_version(self, zip_path):
        """
        尝试检测 mod 的版本号
        
        Args:
            zip_path: ZIP 文件路径
        
        Returns:
            版本号字符串，如果未找到返回 None
        """
        zip_filename = os.path.basename(zip_path)
        
        # 首先尝试从文件名提取（包括 Nexus 格式）
        version = self._extract_version_from_filename(zip_filename)
        if version:
            return version
        
        # 然后尝试从 ZIP 注释提取
        version = self._extract_version_from_zip_comment(zip_path)
        if version:
            return version
        
        return None
    
    def detect_nexus_mod_id(self, zip_path):
        """
        尝试检测 Nexus Mod ID
        
        Args:
            zip_path: ZIP 文件路径
        
        Returns:
            Nexus Mod ID 字符串，如果未找到返回 None
        """
        zip_filename = os.path.basename(zip_path)
        mod_id = self._extract_nexus_mod_id_from_filename(zip_filename)
        return mod_id
    
    def register_mod(self, mod_filename, zip_path=None, version=None, nexus_mod_id=None, enabled=True):
        """
        注册 mod
        
        Args:
            mod_filename: mod 文件名（如 "ModName.ba2"）
            zip_path: 原始 ZIP 文件路径（用于检测版本号和 Mod ID）
            version: 版本号（如果提供则直接使用，否则尝试检测）
            nexus_mod_id: Nexus Mod ID（如果提供则直接使用，否则尝试检测）
            enabled: 是否已启用（在 INI 配置中）
        
        Returns:
            注册的 mod 信息字典
        """
        # 如果没有提供版本号，尝试检测
        if not version and zip_path:
            version = self.detect_version(zip_path)
        
        # 如果没有提供 Nexus Mod ID，尝试检测
        if not nexus_mod_id and zip_path:
            nexus_mod_id = self.detect_nexus_mod_id(zip_path)
        
        mod_info = {
            'name': mod_filename,
            'version': version,
            'install_date': datetime.now().isoformat(),
            'source_file': os.path.basename(zip_path) if zip_path else None,
            'nexus_mod_id': nexus_mod_id,
            'enabled': enabled
        }
        
        # 如果 mod 已存在，更新信息但保留安装日期
        if mod_filename in self.mods:
            old_info = self.mods[mod_filename]
            mod_info['install_date'] = old_info.get('install_date', mod_info['install_date'])
        
        # 使用 mod 文件名作为 key
        self.mods[mod_filename] = mod_info
        
        # 保存注册表
        self._save_registry()
        
        logger.info(f"注册 mod: {mod_filename} (版本: {version or '未知'}, 启用: {enabled})")
        return mod_info
    
    def mark_mod_enabled(self, mod_filename):
        """
        标记 mod 为已启用
        
        Args:
            mod_filename: mod 文件名
        """
        if mod_filename in self.mods:
            self.mods[mod_filename]['enabled'] = True
            self._save_registry()
            logger.debug(f"标记 mod 为已启用: {mod_filename}")
    
    def mark_mod_disabled(self, mod_filename):
        """
        标记 mod 为已禁用
        
        Args:
            mod_filename: mod 文件名
        """
        if mod_filename in self.mods:
            self.mods[mod_filename]['enabled'] = False
            self._save_registry()
            logger.debug(f"标记 mod 为已禁用: {mod_filename}")
    
    def get_enabled_mods(self):
        """
        获取所有已启用的 mod 列表
        
        Returns:
            已启用的 mod 文件名列表
        """
        return [name for name, info in self.mods.items() if info.get('enabled', False)]
    
    def check_missing_mods(self, ini_mod_list):
        """
        检查注册表中已启用的 mod 是否在 INI 列表中
        
        Args:
            ini_mod_list: INI 文件中的 mod 列表
        
        Returns:
            丢失的 mod 文件名列表
        """
        enabled_mods = self.get_enabled_mods()
        missing = [mod for mod in enabled_mods if mod not in ini_mod_list]
        return missing
    
    def get_mod_info(self, mod_filename):
        """
        获取 mod 信息
        
        Args:
            mod_filename: mod 文件名
        
        Returns:
            mod 信息字典，如果不存在返回 None
        """
        return self.mods.get(mod_filename)
    
    def update_mod_version(self, mod_filename, new_version):
        """
        更新 mod 版本号
        
        Args:
            mod_filename: mod 文件名
            new_version: 新版本号
        
        Returns:
            是否成功更新
        """
        if mod_filename in self.mods:
            self.mods[mod_filename]['version'] = new_version
            self.mods[mod_filename]['last_updated'] = datetime.now().isoformat()
            self._save_registry()
            logger.debug(f"更新 mod {mod_filename} 版本号: {new_version}")
            return True
        return False
    
    def list_mods(self):
        """
        列出所有已注册的 mod
        
        Returns:
            mod 信息列表
        """
        return list(self.mods.values())
    
    def remove_mod(self, mod_filename):
        """
        移除 mod 记录
        
        Args:
            mod_filename: mod 文件名
        
        Returns:
            是否成功移除
        """
        if mod_filename in self.mods:
            del self.mods[mod_filename]
            self._save_registry()
            logger.info(f"移除 mod 记录: {mod_filename}")
            return True
        return False

