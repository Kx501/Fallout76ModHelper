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
    """Mod 注册信息管理器"""
    
    def __init__(self, registry_path='mods_registry.json'):
        """
        初始化 Mod 注册信息
        
        Args:
            registry_path: 注册信息文件路径（相对路径，会自动放入 configs/ 文件夹）
        """
        # 获取脚本所在目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_dir = os.path.join(script_dir, 'configs')
        
        # 确保 configs 目录存在
        os.makedirs(config_dir, exist_ok=True)
        
        # 构建完整注册信息文件路径
        if os.path.isabs(registry_path):
            self.registry_path = registry_path
        else:
            self.registry_path = os.path.join(config_dir, registry_path)
        self.mods = {}
        self._load_registry()
    
    def _load_registry(self):
        """加载注册信息"""
        try:
            if os.path.exists(self.registry_path):
                with open(self.registry_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.mods = data.get('mods', {})
                logger.debug(f"加载 Mod 注册信息: {len(self.mods)} 个 mod")
            else:
                self.mods = {}
                logger.debug("创建新的 Mod 注册信息")
        except Exception as e:
            logger.warning(f"加载 Mod 注册信息失败: {e}")
            self.mods = {}
    
    def _save_registry(self):
        """保存注册信息"""
        try:
            os.makedirs(os.path.dirname(self.registry_path), exist_ok=True)
            data = {
                'mods': self.mods,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.registry_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug(f"保存 Mod 注册信息: {len(self.mods)} 个 mod")
            return True
        except Exception as e:
            logger.error(f"保存 Mod 注册信息失败: {e}")
            return False
    
    def _extract_nexus_info_from_filename(self, filename):
        """
        从 Nexus Mods 标准文件名格式中提取 Mod ID 和版本号
        
        Nexus 标准格式：...-{modid}-{version}-{timestamp}.zip
        从文件末尾开始解析，更可靠：
        - 最后的数字：timestamp
        - 倒数第二部分：version（可能是单个数字或多个连字符分隔）
        - 倒数第三部分：mod ID
        
        支持的特殊格式：
        - 版本号包含标签（Beta、Alpha、RC等）：...-{modid}-{v1}-{v2}-{v3}-{tag}-{timestamp}
        - 版本号前有V前缀：...-{modid}-V{v1}-{v2}-{timestamp}
        
        例如：
        - HUDChallenges-2860-1-2-4-1761234069.zip
          Mod ID: 2860, Version: 1.2.4
        - HUDModLoader - HUDTools-3144-63-1761061516.zip
          Mod ID: 3144, Version: 63
        - FastPip V2-Beta-1269-2-0-10-Beta-1761218034.zip
          Mod ID: 1269, Version: 2.0.10-Beta
        - NoLOD-3141-V1-3-1747120450.zip
          Mod ID: 3141, Version: 1.3
        
        Args:
            filename: 文件名
        
        Returns:
            (mod_id, version) 元组，如果未找到返回 (None, None)
        """
        # 移除扩展名
        name_without_ext = os.path.splitext(filename)[0]
        
        # 先尝试匹配包含标签的格式（如 ...-{modid}-{v1}-{v2}-{v3}-Beta-{timestamp}）
        # 支持的标签：Beta, Alpha, RC, Release, Preview 等（不区分大小写）
        # 格式：任意内容-{modid}-{v1}-{v2}-{v3}-{tag}-{timestamp}
        # 使用非贪婪匹配，确保正确提取 mod_id
        tag_pattern = r'^(.+?)-(\d+)-(\d+(?:-\d+)+)-([A-Za-z]+)-(\d+)$'
        match = re.match(tag_pattern, name_without_ext, re.IGNORECASE)
        if match:
            mod_name = match.group(1)
            mod_id = match.group(2)
            version_with_dashes = match.group(3)
            tag = match.group(4)
            timestamp = match.group(5)
            # 将版本号从 "2-0-10" 转换为 "2.0.10"，并添加标签
            version = version_with_dashes.replace('-', '.') + '-' + tag
            logger.debug(f"从 Nexus 格式文件名提取(带标签): Mod ID={mod_id}, Version={version}")
            return mod_id, version
        
        # 尝试匹配V前缀格式（如 ...-{modid}-V{v1}-{v2}-{timestamp}）
        v_prefix_pattern = r'^(.+)-(\d+)-V(\d+)-(\d+)-(\d+)$'
        match = re.match(v_prefix_pattern, name_without_ext, re.IGNORECASE)
        if match:
            mod_name = match.group(1)
            mod_id = match.group(2)
            version_part1 = match.group(3)
            version_part2 = match.group(4)
            timestamp = match.group(5)
            # 去除V前缀，组合版本号
            version = f"{version_part1}.{version_part2}"
            logger.debug(f"从 Nexus 格式文件名提取(V前缀): Mod ID={mod_id}, Version={version}")
            return mod_id, version
        
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
    
    def extract_mod_name_from_filename(self, filename):
        """
        从压缩包文件名提取模组名（modid和版本号之前的部分）
        
        用于匹配特殊模组配置，提取modid和版本号之前的所有内容作为模组名
        
        Args:
            filename: 压缩包文件名
        
        Returns:
            模组名字符串，如果未找到返回 None
        """
        # 移除扩展名
        name_without_ext = os.path.splitext(filename)[0]
        
        # 尝试匹配包含标签的格式
        tag_pattern = r'^(.+?)-(\d+)-(\d+(?:-\d+)+)-([A-Za-z]+)-(\d+)$'
        match = re.match(tag_pattern, name_without_ext, re.IGNORECASE)
        if match:
            mod_name = match.group(1)
            return mod_name
        
        # 尝试匹配V前缀格式
        v_prefix_pattern = r'^(.+)-(\d+)-V(\d+)-(\d+)-(\d+)$'
        match = re.match(v_prefix_pattern, name_without_ext, re.IGNORECASE)
        if match:
            mod_name = match.group(1)
            return mod_name
        
        # 尝试匹配标准格式
        parts = name_without_ext.split('-')
        digit_parts = []
        for i in range(len(parts) - 1, -1, -1):
            part_cleaned = parts[i].strip()
            if part_cleaned.isdigit():
                digit_parts.insert(0, part_cleaned)
            else:
                break
        
        # 至少需要3段数字：mod_id, version(可能多段), timestamp
        if len(digit_parts) >= 3:
            # 找到第一个数字段的位置，之前的部分就是模组名
            # 计算需要去掉的段数
            if len(digit_parts) >= 4:
                # 多段版本号：去掉最后 len(digit_parts) 段
                mod_name_parts = parts[:-len(digit_parts)]
            else:
                # 单段版本号：去掉最后3段
                mod_name_parts = parts[:-3]
            
            if mod_name_parts:
                mod_name = '-'.join(mod_name_parts)
                return mod_name
        
        # 尝试正则表达式匹配
        nexus_pattern_multi = r'^(.+)-(\d+)-(\d+(?:-\d+)+)-(\d+)$'
        match = re.match(nexus_pattern_multi, name_without_ext)
        if match:
            mod_name = match.group(1)
            return mod_name
        
        nexus_pattern_single = r'^(.+)-(\d+)-(\d+)-(\d+)$'
        match = re.match(nexus_pattern_single, name_without_ext)
        if match:
            mod_name = match.group(1)
            return mod_name
        
        return None
    
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
    
    def detect_version(self, archive_path):
        """
        尝试检测 mod 的版本号
        
        Args:
            archive_path: 压缩包文件路径（ZIP 或 7z）
        
        Returns:
            版本号字符串，如果未找到返回 None
        """
        archive_filename = os.path.basename(archive_path)
        
        # 首先尝试从文件名提取（包括 Nexus 格式）
        version = self._extract_version_from_filename(archive_filename)
        if version:
            return version
        
        # 然后尝试从 ZIP 注释提取（仅支持 ZIP 文件）
        if archive_path.lower().endswith('.zip'):
            version = self._extract_version_from_zip_comment(archive_path)
            if version:
                return version
        
        return None
    
    def detect_nexus_mod_id(self, archive_path):
        """
        尝试检测 Nexus Mod ID
        
        Args:
            archive_path: 压缩包文件路径（ZIP 或 7z）
        
        Returns:
            Nexus Mod ID 字符串，如果未找到返回 None
        """
        archive_filename = os.path.basename(archive_path)
        mod_id = self._extract_nexus_mod_id_from_filename(archive_filename)
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
            'alias': None,
            'version': version,
            'nexus_mod_id': nexus_mod_id,
            'enabled': enabled,
            'order': None,
            'install_method': None,  # 安装方式：None/"direct"/"copy"
            'source_file': os.path.basename(zip_path) if zip_path else None,
            'install_date': datetime.now().isoformat(),
        }
        
        # 如果 mod 已存在，更新信息但保留安装日期、别名、顺序和安装方式
        if mod_filename in self.mods:
            old_info = self.mods[mod_filename]
            mod_info['install_date'] = old_info.get('install_date', mod_info['install_date'])
            mod_info['alias'] = old_info.get('alias', None)
            mod_info['order'] = old_info.get('order', None)
            mod_info['install_method'] = old_info.get('install_method', None)
        
        # 使用 mod 文件名作为 key
        self.mods[mod_filename] = mod_info
        
        # 保存注册信息
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
    
    def unregister_mod(self, mod_filename):
        """
        从注册信息中删除 mod
        
        Args:
            mod_filename: mod 文件名
        
        Returns:
            是否成功删除
        """
        if mod_filename in self.mods:
            del self.mods[mod_filename]
            self._save_registry()
            logger.debug(f"从注册信息删除 mod: {mod_filename}")
            return True
        return False
    
    def get_enabled_mods(self):
        """
        获取所有已启用的 mod 列表
        
        Returns:
            已启用的 mod 文件名列表
        """
        return [name for name, info in self.mods.items() if info.get('enabled', False)]
    
    def check_missing_mods(self, ini_mod_list):
        """
        检查注册信息中已启用的 mod 是否在 INI 列表中
        
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
    
    def set_mod_alias(self, mod_filename, alias):
        """
        设置 mod 别名
        
        Args:
            mod_filename: mod 文件名
            alias: 别名（如果为 None 或空字符串则清除别名）
        
        Returns:
            是否成功设置
        """
        if mod_filename not in self.mods:
            return False
        
        # 如果 alias 为空字符串或 None，清除别名
        if not alias or alias.strip() == '':
            self.mods[mod_filename]['alias'] = None
        else:
            self.mods[mod_filename]['alias'] = alias.strip()
        
        self._save_registry()
        logger.debug(f"设置 mod {mod_filename} 别名: {alias or '(无)'}")
        return True
    
    def get_display_name(self, mod_filename):
        """
        获取 mod 的显示名称（如果有别名则返回别名，否则返回原始名称）
        
        Args:
            mod_filename: mod 文件名
        
        Returns:
            显示名称
        """
        if mod_filename not in self.mods:
            return mod_filename
        
        mod_info = self.mods[mod_filename]
        alias = mod_info.get('alias')
        if alias:
            return alias
        return mod_filename
    
    def set_mod_install_method(self, mod_filename, method):
        """
        设置 mod 的安装方式
        
        Args:
            mod_filename: mod 文件名
            method: 安装方式（"direct" 或 "copy"），None 表示使用默认
        
        Returns:
            (是否成功, 提示信息)
        """
        if mod_filename not in self.mods:
            return False, f"Mod {mod_filename} 不存在于注册信息中"
        
        if method not in [None, "direct", "copy"]:
            return False, "安装方式必须是 'direct'、'copy' 或 None"
        
        old_method = self.mods[mod_filename].get('install_method')
        
        # 转换规则：所有安装方式修改都将在下次安装时生效
        self.mods[mod_filename]['install_method'] = method
        self._save_registry()
        return True, "安装方式已更新，将在下次安装时生效"
    
    def set_mod_order(self, mod_filename, order):
        """
        设置 mod 的排序顺序
        
        Args:
            mod_filename: mod 文件名
            order: 排序顺序（整数，None 表示未排序）
        
        Returns:
            是否成功设置
        """
        if mod_filename not in self.mods:
            return False
        
        if order is not None and not isinstance(order, int):
            return False
        
        self.mods[mod_filename]['order'] = order
        self._save_registry()
        logger.debug(f"设置 mod {mod_filename} 顺序: {order}")
        return True
    
    def get_mods_by_order(self, enabled_only=False):
        """
        按 order 排序获取所有 mod
        
        Args:
            enabled_only: 是否只返回已启用的 mod
        
        Returns:
            按 order 排序的 (mod_filename, mod_info) 元组列表
            None 值的 mod 排在最后
        """
        mods_list = []
        for mod_filename, mod_info in self.mods.items():
            if enabled_only and not mod_info.get('enabled', False):
                continue
            mods_list.append((mod_filename, mod_info))
        
        # 排序：有 order 的按 order 排序，None 值排在最后
        def sort_key(item):
            _, mod_info = item
            order = mod_info.get('order')
            if order is None:
                return (1, 0)  # None 排在最后
            return (0, order)  # 有 order 的按 order 排序
        
        mods_list.sort(key=sort_key)
        return mods_list
    
    def validate_and_fix_order(self, enabled_mods_in_ini_order):
        """
        验证并修复 order 值（处理缺失、重复等问题）
        
        根据 INI 文件中的顺序重新分配 order 值
        
        Args:
            enabled_mods_in_ini_order: 已启用 mod 的文件名列表（按 INI 中的顺序）
        
        Returns:
            修复的 mod 数量
        """
        fixed_count = 0
        
        # 为所有已启用的 mod 重新分配 order（从 1 开始）
        for idx, mod_filename in enumerate(enabled_mods_in_ini_order, 1):
            if mod_filename in self.mods:
                old_order = self.mods[mod_filename].get('order')
                if old_order != idx:
                    self.mods[mod_filename]['order'] = idx
                    fixed_count += 1
        
        # 检查是否有不在 INI 列表中的已启用 mod，将其 order 设为 None
        enabled_mods_set = set(enabled_mods_in_ini_order)
        for mod_filename, mod_info in self.mods.items():
            if mod_info.get('enabled', False) and mod_filename not in enabled_mods_set:
                if mod_info.get('order') is not None:
                    self.mods[mod_filename]['order'] = None
                    fixed_count += 1
        
        if fixed_count > 0:
            self._save_registry()
            logger.debug(f"修复了 {fixed_count} 个 mod 的 order 值")
        
        return fixed_count

